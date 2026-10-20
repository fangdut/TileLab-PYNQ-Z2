"""Prepare an isolated HDMI player with labeled procedural reference cases."""
from pathlib import Path
import argparse,shutil,sys,json,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/reference_tile'))
import fixtures
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.out/'host';data=a.out/'data/reference_v167';host.mkdir();data.mkdir(parents=True);(a.out/'reports').mkdir()
    for name in ('ConveyorStimulus.cs','StimulusCommand.cs','hdmi_display.ps1'):shutil.copy2(R/'host'/name,host/name)
    cs=host/'StimulusCommand.cs';s=cs.read_text().replace('station_|real_|calib_|holdout_','station_|real_|calib_|holdout_|ref_').replace('prefix=="station_"?7:', 'prefix=="station_"?7:prefix=="ref_"?1000:');cs.write_text(s)
    ps=host/'hdmi_display.ps1';s=ps.read_text();key="   }elseif($c -match '^real_\\d{3}$'){";assert key in s
    s=s.replace(key,"""   }elseif($c -match '^ref_\\d{3}$'){
    $script:phase='static';$media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'
    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root ('data/reference_v167/'+$c+'.png')))
"""+key,1);ps.write_text(s)
    rows=[]
    for style in fixtures.STYLES:
        ref=fixtures.frame(style);defect,truth=fixtures.add_defect(ref,width=2)
        for kind,image,gt in [('reference',ref,None),('good',fixtures.capture(ref,dx=.75,dy=-.5,noise=.7),None),('line',fixtures.capture(defect,dx=.75,dy=-.5,noise=.7),truth),('invalid_pose',fixtures.capture(ref,dx=6),None)]:
            source=f'ref_{len(rows):03}';f=data/(source+'.png');Image.fromarray(image).save(f)
            if gt is not None:Image.fromarray(gt.astype('uint8')*255).save(data/(source+'_truth.png'))
            rows.append(dict(source=source,style=style,kind=kind,image_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),reference_source=f'ref_{len(rows)//4*4:03}',scope='PROCEDURAL_NOT_REAL_PHOTOGRAPH_NOT_INDEPENDENT_ACCURACY'))
    (a.out/'manifest.json').write_text(json.dumps(dict(scope='HDMI_PROCEDURAL_ENGINEERING_REPLAY',rows=rows),indent=2))
    (host/'display_command.txt').write_text('ref_000\n');print(a.out)
if __name__=='__main__':main()
