"""Make a clean public Git tree and two ZIPs; retain old project/runtime data."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,zipfile

R=Path(__file__).resolve().parents[1];TARGET=R.parent/'TileLab_Submission_2026'
PUBLIC=TARGET/'project'/R.name;OUT=R.parent/'TileLab_提交交付'
SKIP_DIRS={'__pycache__','runtime','.git','.Xil','_ide','.rigel_lopper','CMakeFiles'}
SKIP_SUFFIXES={'.o','.obj','.d','.pyc','.pyo','.log','.jou','.pid','.lock','.tmp','.wdb'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def accepted(p):
    n=p.relative_to(R);parts=n.parts
    if any(x in SKIP_DIRS for x in parts):return False
    if p.suffix.lower() in SKIP_SUFFIXES and n.as_posix()!='reports/v153/host_tests_final.log':return False
    if p.name in ('display_command.txt','display_status.json','display_control.json','CMakeCache.txt','build.ninja','rules.ninja','cmake_install.cmake','.ninja_deps','.ninja_log','dfx_runtime.txt'):return False
    if parts[0]=='host':
        if p.suffix=='.json' and p.name!='recipes.json':return False
        return p.suffix.lower() in ('.py','.ps1','.cs','.js','.html','.json','.txt','.tcl')
    if parts[0] in ('rtl','constraints','ip_repo','models','sim','scripts','docs','data','validation','licenses'):return True
    if parts[0].endswith('.sdk'):return True
    if parts[0]=='reports':
        if len(parts)==2:return p.name in ('timing_summary.rpt','utilization.rpt','drc.rpt','cdc.rpt','cdc_details.rpt','methodology.rpt','programmed_v153.json')
        if parts[1]=='accepted_baseline':return True
        if parts[1]=='v153':
            if any('before_' in x or 'failure' in x or 'initial_status_missing' in x for x in parts):return p.name=='summary.json'
            return p.suffix.lower() in ('.json','.png','.txt') or p.name=='host_tests_final.log'
        if parts[1]=='document_qa':return p.name in ('checks.json','outputs.json','manual_layout.json','film_layout.json','visual_review.json')
        return False
    if parts[0].endswith('.srcs'):return True
    if parts[0].endswith('.gen'):return p.name=='system_wrapper.v'
    return len(parts)==1 and (p.suffix.lower() in ('.md','.json','.bat','.xpr') or p.name=='.gitignore')

def main():
    if TARGET.exists():raise RuntimeError('Refusing to overwrite an existing public staging directory')
    if not (R/'DELIVERY_MANIFEST.json').exists():raise RuntimeError('Seal and verify first')
    OUT.mkdir(exist_ok=True);PUBLIC.mkdir(parents=True)
    paths=[]
    for parent,dirs,files in os.walk(R,followlinks=False):
        dirs[:]=[d for d in dirs if d not in SKIP_DIRS and not (Path(parent)/d).is_symlink() and not (Path(parent)/d).is_junction()]
        for name in files:
            p=Path(parent)/name
            if not p.is_symlink() and accepted(p):paths.append(p)
    for p in paths:
        target=PUBLIC/p.relative_to(R);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    # Installation/runtime data are not part of publication. All authored code,
    # data, references, PDFs and accepted download binaries are retained.
    frozen=json.loads((R/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))
    missing=[n for n in frozen['frozen_sha256'] if not (PUBLIC/n).is_file()]
    if missing:raise RuntimeError('Package omitted frozen files: '+repr(missing))
    subprocess.run([os.sys.executable,'-B',str(PUBLIC/'scripts/relocate_project.py')],check=True)
    subprocess.run([os.sys.executable,'-B',str(PUBLIC/'scripts/verify_submission.py')],check=True)
    (TARGET/'README.md').write_text('# TileLab - PYNQ-Z2 FPGA 瓷砖裂纹检测竞赛原型\n\n'
        '完整项目在 [project/pynq_z2_tile_v1_53](project/pynq_z2_tile_v1_53/README.md)。保留项目文件夹名；其中 `.sdk` 是 Vitis workspace。\n\n'
        '720p60 FPGA 检测、产品最佳证据、以太网与电脑人工复核。已做实际板卡测试；真实照片运动回放不是工厂相机验收。固定配方对外部大理石漏检明显，适用范围与实测结果见工程 README。\n\n'
        '- [技术与教学手册](project/pynq_z2_tile_v1_53/docs/TileLab_最终提交版_技术与教学手册.pdf)\n'
        '- [详细演示视频拍摄方案](project/pynq_z2_tile_v1_53/docs/TileLab_演示视频详细拍摄方案.pdf)\n'
        '- [实测摘要](project/pynq_z2_tile_v1_53/reports/v153/final_validation_summary.json)\n'
        '- [第三方许可](project/pynq_z2_tile_v1_53/THIRD_PARTY_NOTICES.md)\n\n'
        '完整 ZIP 保留输入照片、真值和实测证据；源码 ZIP 省略图片素材与 RGB 基线，无法单独完成照片回归/完整演示。工程不含账号、运行中数据库或海量自动留图。\n',encoding='utf-8')
    (TARGET/'.gitignore').write_text('__pycache__/\n*.pyc\n*.pid\n*.lock\n*.tmp\n*.o\n*.d\n*.wdb\n.Xil/\n**/host/runtime/\n**/review_records/\n**/*display_command.txt\n**/*display_status.json\n',encoding='utf-8')
    (TARGET/'.gitattributes').write_text('* -text\n',encoding='utf-8')
    # Preserve LF/CRLF byte digests instead of letting Git autocrlf transform them.
    secret=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    allfiles=sorted(p for p in TARGET.rglob('*') if p.is_file())
    for p in allfiles:
        if p.stat().st_size>=100*1024*1024:raise RuntimeError('GitHub file too large '+str(p))
        if p.suffix.lower() in ('.py','.json','.tcl','.bat','.ps1','.md','.yaml','.yml','.xml') and secret.search(p.read_bytes()):raise RuntimeError('Credential-shaped content '+str(p))
    release=dict(version='V1.53',files=len(allfiles),uncompressed_bytes=sum(p.stat().st_size for p in allfiles),
        artifact_origin='Accepted V1.52 PL/ARM, V1.53 host physically tested',github_uploaded=False,
        exclusions=['runtime review database and user notes','automatic archive images','Vivado generated IP cache','compiler object files','tool installation and credentials'],
        sha256={p.relative_to(TARGET).as_posix():sha(p) for p in allfiles})
    (TARGET/'PACKAGE_MANIFEST.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
    packages=[]
    allfiles=sorted(p for p in TARGET.rglob('*') if p.is_file())
    for light,label in ((False,'完整工程'),(True,'源码与文档')):
        dest=OUT/f'TileLab_V1.53_{label}.zip'
        if dest.exists():raise RuntimeError('Refusing to overwrite '+str(dest))
        with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            if light:z.writestr(str(Path(TARGET.name)/'SOURCE_ONLY_README.md'),'这是源码与文档阅读包，不含输入图片和 RGB 基线。完整交付请使用完整工程 ZIP 或完整 Git 仓库；光靠本包不能通过完整 DELIVERY_MANIFEST 校验、照片回归或运行全部演示。所有源文件仍保持原始哈希。\n')
            for p in allfiles:
                rel=p.relative_to(TARGET)
                if light and any(x in rel.parts for x in ('data','reference_rgb')):continue
                if light and p.suffix.lower() in ('.png','.bmp','.jpg','.jpeg'):continue
                z.write(p,Path(TARGET.name)/rel)
        with zipfile.ZipFile(dest) as z:assert z.testzip() is None
        packages.append(dict(path=str(dest),bytes=dest.stat().st_size,sha256=sha(dest),full_reproduction=not light))
    (OUT/'packages.json').write_text(json.dumps(packages,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(public_root=str(TARGET),files=release['files'],bytes=release['uncompressed_bytes'],packages=packages),ensure_ascii=False))
if __name__=='__main__':main()
