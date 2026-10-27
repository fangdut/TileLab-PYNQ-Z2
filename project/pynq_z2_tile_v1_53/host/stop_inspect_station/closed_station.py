"""Material verification -> PL inspection -> recorded review -> disposition."""
from pathlib import Path
import json,uuid
from controller import Station,sha,utc
from calibration import Calibrations,digest,text

IDLE=['READY','RELEASED','SEGREGATED','REMOVED']
HOLDS=['CALIBRATION_HOLD','REVIEW_HOLD','GOOD_HOLD','DEFECT_HOLD','CONFLICT_HOLD']

class ClosedStation(Station):
    def __init__(self,backend,catalog,store):
        super().__init__(backend,catalog,store)
        self.calibrations=Calibrations(self.store/'materials',backend.public_profiles())
        self.material_id=None;self.run_id=None;self.selection_id=None
        self.counts.update(calibration_samples=0,calibration_failed=0,manual_reviews=0,conflicts=0)
        self._event('closed_loop_enabled',visual_inference='FPGA_PL',physical_camera_calibration=False)
    def state(self):
        with self.lock:
            s=super().state();m=self.calibrations.materials.get(self.material_id)
            run=self.calibrations.summary(self.run_id)
            for row in s['samples']:row['profile_id_hint']=self.catalog[row['id']].get('profile_id_hint')
            s['closed_loop']=dict(enabled=True,profiles=self.backend.public_profiles(),
                materials=list(self.calibrations.materials.values()),active_material=m,run=run,
                selection_id=self.selection_id,calibrated=bool(run and run['certificate'] and not run['revoked']),
                calibration_scope='已部署参照的工位核验，不是新模型训练或独立准确率认证')
            build=getattr(self.backend,'program',{}).get('build',{})
            s['deployment']=dict(elf_sha256=build.get('elf_sha256'),bit_sha256=build.get('bit_sha256'))
            return s
    def _idle(self):
        if self.phase not in IDLE:raise ValueError('请先完成当前工件的复核和处置')
    def _context(self,certificate=False):
        if not self.material_id or not self.run_id:raise ValueError('请先建立或选择材质标定')
        m=self.calibrations.validate_material(self.material_id);r=self.calibrations.validate_run(self.run_id)
        if certificate and (not r['certificate'] or r['revoked']):raise ValueError('材质尚未通过本批标定核验')
        return dict(material_id=m['id'],material_name=m['name'],material_sha256=digest(m),run_id=r['id'],
            profile_id=m['profile_id'],profile_sha256=m['profile_sha256'],boot_identity=r['boot_identity'],
            certificate_id=r['certificate']['id'] if r['certificate'] else None,selection_id=self.selection_id)
    def _cycle_context(self,certificate=False):
        context=self._context(certificate)
        if not self.cycle or self.cycle['context']!=context:raise ValueError('材质、参照或标定批次已变化，旧结果无效')
        return context
    def _artifacts(self):
        folder=self.store/'cycles'/self.cycle['id']
        if sha(folder/'source.png')!=self.cycle['source_sha256']:raise ValueError('工件原图发生变化')
        for relative,expected in self.cycle.get('artifact_sha256',{}).items():
            if sha(folder/relative)!=expected:raise ValueError('本次检测证据发生变化')
    def _check_review_artifacts(self):
        try:self._artifacts()
        except Exception as error:
            self._fault(error);self._save_cycle(self.store/'cycles'/self.cycle['id'])
            raise ValueError(str(error)) from error
    def _select(self,material_id,reason,force=False):
        self._idle();m=self.calibrations.validate_material(material_id)
        self.material_id=material_id;self.run_id=None;self.selection_id=uuid.uuid4().hex;ident=self.selection_id
        self.cycle=None;self.error=None;self.phase='CONFIGURING';self.stop_requested=True
        self._touch();self._event('material_switch_started',material_id=material_id,old_result_invalidated=True)
        self._launch(lambda:self._activate(ident,m,reason,force))
    def _activate(self,ident,m,reason,force):
        try:
            connection=self.backend.activate(m['profile_id'])
            with self.lock:
                if self.phase!='CONFIGURING' or self.selection_id!=ident:raise ValueError('材质切换任务过期')
                run=self.calibrations.start(m['id'],connection,reason,force)
                self.run_id=run['id'];self.connection=connection;self.phase='READY';self.stop_requested=False
                self._touch();self._event('material_selected',material_id=m['id'],run_id=run['id'],profile_id=m['profile_id'])
        except Exception as error:
            with self.lock:self._fault(error)
    def action(self,body):
        with self.lock:
            self._require(body);op=body.get('op')
            if op=='create_material':
                self._idle();m=self.calibrations.create(body.get('name'),body.get('profile_id'),body.get('conditions'),body.get('operator'))
                self._event('material_created',material_id=m['id']);self._select(m['id'],'首次工位核验')
            elif op=='select_material':
                self._select(body.get('material_id'),'选择已有材质，检查本次启动身份')
            elif op=='restart_calibration':
                if not self.material_id:raise ValueError('尚未选择材质')
                self._select(self.material_id,text(body.get('reason'),'重新核验原因',240),True)
            elif op=='freeze_calibration':
                self._idle();self._context()
                if not self.calibrations.summary(self.run_id)['ready_to_freeze']:raise ValueError('需至少3张不同良品和1张已知缺陷全部核验一致，才能封存')
                if body.get('conditions_confirmed') is not True:raise ValueError('请确认实际条件与记录一致')
                operator=text(body.get('operator'),'操作员',60);ident=self.selection_id
                self.phase='CONFIGURING';self._touch();self._launch(lambda:self._freeze(ident,operator))
            elif op=='load':
                self._idle();purpose=body.get('purpose','inspection')
                if purpose not in ['calibration_good','calibration_defect','inspection']:raise ValueError('请选择核验或检测用途')
                context=self._context(purpose=='inspection')
                if purpose=='inspection' and body.get('conditions_confirmed') is not True:raise ValueError('请确认拍摄条件与标定记录一致')
                row=self.catalog.get(body.get('sample_id'))
                if row is None:raise ValueError('图片不存在')
                if purpose!='inspection':self.calibrations.check_input_unused(self.run_id,row['sha256'])
                super().action(body)
                self.cycle.update(purpose=purpose,context=context,review=None,validation_scope='unvalidated',qualified_model_sha256=None)
                self._event('cycle_context_bound',material_id=self.material_id,run_id=self.run_id,purpose=purpose)
                self._save_cycle(self.store/'cycles'/self.cycle['id'])
            elif op=='inspect':
                self._cycle_context(self.cycle is not None and self.cycle.get('purpose')=='inspection')
                return super().action(body)
            elif op=='review':
                self._review(body)
            elif op in ['release','segregate']:
                self._dispose(body)
            elif op=='reset_fault':
                return super().action(body)
            else:raise ValueError('未知闭环操作')
            return self.state()
    def _freeze(self,ident,operator):
        try:
            connection=self.backend.check()
            with self.lock:
                if self.phase!='CONFIGURING' or ident!=self.selection_id:raise ValueError('标定任务过期')
                cert=self.calibrations.freeze(self.run_id,connection,operator)
                self.connection=connection;self.phase='READY';self.stop_requested=False;self.cycle=None
                self._touch();self._event('calibration_frozen',certificate_id=cert['id'],material_id=self.material_id,run_id=self.run_id)
        except Exception as error:
            with self.lock:self._fault(error)
    def _fault(self,error):
        if getattr(self,'run_id',None):self.calibrations.revoke(self.run_id,str(error))
        if self.cycle:
            if self.cycle.get('result') or self.cycle.get('review'):
                self.cycle.setdefault('invalidated_evidence',[]).append(dict(result=self.cycle.get('result'),review=self.cycle.get('review'),reason=str(error),utc=utc()))
            self.cycle['review']=None
        super()._fault(error)
    def _inspect(self,ident):
        folder=self.store/'cycles'/ident
        try:
            with self.lock:self._cycle_context(self.cycle['purpose']=='inspection');self._artifacts()
            result=self.backend.inspect(folder/'source.png',folder/'fpga')
            with self.lock:
                if self.phase!='INSPECTING' or self.cycle['id']!=ident:raise ValueError('检测结果已过期')
                context=self._cycle_context(self.cycle['purpose']=='inspection');self._artifacts()
                if result['pl_image_alarm'] not in [0,1] or result['model_sha256']!=context['profile_sha256'] or result['boot_identity']!=context['boot_identity']:raise ValueError('FPGA返回的参照身份或结果无效')
                if sha(folder/'fpga/raw_result.bin')!=result['result_sha256']:raise ValueError('FPGA结果文件校验失败')
                result=dict(result,id=uuid.uuid4().hex,completed_utc=utc())
                self.cycle['result']=result;self.cycle['result_qualified']=False
                self.cycle['artifact_sha256']={p.relative_to(folder).as_posix():sha(p) for p in [folder/'source.png',folder/'fpga/raw_result.bin',folder/'fpga/mask.png',folder/'fpga/overlay.png'] if p.is_file()}
                self.phase='REVIEW_HOLD' if self.cycle['purpose']=='inspection' else 'CALIBRATION_HOLD'
                self.counts['inspected']+=1
                if self.cycle['purpose']=='inspection':self.counts['unvalidated']+=1
                self._touch();self._event('inspection_completed',result_id=result['id'],material_id=self.material_id,
                    pl_image_alarm=result['pl_image_alarm'],result_sha256=result['result_sha256'],boot_identity=result['boot_identity'],frame_sequence=result['pl_frame_sequence'])
                self._save_cycle(folder)
        except Exception as error:
            with self.lock:self._fault(error);self._save_cycle(folder)
    def _review(self,body):
        if self.phase not in HOLDS or not self.cycle or not self.cycle['result'] or self.cycle['review']:
            raise ValueError('当前没有可复核的新结果，已有复核不能覆盖')
        self._cycle_context(self.cycle['purpose']=='inspection');self._check_review_artifacts()
        result=self.cycle['result']
        if body.get('result_id')!=result['id']:raise ValueError('复核结果编号过期')
        verdict=body.get('verdict')
        if verdict not in ['good','defect','uncertain']:raise ValueError('请选择人工复核结论')
        operator=text(body.get('operator'),'操作员',60);note=body.get('note','')
        if not isinstance(note,str) or len(note)>240:raise ValueError('复核说明过长')
        disagreement=verdict!='uncertain' and int(verdict=='defect')!=result['pl_image_alarm']
        if (disagreement or verdict=='uncertain') and not note.strip():raise ValueError('冲突或待定结论必须填写复核说明')
        review=dict(id=uuid.uuid4().hex,result_id=result['id'],result_sha256=result['result_sha256'],
                    context_sha256=digest(self.cycle['context']),operator=operator,verdict=verdict,note=note.strip(),utc=utc(),disagreement=disagreement)
        self.cycle['review']=review;self.counts['manual_reviews']+=1
        if self.cycle['purpose']=='inspection':
            if disagreement:
                self.calibrations.revoke(self.run_id,'人工与FPGA结论冲突：'+self.cycle['id']);self.counts['conflicts']+=1
            if verdict=='good' and not disagreement:self.phase='GOOD_HOLD'
            elif verdict=='defect':self.phase='DEFECT_HOLD'
            elif verdict=='good':self.phase='CONFLICT_HOLD'
            else:self.phase='REVIEW_HOLD'
        self._touch();self._event('manual_review_recorded',review_id=review['id'],verdict=verdict,disagreement=disagreement)
        self._save_cycle(self.store/'cycles'/self.cycle['id'])
    def _dispose(self,body):
        if self.phase not in HOLDS or body.get('operator_confirmed') is not True:raise ValueError('请完成复核并确认当前处置')
        if not self.cycle['review'] or body.get('result_id')!=self.cycle['result']['id']:raise ValueError('请先记录本次人工复核，且使用当前结果')
        operator=text(body.get('operator'),'处置操作员',60);self._check_review_artifacts()
        if self.cycle['purpose']!='inspection':
            if body['op']=='release':raise ValueError('核验样本不能计为生产良品放行')
            op='calibration_complete'
        elif body['op']=='release':
            self._cycle_context(True)
            if self.phase!='GOOD_HOLD' or self.cycle['review']['verdict']!='good' or self.cycle['result']['pl_image_alarm']!=0:raise ValueError('人工与FPGA均确认正常且标定有效时才允许良品放行')
            op='release'
        else:
            self._cycle_context(False)
            if self.phase=='GOOD_HOLD':raise ValueError('正常确认结果请使用良品放行')
            op='segregate' if self.cycle['review']['verdict']=='defect' else 'remove_unvalidated'
        self.phase='CONFIRMING';self._touch();self._event('disposition_requested',disposition=op)
        ident=self.cycle['id'];self._launch(lambda:self._confirm(ident,op,operator))
    def _confirm(self,ident,op,operator):
        try:
            connection=self.backend.check()
            with self.lock:
                if self.phase!='CONFIRMING' or self.cycle['id']!=ident:raise ValueError('处置任务已过期')
                context=self._cycle_context(op=='release');self._artifacts()
                if connection['boot_identity']!=context['boot_identity'] or connection['model_sha256']!=context['profile_sha256']:raise ValueError('处置前参照或启动编号变化')
                if op=='calibration_complete':
                    check=self.calibrations.record(self.run_id,self.cycle);self.counts['calibration_samples']+=1
                    self.counts['calibration_failed']+=int(not check['matched']);self.phase='REMOVED'
                else:
                    self.phase={'release':'RELEASED','segregate':'SEGREGATED','remove_unvalidated':'REMOVED'}[op]
                    self.counts[{'release':'released','segregate':'segregated','remove_unvalidated':'unvalidated_removed'}[op]]+=1
                self.connection=connection;self.stop_requested=False
                self.cycle['disposition']=dict(command=op,confirmed_by=operator,confirmed_utc=utc(),result_id=self.cycle['result']['id'],review_id=self.cycle['review']['id'],physical_actuation_verified=False)
                self._touch();self._event('logical_disposition_confirmed',command=op,review_id=self.cycle['review']['id'],physical_actuation_verified=False)
                self._save_cycle(self.store/'cycles'/ident)
        except Exception as error:
            with self.lock:self._fault(error);self._save_cycle(self.store/'cycles'/ident)
    def audit(self):
        with self.lock:
            rows=[]
            for file in sorted((self.store/'cycles').glob('*/cycle.json')):
                data=json.loads(file.read_text(encoding='utf8'));c=data['cycle'];r=c.get('result') or {};review=c.get('review') or {};context=c.get('context') or {};disposition=c.get('disposition') or {}
                invalid=(c.get('invalidated_evidence') or [{}])[-1];old_review=invalid.get('review') or {}
                rows.append(dict(cycle_id=c['id'],loaded_utc=c['loaded_utc'],material=context.get('material_name'),run_id=context.get('run_id'),certificate_id=context.get('certificate_id'),purpose=c.get('purpose'),source_sha256=c['source_sha256'],model_sha256=r.get('model_sha256'),boot_identity=r.get('boot_identity'),frame=r.get('pl_frame_sequence'),fpga_alarm=r.get('pl_image_alarm'),review=review.get('verdict'),review_operator=review.get('operator'),review_note=review.get('note'),review_id=review.get('id'),disposition=disposition.get('command'),confirmed_by=disposition.get('confirmed_by'),confirmed_utc=disposition.get('confirmed_utc'),phase=data['phase'],invalidated_reason=invalid.get('reason'),invalidated_previous_review=old_review.get('verdict'),invalidated_previous_operator=old_review.get('operator')))
            rows.sort(key=lambda r:(r['loaded_utc'],r['cycle_id']))
            return json.loads(json.dumps(dict(scope='LOGICAL_WORKSTATION_AUDIT_NO_PHYSICAL_ACTUATION',materials=list(self.calibrations.materials.values()),calibration_runs=list(self.calibrations.runs.values()),records=rows)))
