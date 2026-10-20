"""Produce an English-path, self-contained source/deployment/replay package."""
from pathlib import Path
import argparse,shutil,json,hashlib,zipfile,re
R=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--player',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);project=a.out/'project';project.mkdir()
    for folder in ('rtl','constraints','ip_repo','experimental/reference_v167','tools/reference_tile','skill'):shutil.copytree(R/folder,project/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    host=project/'host';host.mkdir()
    for f in (R/'host').iterdir():
        if f.is_file() and f.suffix in ('.py','.json','.html','.css','.js','.cs','.ps1','.txt') and not f.name.startswith('test_') and f.name not in ('display_command.txt','player_instance.json','player_status.json'):shutil.copy2(f,host/f.name)
    shutil.copy2(R/'host/test_reference_v167.py',host/'test_reference_v167.py')
    for name in ('create_project.tcl','add_capture.tcl','ps7_preset.tcl','build_single_tile.tcl','program_single_tile_verified.tcl'):
        dest=project/'scripts'/name;dest.parent.mkdir(exist_ok=True);shutil.copy2(R/'scripts'/name,dest)
    shutil.copytree(R/'scripts/reference_v167',project/'scripts/reference_v167',ignore=shutil.ignore_patterns('__pycache__','*.pyc','check_migration.py'))
    sdk=project/'pynq_z2_tile_v1_53.sdk';sdk.mkdir();shutil.copytree(R/'pynq_z2_tile_v1_53.sdk/ethernet_sources',sdk/'ethernet_sources')
    for name in ('build_ethernet.py','reserve_boot_id.py'):shutil.copy2(R/'pynq_z2_tile_v1_53.sdk'/name,sdk/name)
    (project/'config').mkdir();shutil.copy2(R/'config/reference_v165.json',project/'config/reference_v165.json')
    release=project/'releases/v167';release.mkdir(parents=True);manifest=json.loads((a.bundle/'DEPLOYMENT.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(a.bundle/name)!=digest:raise ValueError('Release artifact changed: '+name)
        shutil.copy2(a.bundle/name,release/name)
    shutil.copy2(a.bundle/'DEPLOYMENT.json',release/'DEPLOYMENT.json')
    for name,digest in manifest['source_sha256'].items():
        if sha(project/name)!=digest:raise ValueError('Required source missing or changed in package: '+name)
    shutil.copytree(a.evidence,a.out/'evidence');demo=a.out/'demo_player';demo.mkdir();(demo/'host').mkdir();(demo/'reports').mkdir()
    for name in ('hdmi_display.ps1','StimulusCommand.cs','ConveyorStimulus.cs'):shutil.copy2(a.player/'host'/name,demo/'host'/name)
    shutil.copytree(a.player/'data/reference_v167',demo/'data/reference_v167');shutil.copy2(a.player/'manifest.json',demo/'manifest.json');(demo/'host/display_command.txt').write_text('ref_000\n')
    shutil.copy2(R/'README_REFERENCE_V167.md',a.out/'README.md');shutil.copy2(R/'scripts/reference_v167/start.ps1',a.out/'start.ps1')
    records={}
    for f in a.out.rglob('*'):
        if not f.is_file():continue
        name=f.relative_to(a.out).as_posix()
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',part) for part in Path(name).parts):raise ValueError('Nonportable path: '+name)
        records[name]=sha(f)
    (a.out/'PACKAGE_MANIFEST.json').write_text(json.dumps(dict(schema=1,scope='COMPETITION_PROTOTYPE_PACKAGE_NOT_PHYSICAL_ACCURACY_CERTIFICATION',files=records),indent=2)+'\n')
    archive=a.out.with_suffix('.zip')
    if archive.exists():raise FileExistsError(archive)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in a.out.rglob('*'):
            if f.is_file():z.write(f,f.relative_to(a.out.parent))
    print(json.dumps(dict(package=str(a.out),archive=str(archive),files=len(records),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size)))
if __name__=='__main__':main()
