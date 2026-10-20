"""Create a new capture + DDR reference accelerator project, never edit V164."""
from pathlib import Path
import argparse,shutil,hashlib,json
R=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--hls',required=True,type=Path);p.add_argument('--ip-cache',type=Path);a=p.parse_args()
    out=a.out.resolve()
    if out.exists():raise FileExistsError(out)
    ip=a.hls/'solution/impl/ip'
    if not (ip/'component.xml').exists():raise FileNotFoundError(ip)
    cosim=(a.hls/'solution/sim/report/reference_frame_cosim.rpt').read_text()
    if not any('Verilog' in line and 'Pass' in line for line in cosim.splitlines()):raise ValueError('Full-frame RTL cosimulation has not passed')
    for name in ('reference_frame.cpp','test_frame.cpp'):
        if (a.hls/'src'/name).read_bytes()!=(R/'experimental/reference_v167/hls'/name).read_bytes():raise ValueError('HLS source differs from validated build')
    out.mkdir()
    for folder in ('rtl','constraints','scripts','ip_repo'):shutil.copytree(R/folder,out/folder)
    shutil.copytree(ip,out/'ip_repo/reference_frame_v167')
    # Preserve the established interface and CDC/capture/statistics blocks,
    # remove the previous classifier. Reference inspection uses DDR results.
    old=(R/'rtl/video_bypass.v').read_text();head=old[:old.index(' wire [23:0] original,core_original;')]
    lean='''
 xpm_cdc_async_rst #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(1),.RST_ACTIVE_HIGH(1)) reset_bridge(.src_arst(reset),.dest_clk(pixel_clk),.dest_arst(pixel_reset));
 wire [95:0] cfg;wire [31:0] roi_min=cfg[63:32],roi_max=cfg[95:64];
 config_bridge bridge(control_clk,pixel_clk,config_request,roi_min_request,roi_max_request,cfg);
 reg pv=0,pd=0;reg [15:0] x=0,y=0;
 always @(posedge pixel_clk)begin
  if(pixel_reset)begin config_active<=0;pv<=0;pd<=0;x<=0;y<=0;end
  else begin pv<=vs_in;pd<=de_in;
   if(vs_in && !pv)begin config_active<=cfg[31:0];x<=0;y<=0;end
   else begin if(de_in)x<=x+1'b1;else x<=0;if(pd && !de_in)y<=y+1'b1;end
  end
 end
 wire roi_ok=x>=roi_min[15:0] && x<=roi_max[15:0] && y>=roi_min[31:16] && y<=roi_max[31:16];
 wire [9:0] luma={2'b0,rgb_in[23:16]}+{1'b0,rgb_in[7:0],1'b0}+{2'b0,rgb_in[15:8]};
 brightness_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) brightness(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(de_in),.vs(vs_in),.gray(luma[9:2]),.include_pixel(roi_ok),
 .config_word(config_active),.roi_min(roi_min),.roi_max(roi_max),.count_ref(brightness_count_ref),.sum_ref(brightness_sum_ref),.seq_ref(brightness_seq_ref),.config_ref(brightness_config_ref),.min_ref(brightness_min_ref),.max_ref(brightness_max_ref));
 candidate_stats #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) candidates(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(de_in),.vs(vs_in),.mask(1'b0),.config_word(config_active),
 .count_ref(candidate_count_ref),.min_ref(bbox_min_ref),.max_ref(bbox_max_ref),.seq_ref(snapshot_seq_ref),.config_ref(snapshot_config_ref),.status_ref(snapshot_status_ref),.crc_ref(mask_crc_ref));
 region_quality_v157 #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) regions(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(de_in),.vs(vs_in),.mask(1'b0),.trusted_mask(1'b0),.quality_enable(1'b0),
 .boxes(capture_region_boxes),.areas(capture_region_areas),.result_seq(capture_region_seq),.result_status(capture_region_status),.snapshot_ref(regions_ref));
 assign capture_rgb=rgb_in;assign capture_de=de_in;assign capture_vs=vs_in;assign capture_mask=0;
 video_stats stats(pixel_clk,pixel_reset,rgb_in,de_in,hs_in,vs_in,rgb_out,de_out,hs_out,vs_out,frame_count,frame_pixels,frame_lines,line_pixels,format_ok);
 assign out_x=x;assign out_y=y;assign mode_active=0;assign window_valid=de_in;
endmodule
'''
    (out/'rtl/video_bypass.v').write_text(head+lean)
    status=out/'rtl/status_cdc.v';status.write_text(status.read_text().replace('assign source_hpd=hpd_ref;','assign source_hpd=1\'b1; // Receiver EDID is independent of output monitor.'))
    region=out/'rtl/region_axi.v';region.write_text(region.read_text().replace("32'hd06b3b9b","32'h16700601"))
    create=out/'scripts/create_project.tcl';s=create.read_text();key='source $root/scripts/add_capture.tcl\nvalidate_bd_design';assert key in s
    s=s.replace(key,'source $root/scripts/add_capture.tcl\nsource $root/scripts/reference_v167/add_reference.tcl\nvalidate_bd_design')
    if a.ip_cache:
        cache=a.ip_cache.resolve()
        if not cache.is_dir():raise ValueError('IP cache directory is missing')
        s=s.replace('set_property target_language Verilog',f'config_ip_cache -use_cache_location {{{cache.as_posix()}}}\nset_property target_language Verilog',1)
    create.write_text(s)
    (out/'reports').mkdir();(out/'reports/v164').mkdir();(out/'tmp').mkdir();(out/'SINGLE_TILE_BUILD_ONLY').write_text('Isolated V167 project; no automatic programming.\n')
    files=[f for folder in ('rtl','constraints','scripts','ip_repo') for f in (out/folder).rglob('*') if f.is_file()]
    (out/'SOURCE_INPUTS.json').write_text(json.dumps({f.relative_to(out).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2))
    print(out)
if __name__=='__main__':main()
