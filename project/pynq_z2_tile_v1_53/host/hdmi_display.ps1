param([string]$Root=(Split-Path $PSScriptRoot -Parent),[ValidateRange(0,10)][double]$DiagnosticHoldSeconds=0,[ValidateRange(0,60)][double]$DiagnosticStartAfterSeconds=3)
$ErrorActionPreference='Stop'
# Prioritize only this stimulus process modestly; never use real-time priority.
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass='AboveNormal'
Add-Type @'
using System;using System.Runtime.InteropServices;
public class TileDisplayDpi {
 [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h,IntPtr after,int x,int y,int w,int hgt,uint flags);
}
'@
[TileDisplayDpi]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null
Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase,System.Windows.Forms
Add-Type -Path (Join-Path $Root 'host/ConveyorStimulus.cs') -ReferencedAssemblies WindowsBase,PresentationCore,PresentationFramework,System.Xaml
Add-Type -Path (Join-Path $Root 'host/StimulusCommand.cs')
$screens=@([System.Windows.Forms.Screen]::AllScreens | Where-Object {!$_.Primary})
if($screens.Count -ne 1 -or $screens[0].Bounds.Width -ne 1280 -or $screens[0].Bounds.Height -ne 720){throw 'Expected one 1280x720 extended HDMI display'}
$b=$screens[0].Bounds
$w=New-Object System.Windows.Window
$w.WindowStyle='None';$w.ResizeMode='NoResize';$w.WindowStartupLocation='Manual'
$w.Left=$b.X;$w.Top=$b.Y;$w.Width=1280;$w.Height=720;$w.Background='Black';$w.Topmost=$true
$w.Title='Tile inspection HDMI stimulus — SYNTHETIC'
# The HDMI stimulus must not contain a desktop pointer over the test image.
# Local to this window: the pointer remains visible on the operator's desktop.
$w.Cursor=[System.Windows.Input.Cursors]::None;$w.ForceCursor=$true
$w.Add_ContentRendered({
 $own=New-Object System.Windows.Interop.WindowInteropHelper($w)
 [TileDisplayDpi]::SetWindowPos($own.Handle,[IntPtr](-1),$b.X,$b.Y,1280,720,0x40) | Out-Null
})
$grid=New-Object System.Windows.Controls.Grid;$w.Content=$grid
$image=New-Object System.Windows.Controls.Image;$image.Stretch='Fill';$grid.Children.Add($image)|Out-Null
function New-TileMedia {
 $element=New-Object System.Windows.Controls.MediaElement
 $element.LoadedBehavior='Manual';$element.UnloadedBehavior='Manual';$element.Stretch='Fill';$element.Volume=0
 $element.ScrubbingEnabled=$true
 $element.Add_MediaEnded({param($sender,$eventArgs);if($sender -eq $script:media){$sender.Position=[TimeSpan]::Zero;$sender.Play()}})
 $element.Add_MediaFailed({param($sender,$eventArgs);if($sender -ne $script:media){return};$script:mediaError=$eventArgs.ErrorException.ToString();([DateTime]::UtcNow.ToString('o')+' '+$script:activeVideo+' '+$script:mediaError) | Add-Content -LiteralPath (Join-Path $Root 'reports/media_failed.log')})
 $element.Add_MediaOpened({param($sender,$eventArgs);if($sender -ne $script:media){return};$sender.Pause();$sender.Position=[TimeSpan]::Zero;$script:phase='priming';$script:playAfter=[DateTime]::UtcNow.AddSeconds(1);$script:opened=[DateTime]::UtcNow.ToString('o');('Opened video '+$sender.NaturalVideoWidth+'x'+$sender.NaturalVideoHeight+' at '+$script:opened) | Add-Content -LiteralPath (Join-Path $Root 'reports/media_opened.log')})
 return $element
}
$script:media=New-TileMedia;$grid.Children.Add($media)|Out-Null
$motion=New-Object ConveyorStimulus;$motion.Visibility='Hidden'
# Match the existing full-frame Image/MediaElement behavior under Windows DPI scaling.
$motionBox=New-Object System.Windows.Controls.Viewbox;$motionBox.Stretch='Fill';$motionBox.Child=$motion;$grid.Children.Add($motionBox)|Out-Null
$script:mediaError=$null;$script:retryCount=0;$script:requested=''
$script:playerSession=[Guid]::NewGuid().ToString('N');$script:startedUtc=[DateTime]::UtcNow.ToString('o')
$script:instancePublished=$false;$script:adoptedRequest=$null;$script:commandVersion=0
$script:last='';$command=Join-Path $Root 'host/display_command.txt'
$script:lastStatusWrite=[DateTime]::MinValue
$script:phase='static';$script:playAfter=$null
$timer=New-Object System.Windows.Threading.DispatcherTimer;$timer.Interval=[TimeSpan]::FromMilliseconds(20)
$timer.Add_Tick({
 if($script:phase -eq 'priming' -and [DateTime]::UtcNow -ge $script:playAfter){$media.Play();$script:phase='playing'}
 if(([DateTime]::UtcNow-$script:lastStatusWrite).TotalMilliseconds -ge 150){
  $position=if($script:phase -eq 'rendering'){$motion.PositionSeconds}else{$media.Position.TotalSeconds}
  # Publish once, retry sharing conflicts without interrupting rendering. A retiring
  # player must never republish its identity over a newer player's marker.
  if(!$script:instancePublished){
   $instancePath=Join-Path $Root 'host/player_instance.json';$instanceTemp=Join-Path $Root ("host/player_instance.$PID.tmp")
   try {
    $instance=@{version=1;session=$script:playerSession;pid=$PID;started_utc=$script:startedUtc}|ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText($instanceTemp,$instance)
    if([System.IO.File]::Exists($instancePath)){[System.IO.File]::Replace($instanceTemp,$instancePath,[System.Management.Automation.Language.NullString]::Value)}else{[System.IO.File]::Move($instanceTemp,$instancePath)}
    $script:instancePublished=$true
   }catch [System.IO.IOException]{}
  }
  $playerState=@{drawn_frames=$motion.DrawnFrames;drawn_source_frame=$motion.DrawnSourceFrame;diagnostic_hold_active=$motion.DiagnosticHoldActive;request_id=$script:adoptedRequest;command_version=$script:commandVersion;player_session=$script:playerSession;player_pid=$PID;source=$script:last;phase=$script:phase;source_file=$script:activeVideo;position_seconds=$position;source_frame=$motion.SourceFrame;rendered_frames=$motion.RenderedFrames;max_render_interval_ms=$motion.MaxRenderIntervalMs;utc=[DateTime]::UtcNow.ToString('o');opened=$script:opened;error=$script:mediaError;retries=$script:retryCount} | ConvertTo-Json -Compress
  # Telemetry must not terminate video if a reader or retiring player holds a file.
  # Replace atomically so readers never observe truncated JSON.
  $statusPath=Join-Path $Root 'host/player_status.json'
  $statusTemp=Join-Path $Root ("host/player_status.$PID.tmp")
  try {
   [System.IO.File]::WriteAllText($statusTemp,$playerState)
   if([System.IO.File]::Exists($statusPath)){[System.IO.File]::Replace($statusTemp,$statusPath,[System.Management.Automation.Language.NullString]::Value)}else{[System.IO.File]::Move($statusTemp,$statusPath)}
  }catch [System.IO.IOException]{}
  $script:lastStatusWrite=[DateTime]::UtcNow
 }
 if([System.IO.File]::Exists($command)){
  # The workstation atomically replaces this command. A short Windows sharing
  # conflict must skip one timer tick, not terminate the HDMI source process.
  try {$commandText=[StimulusCommand]::ReadBounded($command)}catch [System.IO.IOException]{return}catch [System.IO.InvalidDataException]{return}catch [System.Text.DecoderFallbackException]{return}
  $c=$commandText
  if($c -eq 'close'){$w.Close();return}
  $parsed=[StimulusCommand]::Parse($commandText);if($null -eq $parsed){return};$c=$parsed.Source
  if($c -ne $script:requested){$script:requested=$c;$script:retryCount=0;$script:mediaError=$null}
  if($script:mediaError -and $script:retryCount -lt 2 -and $c -in @('video','fast','ultrafast','burst','real_video','holdout_video','calib_video')){$script:last='';$script:mediaError=$null;$script:retryCount++}
  if($c -ne $script:last){
   $motion.Stop();$motion.Visibility='Hidden'
   if($c -in @('video','fast','ultrafast','real_video','holdout_video','dark_video')){
    $media.Stop();$media.Visibility='Hidden';$image.Visibility='Hidden'
    $motion.Start($Root,$c);if($DiagnosticHoldSeconds -gt 0){$motion.SetDiagnosticHold($DiagnosticStartAfterSeconds,$DiagnosticHoldSeconds)};$motion.Visibility='Visible';$script:phase='rendering'
    $script:activeVideo='PRELOADED_TEXTURE_RENDERER';$script:opened=[DateTime]::UtcNow.ToString('o')
   }elseif($c -in @('burst','calib_video')){
    # Reopen even the same URI so a stopped decoder cannot reuse a stale timeline.
    # Pause primes the media; MediaOpened resets its clock before starting playback.
    $oldMedia=$media;$script:media=$null;$oldMedia.Stop();$oldMedia.Close();$grid.Children.Remove($oldMedia)
    $script:media=New-TileMedia;$grid.Children.Add($media)|Out-Null;$script:opened=$null;$script:phase='loading'
    $image.Visibility='Hidden';$media.Visibility='Visible'
    $videoName=if($c -eq 'burst'){'data/burst_SYNTHETIC_720p60.mp4'}elseif($c -eq 'calib_video'){'data/calibration_hdmi_video.mp4'}else{"data/continuous_${c}_720p60.mp4"}
    # A ten-minute stream avoids MediaEnded restarts every 3/6/12 seconds.
    # The source remains constant-motion; no camera-triggered dwell is inserted.
    $longName="data/continuous_${c}_long_720p60.mp4"
    if($c -ne 'burst' -and (Test-Path -LiteralPath (Join-Path $Root $longName))){$videoName=$longName}
    $script:activeVideo=$videoName;$media.Source=[Uri](Join-Path $Root $videoName);$media.Pause()
   }elseif($c -match '^calib_\d{3}$'){
    $script:phase='static'
    $media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'
    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root ('data/calibration_hdmi/'+$c+'.png')))
   }elseif($c -match '^holdout_\d{3}$'){
    $script:phase='static'
    $media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'
    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root ('data/independent_mcs2/hdmi/'+$c+'.png')))
   }elseif($c -match '^real_\d{3}$'){
    $script:phase='static'
    $media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'
    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root ('data/real_tiles/hdmi/'+$c+'.png')))
   }elseif($c -eq 'transport_noise'){
    $script:phase='static';$media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'
    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root 'data/conveyor/transport_noise.png'))
   }elseif($c -match '^station_[0-6]$'){
    $script:phase='static'
    $media.Stop();$media.Visibility='Hidden';$image.Visibility='Visible'
    $image.Source=New-Object System.Windows.Media.Imaging.BitmapImage([Uri](Join-Path $Root ('data/conveyor/'+$c+'.png')))
   }
   $script:last=$c
  }
  # Repeated selection adopts a new ID without restarting continuous motion.
  $script:adoptedRequest=$parsed.RequestId;$script:commandVersion=$parsed.Version
 }
})
$w.Add_KeyDown({if($_.Key -eq 'Escape'){$w.Close()}})
$timer.Start()
try{$w.ShowDialog()|Out-Null}finally{$timer.Stop();$motion.Stop();$media.Close()}
