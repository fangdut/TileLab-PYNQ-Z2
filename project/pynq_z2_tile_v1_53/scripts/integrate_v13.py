from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'rtl/video_bypass.v';s=p.read_text();s=s.replace('output wire [31:0] candidate_count_ref','output wire [831:0] regions_ref,\n output wire [31:0] candidate_count_ref')
a=s.index(' bbox_overlay #(');b=s.index(' video_stats stats',a)
s=s[:a]+''' wire [511:0] region_boxes;wire [255:0] region_areas;wire [31:0] region_seq,region_status;
 region_grid #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) regions(
 .clk(pixel_clk),.control_clk(control_clk),.reset(pixel_reset),.de(d2),.vs(v2),.mask(final_mask),
 .boxes(region_boxes),.areas(region_areas),.result_seq(region_seq),.result_status(region_status),.snapshot_ref(regions_ref));
 reg [15:0] box_x=0,box_y=0;reg box_pd=0,box_pv=0;
 always @(posedge pixel_clk)begin
  if(pixel_reset)begin box_x<=0;box_y<=0;box_pd<=0;box_pv<=0;end
  else begin
   box_pd<=d2;box_pv<=v2;
   if(v2 && !box_pv)begin box_x<=0;box_y<=0;end
   else begin if(d2)box_x<=box_x+1'b1;else box_x<=0;if(box_pd && !d2)box_y<=box_y+1'b1;end
  end
 end
 reg box_edge;integer bi;
 reg [15:0] lx,ly,hx,hy;
 always @*begin
  box_edge=0;lx=0;ly=0;hx=0;hy=0;
  for(bi=0;bi<8;bi=bi+1)begin
   lx=region_boxes[bi*64+:16];ly=region_boxes[bi*64+16+:16];hx=region_boxes[bi*64+32+:16];hy=region_boxes[bi*64+48+:16];
   if(bi<region_status[3:0] && !region_status[31] && (((box_x==lx || box_x==hx) && box_y>=ly && box_y<=hy) || ((box_y==ly || box_y==hy) && box_x>=lx && box_x<=hx)))box_edge=1;
  end
 end
 assign boxed=(d2 && config_active[21] && shown_mode==7 && box_edge)?24'hff0000:shown;
'''+s[b:];p.write_text(s)
p=r/'scripts/add_capture.tcl';s=p.read_text();s+='''
create_bd_cell -type module -reference region_axi regions_regs
net bypass/regions_ref regions_regs/snapshot
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master {/ps7/M_AXI_GP0} Clk_master {/ps7/FCLK_CLK0 (100 MHz)} Clk_slave {/ps7/FCLK_CLK0 (100 MHz)} Clk_xbar {/ps7/FCLK_CLK0 (100 MHz)}} [get_bd_intf_pins regions_regs/S_AXI]
assign_bd_address
set_property offset 0x43C00000 [get_bd_addr_segs ps7/Data/SEG_regions_regs_reg0]
''';p.write_text(s)
