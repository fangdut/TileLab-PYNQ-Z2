"""Stop/inspect/operator-confirm workflow. Image detection belongs to FPGA PL.

These are logical station commands: no motor, brake, or reject actuator is
connected to the current photo-input demonstrator. Never claim physical motion.
"""
from pathlib import Path
import datetime
import hashlib
import json
import threading
import uuid


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Station:
    def __init__(self, backend, catalog, store):
        self.backend = backend
        self.store = Path(store)
        self.store.mkdir(parents=True, exist_ok=True)
        self.catalog = {r['id']: dict(r) for r in catalog}
        if len(self.catalog) != len(catalog):
            raise ValueError('Duplicate sample identifiers')
        self.lock = threading.RLock()
        self.session = uuid.uuid4().hex
        self.revision = 0
        self.phase = 'READY'
        self.cycle = None
        self.error = None
        self.connection = None
        self.stop_requested = False
        self.counts = dict(inspected=0, good=0, defect=0, released=0, segregated=0, faults=0,
                           unvalidated=0, unvalidated_removed=0)
        self.events = []
        self.worker = None
        self._event('session_started', previous_results_reusable=False)

    def _event(self, event, **details):
        row = dict(utc=utc(), session=self.session, revision=self.revision,
                   cycle_id=self.cycle['id'] if self.cycle else None,
                   event=event, phase=self.phase, **details)
        self.events.append(row)
        with (self.store/'events.jsonl').open('a', encoding='utf8') as f:
            f.write(json.dumps(row, ensure_ascii=False)+'\n')

    def _touch(self):
        self.revision += 1

    def state(self):
        with self.lock:
            result = dict(session=self.session, revision=self.revision, phase=self.phase,
                cycle=self.cycle, error=self.error, connection=self.connection, counts=self.counts,
                samples=[{k: r[k] for k in ['id', 'name', 'source_url', 'sha256']}
                         for r in self.catalog.values()],
                events=self.events[-18:], transport='TCP original-photo input',
                cpu_detection=False, gpu_detection=False,
                physical_actuator_connected=False, physical_tile_present=False,
                stop_requested=self.stop_requested,
                logical_release_requested=self.phase == 'RELEASED',
                physical_actuation_verified=False,
                mask_is_precise_crack_trace=False)
            return json.loads(json.dumps(result))

    def _require(self, body):
        if body.get('session') != self.session or body.get('revision') != self.revision:
            raise ValueError('状态已更新，请刷新后操作；过期操作已拒绝')

    def add_image(self, raw, name):
        """Decode only to validate format/dimensions; preserve original bytes."""
        import io
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ['PNG', 'JPEG'] or (image.width, image.height) != (256,1408):
                raise ValueError('请选择256×1408的PNG或JPEG原始灰度扫描图；其他输入尚未验收')
            image.verify()
        digest = hashlib.sha256(raw).hexdigest()
        with self.lock:
            if self.phase not in ['READY', 'RELEASED', 'SEGREGATED', 'REMOVED']:
                raise ValueError('请先完成当前工件的处置，再导入照片')
            folder = self.store/'uploads'
            folder.mkdir(exist_ok=True)
            file = folder/(digest+'.image')
            if file.exists() and sha(file) != digest:
                raise ValueError('导入目录中的同名文件已损坏')
            if not file.exists():
                file.write_bytes(raw)
            ident = 'upload_'+digest[:24]
            self.catalog[ident] = dict(id=ident, file=str(file), sha256=digest,
                name='本地导入 · '+Path(name).name[:80], source_url='', original_unedited=True,
                user_supplied=True, accuracy_prevalidated=False, validation_scope='unvalidated')
            self._touch()
            self._event('image_imported', sample_id=ident, sha256=digest,
                        accuracy_prevalidated=False)
            return dict(sample_id=ident, state=self.state())

    def _launch(self, target):
        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def action(self, body):
        with self.lock:
            self._require(body)
            op = body.get('op')
            if op == 'load':
                if self.phase not in ['READY', 'RELEASED', 'SEGREGATED', 'REMOVED']:
                    raise ValueError('请先完成当前工件的检测与处置')
                row = self.catalog.get(body.get('sample_id'))
                if row is None:
                    raise ValueError('请选择清单中的真实照片')
                file = Path(row['file'])
                if sha(file) != row['sha256']:
                    raise ValueError('输入照片校验失败')
                ident = uuid.uuid4().hex
                folder = self.store/'cycles'/ident
                folder.mkdir(parents=True, exist_ok=False)
                # Freeze this cycle's original file; later source changes cannot
                # silently change the input associated with an operator action.
                (folder/'source.png').write_bytes(file.read_bytes())
                if sha(folder/'source.png') != row['sha256']:
                    raise ValueError('输入冻结校验失败')
                self.cycle = dict(id=ident, sample_id=row['id'], name=row['name'],
                    source_sha256=row['sha256'], source_url=row['source_url'],
                    validation_scope=row.get('validation_scope', 'unvalidated'),
                    qualified_model_sha256=row.get('qualified_model_sha256'),
                    loaded_utc=utc(), result=None, disposition=None)
                self.phase = 'STOPPED'
                self.stop_requested = True
                self.error = None
                self._touch()
                self._event('input_frozen', physical_motion_verified=False,
                            source_sha256=row['sha256'])
            elif op == 'inspect':
                if self.phase != 'STOPPED' or body.get('input_held_confirmed') is not True:
                    raise ValueError('请确认输入已固定，再开始检测')
                self.phase = 'INSPECTING'
                self._touch()
                self._event('inspection_started', cpu_detection=False, gpu_detection=False)
                ident = self.cycle['id']
                self._launch(lambda: self._inspect(ident))
            elif op in ['release', 'segregate']:
                expected = ['GOOD_HOLD'] if op == 'release' else ['DEFECT_HOLD', 'REVIEW_HOLD']
                if self.phase not in expected or body.get('operator_confirmed') is not True:
                    raise ValueError('当前状态不允许该处置，请核对结果并确认')
                if body.get('result_id') != self.cycle['result']['id']:
                    raise ValueError('结果编号过期，禁止处置')
                disposition = 'remove_unvalidated' if self.phase == 'REVIEW_HOLD' else op
                self.phase = 'CONFIRMING'
                self._touch()
                self._event('disposition_requested', disposition=disposition)
                ident = self.cycle['id']
                self._launch(lambda: self._confirm(ident, disposition))
            elif op == 'reset_fault':
                if self.phase != 'FAULT' or body.get('operator_confirmed') is not True:
                    raise ValueError('仅故障状态可以复位；请确认当前工件已移走')
                # Clear the old result before checking the connection. A reset
                # never restores an earlier good decision or releases an item.
                self.cycle = None
                self.error = None
                self.phase = 'READY'
                self.stop_requested = False
                self._touch()
                self._event('fault_reset', old_result_discarded=True)
            else:
                raise ValueError('Unknown operation')
            return self.state()

    def _fault(self, error):
        self.phase = 'FAULT'
        self.stop_requested = True
        self.error = str(error)
        self.counts['faults'] += 1
        if self.cycle:
            self.cycle['result'] = None
        self._touch()
        self._event('fault', reason=str(error), release_permitted=False)

    def _inspect(self, ident):
        folder = self.store/'cycles'/ident
        try:
            if sha(folder/'source.png') != self.cycle['source_sha256']:
                raise ValueError('冻结输入已变化')
            result = self.backend.inspect(folder/'source.png', folder/'fpga')
            if sha(folder/'source.png') != self.cycle['source_sha256']:
                raise ValueError('检测期间输入发生变化')
            with self.lock:
                if self.phase != 'INSPECTING' or self.cycle['id'] != ident:
                    raise ValueError('检测结果与当前工件不匹配')
                alarm = result['pl_image_alarm']
                if alarm not in [0, 1]:
                    raise ValueError('FPGA未返回有效判定')
                result = dict(result, id=uuid.uuid4().hex, completed_utc=utc())
                self.cycle['result'] = result
                qualified = (self.cycle['validation_scope'] == 'development_examples'
                    and bool(self.cycle['qualified_model_sha256'])
                    and self.cycle['qualified_model_sha256'] == result.get('model_sha256'))
                self.cycle['result_qualified'] = qualified
                self.phase = ('DEFECT_HOLD' if alarm else 'GOOD_HOLD') if qualified else 'REVIEW_HOLD'
                self.counts['inspected'] += 1
                self.counts[('defect' if alarm else 'good') if qualified else 'unvalidated'] += 1
                self._touch()
                self._event('inspection_completed', result_id=result['id'],
                    pl_image_alarm=alarm, result_sha256=result['result_sha256'],
                    result_qualified_for_demo_workflow=qualified,
                    boot_identity=result['boot_identity'], frame_sequence=result['pl_frame_sequence'])
                self._save_cycle(folder)
        except Exception as error:
            with self.lock:
                self._fault(error)
                self._save_cycle(folder)

    def _confirm(self, ident, op):
        try:
            # A reset, lost model or disconnected board invalidates the hold.
            connection = self.backend.check()
            with self.lock:
                if self.phase != 'CONFIRMING' or self.cycle['id'] != ident:
                    raise ValueError('处置与当前工件不匹配')
                self.connection = connection
                self.cycle['disposition'] = dict(command=op, confirmed_utc=utc(),
                    result_id=self.cycle['result']['id'], physical_actuation_verified=False)
                self.phase = {'release':'RELEASED', 'segregate':'SEGREGATED',
                              'remove_unvalidated':'REMOVED'}[op]
                self.stop_requested = False
                self.counts[{'release':'released', 'segregate':'segregated',
                             'remove_unvalidated':'unvalidated_removed'}[op]] += 1
                self._touch()
                self._event('logical_disposition_confirmed', command=op,
                            physical_actuation_verified=False)
                self._save_cycle(self.store/'cycles'/ident)
        except Exception as error:
            with self.lock:
                self._fault(error)
                self._save_cycle(self.store/'cycles'/ident)

    def _save_cycle(self, folder):
        path = folder/'cycle.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(session=self.session, phase=self.phase,
            cycle=self.cycle, error=self.error), ensure_ascii=False, indent=2), encoding='utf8')
        temp.replace(path)


