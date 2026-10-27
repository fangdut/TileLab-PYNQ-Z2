"""Frozen-reference selection and FPGA transport; no host vision inference."""
from pathlib import Path
import hashlib,json,struct,zlib,sys
from controller import FPGABackend,sha,utc

CAPABILITY=0x2000c001

class ProfilesBackend(FPGABackend):
    def __init__(self,address,registry,program,hardware):
        root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/fpga_texture_v170'))
        from board_client import Board
        self.board=Board(address=address,timeout=15);self.program=json.loads((Path(program)/'identity.json').read_text())
        for key,path in [('bit',Path(hardware)/'system.bit'),('xsa',Path(hardware)/'system.xsa')]:
            if sha(path)!=self.program['build'][key+'_sha256']:raise ValueError('已下载硬件与参照配置不匹配')
        registry=Path(registry).resolve();self.registry_sha256=sha(registry);self.registry_file=registry
        if self.registry_sha256!=self.program['build'].get('profile_registry_sha256'):raise ValueError('参照清单与已下载固件不匹配')
        index=json.loads(registry.read_text(encoding='utf8'));self.slots={}
        allowed=self.program['build'].get('allowed_profiles',[])
        if not allowed:raise ValueError('请先部署支持明确参照列表的闭环固件')
        compiled={p['id']:p for p in allowed}
        for item in index['profiles']:
            folder=(registry.parent/item['path']).resolve()
            if not folder.is_relative_to(registry.parent) or item['id'] in self.slots:raise ValueError('无效的参照路径或重复编号')
            if item['id'] not in compiled or any(item[k]!=compiled[item['id']][k] for k in ['model_sha256','model_crc32','model_bytes']):raise ValueError('参照不在已编译允许列表中')
            self.slots[item['id']]=dict(item,path=folder)
            self._verify_slot(item['id'])
        if set(self.slots)!=set(compiled) or len(self.slots)!=2:raise ValueError('参照列表与固件不一致')
        self.profile_id=None;self.profile=None;self.model=None;self.last_sequence=None
        h=self._status()
        matches=[key for key,p in self.slots.items() if p['model_crc32']==h[6] and p['model_bytes']==h[7]]
        if len(matches)!=1:raise ValueError('板端未加载已部署参照，请重新部署')
        self._set_active(matches[0]);self.check()
    def _verify_slot(self,key):
        item=self.slots[key];folder=item['path'];blob=(folder/'model.bin').read_bytes();graph=json.loads((folder/'graph.json').read_text())
        if hashlib.sha256(blob).hexdigest()!=item['model_sha256'] or zlib.crc32(blob)!=item['model_crc32'] or len(blob)!=item['model_bytes']:
            raise ValueError('参照二进制发生变化')
        if sha(folder/'graph.json')!=item['graph_sha256']:raise ValueError('参照元数据发生变化')
        if graph['sha256']!=item['model_sha256'] or graph['crc32']!=item['model_crc32']:raise ValueError('参照元数据与二进制不匹配')
        h=struct.unpack_from('<64I',blob)
        if (h[0],h[2],h[3],h[4],h[16])!=(0x17000001,47,224,28,2408448) or any(h[20:27]):raise ValueError('参照几何或ABI不匹配')
        return graph
    def _status(self):
        h,data,_=self.board.request(1)
        if h[8]!=self.program['boot_identity']:raise ValueError('开发板启动编号变化，旧标定和结果不得继续使用')
        expected=sorted(p['model_crc32'] for p in self.slots.values())
        if len(data)!=32:raise ValueError('板端不支持闭环参照切换')
        cap=struct.unpack('<8I',data)
        if cap[0]!=CAPABILITY or cap[1]!=2 or sorted(cap[2:4])!=expected or cap[4:7]!=(751760,28,47):raise ValueError('板端参照能力与部署记录不一致')
        return h
    def _set_active(self,key):
        self.model=self._verify_slot(key);self.profile=self.slots[key]['path'];self.profile_id=key
    def public_profiles(self):
        return [{k:p[k] for k in ['id','name','note','model_sha256']} for p in self.slots.values()]
    def activate(self,key):
        if key not in self.slots:raise ValueError('请选择已部署的参照')
        if sha(self.registry_file)!=self.registry_sha256:raise ValueError('参照列表运行期间发生变化')
        graph=self._verify_slot(key);h=self._status()
        try:
            if h[6]!=graph['crc32'] or h[7]!=graph['model_bytes']:
                self.profile_id=None;self.model=None;self.profile=None
                self.board.upload(self.slots[key]['path']);self.last_sequence=None
            self._set_active(key);return self.check()
        except Exception:
            self.profile_id=None;self.model=None;self.profile=None
            raise
    def check(self):
        if self.profile_id is None:raise ValueError('参照切换未完成，禁止检测或处置')
        if sha(self.registry_file)!=self.registry_sha256:raise ValueError('参照列表发生变化')
        self._verify_slot(self.profile_id);h=self._status()
        if h[6]!=self.model['crc32'] or h[7]!=self.model['model_bytes']:raise ValueError('板端参照与当前材质不匹配')
        return dict(verified_utc=utc(),boot_identity=h[8],model_crc32=h[6],pl_identity=h[5],
                    model_sha256=self.model['sha256'],profile_id=self.profile_id)
