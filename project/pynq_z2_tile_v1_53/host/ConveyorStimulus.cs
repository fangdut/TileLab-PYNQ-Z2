// HDMI stimulus only. This class neither detects defects nor reads FPGA results.
// Textures are loaded once; motion and the source frame code share one frame index.
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

public sealed class ConveyorStimulus : FrameworkElement {
    readonly Stopwatch clock = new Stopwatch();
    readonly BitmapSource[] tiles = new BitmapSource[4];
    readonly Brush background = Brush(30,39,44), rail=Brush(79,97,103), roller=Brush(37,47,52);
    readonly Brush shadow=Brush(18,24,26), textBrush=Brush(210,220,225), darkBackground=Brush(8,8,8);
    bool active, real, darkGate, holdout; int step, tileWidth, period;
    TimeSpan lastRender=TimeSpan.MinValue;
    FormattedText title, credit;
    public int SourceFrame { get; private set; }
    public long RenderedFrames { get; private set; }
    public long DrawnFrames { get; private set; }
    public int DrawnSourceFrame { get; private set; }
    double diagnosticBegin,diagnosticEnd;
    // Bounded, opt-in fault injection for acceptance tests. Off on normal startup.
    public void SetDiagnosticHold(double after,double seconds) {
        if(double.IsNaN(after)||double.IsInfinity(after)||double.IsNaN(seconds)||double.IsInfinity(seconds)||after<0||after>60||seconds<0||seconds>10)throw new ArgumentOutOfRangeException();
        diagnosticBegin=after;diagnosticEnd=after+seconds;
    }
    public bool DiagnosticHoldActive { get { double t=clock.Elapsed.TotalSeconds;return active && diagnosticEnd>diagnosticBegin && t>=diagnosticBegin && t<diagnosticEnd; } }
    public double MaxRenderIntervalMs { get; private set; }
    public double PositionSeconds { get { return clock.Elapsed.TotalSeconds; } }
    static Brush Brush(byte r,byte g,byte b) { var v=new SolidColorBrush(Color.FromRgb(r,g,b));v.Freeze();return v; }
    static BitmapSource Load(string p) {
        var b=new BitmapImage();b.BeginInit();b.CacheOption=BitmapCacheOption.OnLoad;
        b.UriSource=new Uri(p);b.EndInit();b.Freeze();return b;
    }
    public ConveyorStimulus() {
        Width=1280;Height=720;ClipToBounds=true;SnapsToDevicePixels=true;UseLayoutRounding=true;
        RenderOptions.SetBitmapScalingMode(this,BitmapScalingMode.NearestNeighbor);
        RenderOptions.SetEdgeMode(this,EdgeMode.Aliased);
    }
    public void Start(string root,string mode) {
        Stop();holdout=mode=="holdout_video";real=mode=="real_video";darkGate=mode=="dark_video";step=mode=="ultrafast"?32:mode=="fast"?16:8;
        tileWidth=(real||darkGate||holdout)?500:560;period=5760/step;
        for(int k=0;k<4;k++)tiles[k]=Load(Path.Combine(root,holdout?"data/independent_mcs2/motion/tile_"+k+".png":darkGate?"data/dark_gate/tile_"+k+".png":real?"data/real_tiles/motion/tile_"+k+".png":"data/conveyor/tile_"+k+".png"));
        title=new FormattedText((holdout?"MCS2 RGB / SYNTHETIC MOTION / EXTERNAL MATERIAL HOLDOUT":darkGate?"SYNTHETIC DARK TILE GATE TEST / GRAY 70 AND 110":real?"REAL PHOTOS / SYNTHETIC MOTION":"SYNTHETIC CONTINUOUS CONVEYOR")+" | "+step*60+" px/s | PRELOADED HDMI SOURCE",CultureInfo.InvariantCulture,FlowDirection.LeftToRight,new Typeface("Segoe UI"),13,textBrush,1.0);
        credit=new FormattedText(holdout?"Vrochidou et al., MCS2 RGB | CC BY 4.0 | Fixed-parameter external holdout; FPGA defect boxes.":real?"MVTec Software GmbH | CC BY-NC-SA 4.0 | Defect boxes are generated only by FPGA.":"Constant speed; no camera dwell. Defect boxes are generated only by FPGA.",CultureInfo.InvariantCulture,FlowDirection.LeftToRight,new Typeface("Segoe UI"),13,textBrush,1.0);
        SourceFrame=0;RenderedFrames=0;DrawnFrames=0;DrawnSourceFrame=0;diagnosticBegin=diagnosticEnd=0;MaxRenderIntervalMs=0;lastRender=TimeSpan.MinValue;
        active=true;clock.Restart();CompositionTarget.Rendering+=Tick;InvalidateVisual();
    }
    public void Stop() { if(active)CompositionTarget.Rendering-=Tick;active=false;clock.Stop(); }
    void Tick(object sender,EventArgs e) {
        if(DiagnosticHoldActive)return;
        var stamp=((RenderingEventArgs)e).RenderingTime;
        if(stamp==lastRender)return;
        if(lastRender!=TimeSpan.MinValue)MaxRenderIntervalMs=Math.Max(MaxRenderIntervalMs,(stamp-lastRender).TotalMilliseconds);
        lastRender=stamp;
        int next=((int)Math.Floor(clock.Elapsed.TotalSeconds*60.0))%period;
        // A 144 Hz primary monitor can raise Rendering more often than this 60 Hz
        // source needs. Do not redraw identical source frames; keep wall-clock motion.
        if(next==SourceFrame && RenderedFrames>0)return;
        SourceFrame=next;
        RenderedFrames++;InvalidateVisual();
    }
    protected override void OnRender(DrawingContext dc) {
        base.OnRender(dc);dc.DrawRectangle(darkGate?darkBackground:background,null,new Rect(0,0,1280,720));
        if(!active)return;
        int n=SourceFrame;
        if(!real && !darkGate && !holdout) {
            dc.DrawRectangle(rail,null,new Rect(0,62,1280,23));dc.DrawRectangle(rail,null,new Rect(0,636,1280,23));
            for(int x=-80;x<1360;x+=80)dc.DrawRectangle(roller,null,new Rect(x+(n*step)%80,92,9,536));
        }
        for(int k=0;k<4;k++) {
            int x=((n*step-k*1440+tileWidth)%5760+5760)%5760-tileWidth;
            if(x>=1280 || x+tileWidth<=0)continue;
            if(!real && !darkGate && !holdout)dc.DrawRectangle(shadow,null,new Rect(x-5,106,tileWidth+11,513));
            dc.DrawImage(tiles[k],new Rect(x,110,tileWidth,500));
        }
        dc.DrawText(title,new Point(24,20));dc.DrawText(credit,new Point(24,680));
        for(int b=0;b<16;b++)dc.DrawRectangle((n&(1<<b))!=0?Brushes.White:Brushes.Black,null,new Rect(1016+b*14,20,12,20));
        DrawnSourceFrame=n;DrawnFrames++; // Actual WPF drawing callback, not merely a timer tick.
    }
}