class FPGABackend:
    def __init__(self,address,profile,program,hardware):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
        from experimental.hfenet_v198.board_client import Board
        from experimental.hfenet_v198.model_identity import load_identity
        self.board=Board(address=address,timeout=1800)
        self.profile=Path(profile);self.model,_=load_identity(self.profile)
        self.program=json.loads((Path(program)/'identity.json').read_text())
        if self.program['build'].get('pl_identity')!=0x19800001:raise ValueError('不是完整HFENet198固件')
        for key,path in [('model',self.profile/'model.bin'),('bit',Path(hardware)/'system.bit'),('xsa',Path(hardware)/'system.xsa')]:
            if sha(path)!=self.program['build'][key+'_sha256']:raise ValueError('配置与已下载文件身份不匹配: '+key)
        self.board.boot=self.program['boot_identity']
    def check(self):
        h,_,_=self.board.request(1)
        if h[6]!=self.model['crc32'] or h[7]!=self.model['model_bytes']:raise ValueError('板端模型不匹配')
        return dict(verified_utc=utc(),boot_identity=h[8],model_crc32=h[6],pl_identity=h[5])
    def inspect(self,image,folder):
        self.check();result=self.board.infer(image,folder,self.model)
        if result['input_file_sha256']!=sha(image):raise ValueError('图片身份不匹配')
        return result
