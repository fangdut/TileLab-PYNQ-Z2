"""Package matching routed hardware and compiled ARM firmware. No programming."""
from pathlib import Path
import argparse,json,shutil,zipfile
from deployment_single_tile import ROOT,sha,matching_bit,load,verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--hardware',required=True,type=Path);ap.add_argument('--workspace',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();p=load(ROOT)
    if a.out.exists():raise FileExistsError(a.out)
    hw=a.hardware;ws=a.workspace;matching_bit(hw)
    built=json.loads((ws/'build_result.json').read_text());inputs=json.loads((hw.parent/'SOURCE_INPUTS.json').read_text());source={}
    if not built.get('compiled') or built['elf_sha256']!=sha(ws/'hdmi_ethernet/build/hdmi_ethernet.elf') or built['xsa_sha256']!=sha(hw/'system.xsa'):raise ValueError('Compiled software provenance mismatch')
    if built['profile_sha256']!=sha(ROOT/'config/single_tile.json'):raise ValueError('Software profile changed')
    for rel,digest in inputs.items():
        if rel.startswith('rtl/'):
            if sha(ROOT/rel)!=digest:raise ValueError('RTL differs from routed build: '+rel)
            source[rel]=digest
    authored=ROOT/'pynq_z2_tile_v1_53.sdk/ethernet_sources'
    for name,digest in built['source_sha256'].items():
        if sha(authored/name)!=digest:raise ValueError('Firmware source changed: '+name)
        source[(authored/name).relative_to(ROOT).as_posix()]=digest
    for rel in ['config/single_tile.json','models/v159_integer_model.json','scripts/program_single_tile.tcl']:source[rel]=sha(ROOT/rel)
    a.out.mkdir(parents=True)
    for name in ['system.bit','system.xsa','implementation_status.txt','timing_summary.rpt','utilization.rpt','drc.rpt','cdc.rpt','bus_skew.rpt','methodology.rpt','route_status.rpt']:shutil.copy2(hw/name,a.out/name)
    shutil.copy2(ws/'hdmi_ethernet/build/hdmi_ethernet.elf',a.out/'hdmi_ethernet.elf')
    with zipfile.ZipFile(hw/'system.xsa') as z:
        names=[n for n in z.namelist() if n.split('/')[-1]=='ps7_init.tcl']
        if len(names)!=1:raise ValueError('Ambiguous/missing vendor PS initialization script')
        (a.out/'ps7_init.tcl').write_bytes(z.read(names[0]))
    m=dict(release='V1.64',firmware_version=0x13200,model_id=p['model_id'],profile_sha256=p['profile_sha256'],scope='Matching development hardware/software bundle; no current board or painted/multi-material accuracy acceptance',board_accepted=False,accuracy_qualified=False,source_sha256=source,files={q.name:sha(q) for q in a.out.iterdir() if q.is_file()})
    (a.out/'DEPLOYMENT.json').write_text(json.dumps(m,indent=2)+'\n');verify(a.out);print(json.dumps(dict(bundle=str(a.out.resolve()),verified=True,board_accepted=False)))

if __name__=='__main__':main()
