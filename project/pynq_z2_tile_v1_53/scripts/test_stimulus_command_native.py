"""Compile and exercise the exact parser used by the WPF player."""
from pathlib import Path
import json,subprocess,sys
R=Path(__file__).resolve().parents[1];O=R/'reports/v148/native_stimulus';O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'host'))
from stimulus_command import parse_command,make_command
sources=['video','fast','ultrafast','real_video','holdout_video','dark_video','calib_video','transport_noise','burst']
sources += [f'station_{i}' for i in range(7)]+[f'real_{i:03d}' for i in range(117)]+[f'calib_{i:03d}' for i in range(230)]+[f'holdout_{i:03d}' for i in range(24)]
texts=[]
for source in sources:texts += [source,make_command(source,'a'*32)[0].decode()]
texts += ['','station_7','real_117','calib_230','holdout_024','holdout_００１','real_００１','../real_001','close','real_0','x'*129,'é'*65,
          'TILE_CMD_V1 '+'A'*32+' real_video','TILE_CMD_V1 '+'a'*31+' real_video',
          'TILE_CMD_V1 '+'a'*32+' real_video extra','TILE_CMD_V1\t'+'a'*32+' real_video']
rows=[]
for text in texts:
    try:expected=parse_command(text)
    except ValueError:expected=None
    rows.append(dict(text=text,expected=expected))
(O/'cases.json').write_text(json.dumps(rows,ensure_ascii=True),encoding='utf-8')
script=r'''
param([string]$Root,[string]$Output)
$ErrorActionPreference='Stop'
Add-Type -Path (Join-Path $Root 'host/StimulusCommand.cs')
$cases=Get-Content -LiteralPath (Join-Path $Output 'cases.json') -Raw | ConvertFrom-Json
$count=0
foreach($case in $cases){
 $actual=[StimulusCommand]::Parse($case.text)
 if($null -eq $case.expected){if($null -ne $actual){throw 'Invalid accepted'}}
 elseif($null -eq $actual -or $actual.Source -cne $case.expected.source -or $actual.RequestId -cne $case.expected.request_id -or $actual.Version -ne $case.expected.version){throw ('Parser mismatch: '+$case.text)}
 $count++
}
$file=Join-Path $Output 'command_probe.txt'
$utf8=New-Object System.Text.UTF8Encoding($false,$true)
$valid='TILE_CMD_V1 '+('a'*32)+' real_video'
[System.IO.File]::WriteAllText($file,$valid,$utf8)
if([StimulusCommand]::ReadBounded($file) -cne $valid){throw 'Read mismatch'}
$handle=[System.IO.File]::Open($file,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::None)
try {
 $caught=$false
 try{[StimulusCommand]::ReadBounded($file)|Out-Null}catch [System.IO.IOException]{$caught=$true}
 if(!$caught){throw 'Exclusive lock not detected'}
}finally{$handle.Dispose()}
foreach($bytes in @([byte[]](0xff),[System.Text.Encoding]::UTF8.GetBytes(('x'*129)))){
 [System.IO.File]::WriteAllBytes($file,$bytes);$caught=$false
 try{[StimulusCommand]::ReadBounded($file)|Out-Null}catch [System.IO.IOException]{$caught=$true}catch [System.IO.InvalidDataException]{$caught=$true}catch [System.Text.DecoderFallbackException]{$caught=$true}
 if(!$caught){throw 'Invalid bytes accepted'}
}
# A real atomic replacement remains readable with the requested sharing flags.
[System.IO.File]::WriteAllText($file,$valid,$utf8)
$other=$file+'.new';[System.IO.File]::WriteAllText($other,'station_6',$utf8)
[System.IO.File]::Replace($other,$file,[System.Management.Automation.Language.NullString]::Value)
if([StimulusCommand]::Parse([StimulusCommand]::ReadBounded($file)).Source -cne 'station_6'){throw 'Replace failed'}
# Parse the actual player script without launching a second player.
$tokens=$null;$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $Root 'host/hdmi_display.ps1'),[ref]$tokens,[ref]$errors)|Out-Null
if($errors.Count){throw ($errors|Out-String)}
Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase
Add-Type -Path (Join-Path $Root 'host/ConveyorStimulus.cs') -ReferencedAssemblies WindowsBase,PresentationCore,PresentationFramework,System.Xaml
$motion=New-Object ConveyorStimulus
if($motion.DrawnFrames -ne 0 -or $motion.DiagnosticHoldActive){throw 'Unexpected initial renderer state'}
$motion.SetDiagnosticHold(3,8)
foreach($pair in @(@(-1,1),@(1,-1),@(61,1),@(1,11),@([double]::NaN,1),@(1,[double]::PositiveInfinity))){
 $caught=$false
 try{$motion.SetDiagnosticHold($pair[0],$pair[1])}catch [System.ArgumentOutOfRangeException]{$caught=$true}
 if(!$caught){throw 'Unbounded diagnostic hold accepted'}
}
@{passed=$true;catalog_parsing_cases=$count;exclusive_file_lock=$true;invalid_encoding_and_bound=$true;atomic_replacement=$true;player_script_syntax=$true;actual_renderer_compiled=$true;diagnostic_bounds_rejected=6}|ConvertTo-Json
'''
(O/'native_test.ps1').write_text(script,encoding='utf-8-sig')
proc=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(O/'native_test.ps1'),'-Root',str(R),'-Output',str(O)],capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=0x08000000)
(O/'output.log').write_text(proc.stdout+proc.stderr,encoding='utf-8');print(proc.stdout,proc.stderr)
assert proc.returncode==0
result=json.loads(proc.stdout);assert result['passed'];(O/'summary.json').write_text(json.dumps(result,indent=2))
