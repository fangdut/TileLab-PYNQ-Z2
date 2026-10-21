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
using Screen=System.Windows.Forms.Screen;

public sealed class Photo {
 public string id, file, sha256, label;
}
public static class RealPhotoSource {
 [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr context);
 [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);
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
   if(args.Length==1&&args[0]=="--inventory"){
    var inventory=new List<object>();
    foreach(var s in screens)inventory.Add(new {device=s.DeviceName,primary=s.Primary,x=s.Bounds.X,y=s.Bounds.Y,width=s.Bounds.Width,height=s.Bounds.Height});
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
   var canvas=new Canvas {Width=1280,Height=720,ClipToBounds=true};window.Content=canvas;
   var image=new Image {Width=720,Height=720,Stretch=Stretch.Fill,Source=bitmaps[0]};
   Canvas.SetLeft(image,280);Canvas.SetTop(image,0);canvas.Children.Add(image);
   var text=new TextBlock {Width=250,Foreground=Brushes.White,FontSize=18,TextWrapping=TextWrapping.Wrap};
   Canvas.SetLeft(text,15);Canvas.SetTop(text,30);canvas.Children.Add(text);
   var stamp=new TextBlock {Width=250,Foreground=Brushes.White,FontSize=16,TextWrapping=TextWrapping.Wrap};
   Canvas.SetLeft(stamp,1015);Canvas.SetTop(stamp,30);canvas.Children.Add(stamp);
   string session=Guid.NewGuid().ToString("N");int index=0,changes=0;long frames=0;
   DateTime since=DateTime.UtcNow;bool paused=false,running=true;
   Action publish=()=>{
    Atomic(status,new {scope="REAL_PHOTO_HDMI_SOURCE_ONLY",session=session,utc=DateTime.UtcNow.ToString("o"),
     image_id=photos[index].id,original_file=photos[index].file,original_sha256=photos[index].sha256,
     image_changes=changes,rendered_frames=frames,display_device=target.DeviceName,width=1280,height=720,
     roi_x=280,roi_y=0,roi_width=720,roi_height=720,paused=paused,running=running,cpu_detection=false,gpu_detection=false});
   };
   var timer=new DispatcherTimer {Interval=TimeSpan.FromMilliseconds(250)};
   timer.Tick+=(sender,eventArgs)=>{
    bool stillConnected=false;
    foreach(var screen in Screen.AllScreens)if(screen.DeviceName==target.DeviceName&&!screen.Primary&&screen.Bounds.Width==1280&&screen.Bounds.Height==720)stillConnected=true;
    if(!stillConnected){window.Close();return;}
    if(File.Exists(command)){
     string c=File.ReadAllText(command).Trim();
     if(c=="close"){window.Close();return;}
     paused=c=="pause";
    }
    if(!paused&&(DateTime.UtcNow-since).TotalSeconds>=interval){
     index=(index+1)%photos.Count;changes++;image.Source=bitmaps[index];since=DateTime.UtcNow;
    }
    text.Text="REAL PHOTOGRAPH\nHDMI INPUT ONLY\n\n"+photos[index].id+"\n\nNo PC detection\nFPGA performs inference";
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
