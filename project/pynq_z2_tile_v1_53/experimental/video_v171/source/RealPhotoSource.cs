// SPDX-License-Identifier: MIT
// HDMI INPUT GENERATOR ONLY. It decodes/displays original photos; no detector.
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Windows.Interop;
using Screen=System.Windows.Forms.Screen;

public sealed class Photo {
 public string id, file, sha256, label;
}
public static class RealPhotoSource {
 [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr context);
 [DllImport("user32.dll")] static extern IntPtr GetThreadDpiAwarenessContext();
 [DllImport("user32.dll")] static extern int GetAwarenessFromDpiAwarenessContext(IntPtr context);
 [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);
 [StructLayout(LayoutKind.Sequential)] struct Rect {public int left,top,right,bottom;}
 [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr window,out Rect rect);
 [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr window,IntPtr after,int x,int y,int width,int height,uint flags);
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct DevMode {
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string device;
  public ushort spec,driver,size,extra;public uint fields;
  public int x,y;public uint orientation,fixedOutput;
  public short color,duplex,yResolution,ttOption,collate;
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string form;
  public ushort logPixels;
  public uint bits,width,height,flags,frequency,icmMethod,icmIntent,media,dither,reserved1,reserved2,panningWidth,panningHeight;
 }
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern bool EnumDisplaySettings(string device,int mode,ref DevMode value);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int ChangeDisplaySettingsEx(string device,ref DevMode value,IntPtr window,uint flags,IntPtr parameter);
 static void Set720p(Screen[] screens){
  Screen target=null;
  foreach(var s in screens)if(!s.Primary){if(target!=null)throw new InvalidOperationException("Expected one external display");target=s;}
  if(target==null)throw new InvalidOperationException("No external display; no mode changed");
  var current=new DevMode();current.size=(ushort)Marshal.SizeOf(typeof(DevMode));
  if(!EnumDisplaySettings(target.DeviceName,-1,ref current))throw new InvalidOperationException("Cannot read external display mode");
  bool supported=false;
  for(int i=0;i<1000;i++){
   var mode=new DevMode();mode.size=(ushort)Marshal.SizeOf(typeof(DevMode));
   if(!EnumDisplaySettings(target.DeviceName,i,ref mode))break;
   if(mode.width==1280&&mode.height==720&&mode.frequency==60&&mode.bits==current.bits){supported=true;break;}
  }
  if(!supported)throw new InvalidOperationException("External display does not advertise 1280x720 at 60 Hz; no mode changed");
  Console.WriteLine(Json.Serialize(new {scope="EXTERNAL_SOURCE_DISPLAY_MODE_ONLY",device=target.DeviceName,
   previous_width=current.width,previous_height=current.height,previous_hz=current.frequency}));
  current.width=1280;current.height=720;current.frequency=60;
  current.fields=0x00080000u|0x00100000u|0x00400000u;
  int test=ChangeDisplaySettingsEx(target.DeviceName,ref current,IntPtr.Zero,2,IntPtr.Zero);
  if(test!=0)throw new InvalidOperationException("Display mode test rejected: "+test);
  int applied=ChangeDisplaySettingsEx(target.DeviceName,ref current,IntPtr.Zero,0,IntPtr.Zero);
  if(applied!=0)throw new InvalidOperationException("Display mode change rejected: "+applied);
  Console.WriteLine("EXTERNAL_720P60_MODE_APPLIED_TEMPORARILY");
 }
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static string Hash(string path){
  using(var sha=SHA256.Create())using(var stream=File.OpenRead(path))
   return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
 }
 static void Atomic(string path,object value){
  string temp=path+".tmp";File.WriteAllText(temp,Json.Serialize(value));
  if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);
 }
 [STAThread] public static int Main(string[] args){
  try{
   SetProcessDpiAwarenessContext(new IntPtr(-4));
   var screens=Screen.AllScreens;
   if(args.Length==1&&args[0]=="--set720p"){Set720p(screens);return 0;}
   if(args.Length==1&&args[0]=="--inventory"){
    var inventory=new List<object>();
    foreach(var s in screens){
     var mode=new DevMode();mode.size=(ushort)Marshal.SizeOf(typeof(DevMode));
     if(!EnumDisplaySettings(s.DeviceName,-1,ref mode))throw new InvalidOperationException("Cannot inspect current display mode");
     inventory.Add(new {device=s.DeviceName,primary=s.Primary,x=s.Bounds.X,y=s.Bounds.Y,width=s.Bounds.Width,height=s.Bounds.Height,
      physical_width=mode.width,physical_height=mode.height,physical_hz=mode.frequency,dpi_awareness=GetAwarenessFromDpiAwarenessContext(GetThreadDpiAwarenessContext())});
    }
    Console.WriteLine(Json.Serialize(inventory));return 0;
   }
   if(args.Length<2)throw new ArgumentException("Usage: RealPhotoSource.exe catalog.json status.json [seconds_per_photo] [command_file]");
   string catalog=Path.GetFullPath(args[0]),status=Path.GetFullPath(args[1]);
   string command=args.Length>3?Path.GetFullPath(args[3]):status+".command";
   double interval=args.Length>2?double.Parse(args[2],System.Globalization.CultureInfo.InvariantCulture):4;
   if(interval<1||interval>60)throw new ArgumentException("Use a 1-60 second display interval");
   var photos=Json.Deserialize<List<Photo>>(File.ReadAllText(catalog));
   if(photos==null||photos.Count<1)throw new ArgumentException("Empty photo catalog");
   Screen target=null;
   foreach(var s in screens)if(!s.Primary){if(target!=null)throw new InvalidOperationException("Expected exactly one external display");target=s;}
   if(target==null||target.Bounds.Width!=1280||target.Bounds.Height!=720)
    throw new InvalidOperationException("Expected one external 1280x720 HDMI display; no window opened");
   var bitmaps=new List<BitmapImage>();
   foreach(var p in photos){
    if(!Path.IsPathRooted(p.file)||Hash(p.file)!=p.sha256)throw new InvalidDataException("Original photo SHA256 mismatch: "+p.id);
    var bitmap=new BitmapImage();bitmap.BeginInit();bitmap.CacheOption=BitmapCacheOption.OnLoad;
    bitmap.UriSource=new Uri(p.file);bitmap.EndInit();bitmap.Freeze();bitmaps.Add(bitmap);
   }
   Directory.CreateDirectory(Path.GetDirectoryName(status));
   var app=new Application();
   var window=new Window {Title="TileLab real-photo HDMI source (no detection)",WindowStyle=WindowStyle.None,
    ResizeMode=ResizeMode.NoResize,WindowStartupLocation=WindowStartupLocation.Manual,Left=target.Bounds.X,Top=target.Bounds.Y,
    Width=1280,Height=720,Background=Brushes.Black,Topmost=true,Cursor=Cursors.None};
   var canvas=new Canvas {Width=1280,Height=720,ClipToBounds=true};
   window.Content=new Viewbox {Stretch=Stretch.Fill,Child=canvas};
   IntPtr handle=IntPtr.Zero;
   window.SourceInitialized+=(sender,eventArgs)=>{handle=new WindowInteropHelper(window).Handle;};
   Action place=()=>{
    if(handle!=IntPtr.Zero&&!SetWindowPos(handle,new IntPtr(-1),target.Bounds.X,target.Bounds.Y,1280,720,0x10))
     throw new InvalidOperationException("Cannot place the input generator on the exact external pixel bounds");
   };
   window.Loaded+=(sender,eventArgs)=>{place();};
   var image=new Image {Width=720,Height=720,Stretch=Stretch.Fill,Source=bitmaps[0]};
   byte[] ramp=new byte[720*720*3];
   for(int y=0;y<720;y++)for(int x=0;x<720;x++){
    byte v=(byte)(x<104?0:x>=616?255:(x-104)/2);
    for(int c=0;c<3;c++)ramp[(y*720+x)*3+c]=v;
   }
   var calibrationBitmap=BitmapSource.Create(720,720,96,96,PixelFormats.Rgb24,null,ramp,720*3);calibrationBitmap.Freeze();
   Canvas.SetLeft(image,280);Canvas.SetTop(image,0);canvas.Children.Add(image);
   var text=new TextBlock {Width=250,Foreground=Brushes.White,FontSize=18,TextWrapping=TextWrapping.Wrap};
   Canvas.SetLeft(text,15);Canvas.SetTop(text,30);canvas.Children.Add(text);
   var stamp=new TextBlock {Width=250,Foreground=Brushes.White,FontSize=16,TextWrapping=TextWrapping.Wrap};
   Canvas.SetLeft(stamp,1015);Canvas.SetTop(stamp,30);canvas.Children.Add(stamp);
   string session=Guid.NewGuid().ToString("N");int index=0,changes=0;long frames=0;
   DateTime since=DateTime.UtcNow;bool paused=false,running=true,calibration=false;
   Action publish=()=>{
    Rect rect=new Rect();bool positioned=handle!=IntPtr.Zero&&GetWindowRect(handle,out rect);
    if(!positioned)rect=new Rect();
    Atomic(status,new {scope=calibration?"HDMI_CALIBRATION_PATTERN_ONLY":"REAL_PHOTO_HDMI_SOURCE_ONLY",session=session,utc=DateTime.UtcNow.ToString("o"),
     image_id=calibration?"HDMI_GRAY_RAMP":photos[index].id,original_file=calibration?null:photos[index].file,original_sha256=calibration?null:photos[index].sha256,
     image_changes=changes,rendered_frames=frames,display_device=target.DeviceName,width=1280,height=720,
     roi_x=280,roi_y=0,roi_width=720,roi_height=720,paused=paused,running=running,calibration_pattern=calibration,
     window_x=rect.left,window_y=rect.top,window_width=rect.right-rect.left,window_height=rect.bottom-rect.top,
     physical_window_bounds_verified=positioned&&rect.left==target.Bounds.X&&rect.top==target.Bounds.Y&&rect.right-rect.left==1280&&rect.bottom-rect.top==720,
     cpu_detection=false,gpu_detection=false});
   };
   var timer=new DispatcherTimer {Interval=TimeSpan.FromMilliseconds(250)};
   timer.Tick+=(sender,eventArgs)=>{
    bool stillConnected=false;
    foreach(var screen in Screen.AllScreens)if(screen.DeviceName==target.DeviceName&&!screen.Primary&&screen.Bounds.Width==1280&&screen.Bounds.Height==720)stillConnected=true;
    if(!stillConnected){window.Close();return;}
    if(File.Exists(command)){
     string c=File.ReadAllText(command).Trim();
     if(c=="close"){window.Close();return;}
     calibration=c=="calibrate";paused=calibration||c=="pause";
     if(c.StartsWith("photo:")){
      string id=c.Substring(6);int selected=photos.FindIndex(p=>p.id==id);
      if(selected<0)throw new InvalidDataException("Unknown playback photo: "+id);
      index=selected;paused=true;calibration=false;
     }
     image.Source=calibration?(ImageSource)calibrationBitmap:bitmaps[index];
     RenderOptions.SetBitmapScalingMode(image,calibration?BitmapScalingMode.NearestNeighbor:BitmapScalingMode.LowQuality);
    }
    if(!paused&&(DateTime.UtcNow-since).TotalSeconds>=interval){
     index=(index+1)%photos.Count;changes++;image.Source=bitmaps[index];since=DateTime.UtcNow;
    }
    text.Text=(calibration?"CALIBRATION PATTERN":"REAL PHOTOGRAPH")+"\nHDMI INPUT ONLY\n\n"+(calibration?"HDMI_GRAY_RAMP":photos[index].id)+"\n\nNo PC detection\nFPGA performs inference";
    stamp.Text="Playback counter: "+frames+"\nPhoto change: "+changes+"\n"+DateTime.UtcNow.ToString("HH:mm:ss.fff");
    try{publish();}catch(IOException){}
   };
   CompositionTarget.Rendering+=(sender,eventArgs)=>{frames++;};
   window.KeyDown+=(sender,eventArgs)=>{if(eventArgs.Key==Key.Escape)window.Close();};
   window.Closed+=(sender,eventArgs)=>{running=false;timer.Stop();try{publish();}catch(IOException){}app.Shutdown();};
   SetThreadExecutionState(0x80000003u);
   try{timer.Start();publish();app.Run(window);}finally{SetThreadExecutionState(0x80000000u);}
   return 0;
  }catch(Exception error){Console.Error.WriteLine(error.ToString());return 1;}
 }
}
