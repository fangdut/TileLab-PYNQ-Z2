"""Create a fresh isolated Vivado build; the archived release is never edited."""
from pathlib import Path
import argparse,shutil,json,hashlib
R=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);args=ap.parse_args();out=args.out.resolve()
    if out.exists():raise FileExistsError('Choose a new build directory')
    model=json.loads((R/'models/v159_frozen_profile.json').read_text())
    for rel,h in model['source_sha256'].items():
        if hashlib.sha256((R/rel).read_bytes()).hexdigest()!=h:raise RuntimeError('Frozen detector source changed: '+rel)
    out.mkdir(parents=True)
    for folder in ['rtl','constraints','ip_repo','scripts']:shutil.copytree(R/folder,out/folder)
    (out/'config').mkdir();shutil.copy2(R/'config/single_tile.json',out/'config/single_tile.json');(out/'reports/v164').mkdir(parents=True);(out/'tmp').mkdir();(out/'SINGLE_TILE_BUILD_ONLY').write_text('No automatic board programming.\n')
    p=out/'scripts/create_project.tcl';s=p.read_text();key='source $root/scripts/add_capture.tcl\nvalidate_bd_design';assert key in s;s=s.replace(key,'source $root/scripts/add_capture.tcl\nset f [open $root/reports/v164/bd_model_id.txt w]\nputs $f [get_property CONFIG.MODEL_ID [get_bd_cells regions_regs]]\nclose $f\nvalidate_bd_design',1);p.write_text(s)
    files=[p for folder in ['rtl','constraints','ip_repo','scripts','config'] for p in (out/folder).rglob('*') if p.is_file()]
    (out/'reports/v164/SOURCE_INPUTS.json').write_text(json.dumps({p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2));print(out)
if __name__=='__main__':main()
