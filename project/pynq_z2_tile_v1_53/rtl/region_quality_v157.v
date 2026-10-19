// V157 regional evidence filter. Raw pixel candidates remain available; only qualified regions trigger product alarms.
// FPGA-only 8-connected components on occupied 32x32 cells.
// Exact candidate counts/extrema are retained inside each cell. Consequently
// returned rectangles are pixel-accurate, but nearby separate objects can merge
// at the CELL resolution. This is explicitly not pixel-level CCL or YOLO.
// Flood fill runs during vertical blanking; at most CELLS nodes are enqueued.
module region_quality_v157 #(parameter WIDTH=1280, HEIGHT=720, SHIFT=5, BOXES=8, MIN_TRUSTED=16, EVIDENCE_SHIFT=2)(
 input wire clk,control_clk,reset,de,vs,mask,
 input wire trusted_mask,quality_enable,
 output reg [BOXES*64-1:0] boxes=0,
 output reg [BOXES*32-1:0] areas=0,
 output reg [31:0] result_seq=0,result_status=0,
 output wire [BOXES*96+64-1:0] snapshot_ref);
 localparam GW=(WIDTH+(1<<SHIFT)-1)>>SHIFT, GH=(HEIGHT+(1<<SHIFT)-1)>>SHIFT;
 localparam CELLS=GW*GH, AW=$clog2(CELLS+1), CW=22+4*SHIFT;
 reg [CELLS-1:0] occupied=0,visited=0;
 reg [10:0] row_count[0:GW-1],row_trusted[0:GW-1];
 reg frame_quality=0;reg [31:0] trusted_count=0;
 reg [SHIFT-1:0] row_x0[0:GW-1],row_x1[0:GW-1],row_y0[0:GW-1],row_y1[0:GW-1];
 (* ram_style="block" *) reg [CW-1:0] cells[0:CELLS-1];
 (* ram_style="block" *) reg [AW-1:0] queue[0:CELLS-1];
 reg [CW-1:0] cell_q=0;reg [AW-1:0] queue_q=0;
 reg [15:0] x=0,y=0;reg pd=0,pv=0,started=0;
 reg [31:0] frame_id=0,working_seq=0,pixels=0;
 reg flush=0,flush_final=0;reg [7:0] flush_col=0;reg [AW-1:0] flush_base=0;
 localparam IDLE=0,SCAN=1,POP=2,WAITQ=3,READCELL=4,ADD=5,NEIGHBOR=6,FINISH=7,DONE=8;
 reg [3:0] state=IDLE;reg [AW-1:0] scan=0,head=0,tail=0,node=0;
 reg [7:0] scan_x=0,scan_y=0,cx=0,cy=0;
 reg [3:0] neighbor=0,nbox=0;reg overflow=0,bad=0;
 reg [31:0] count=0;reg [15:0] minx=0,miny=0,maxx=0,maxy=0;
 reg [BOXES*64-1:0] work_boxes=0;reg [BOXES*32-1:0] work_areas=0;
 reg signed [9:0] nx,ny;reg [AW-1:0] next_node;
 reg publish=0;integer i;
 wire [7:0] col=x>>SHIFT;
 wire [AW-1:0] cell_index=(y>>SHIFT)*GW+col;
 wire [10:0] cell_count=cell_q[4*SHIFT+:11];
 wire [10:0] cell_trusted=cell_q[4*SHIFT+11+:11];
 wire [15:0] cell_x0=(cx<<SHIFT)+cell_q[SHIFT-1:0];
 wire [15:0] cell_x1=(cx<<SHIFT)+cell_q[2*SHIFT-1:SHIFT];
 wire [15:0] cell_y0=(cy<<SHIFT)+cell_q[3*SHIFT-1:2*SHIFT];
 wire [15:0] cell_y1=(cy<<SHIFT)+cell_q[4*SHIFT-1:3*SHIFT];
 // A single muxed write port plus one synchronous read port infers BRAM.
 // Two independent indexed assignments were interpreted as two write ports
 // plus a read port, expanding 920 queue entries into FFs and a long CE path.
 wire queue_seed=state==SCAN && scan<CELLS && occupied[scan] && !visited[scan];
 wire queue_push=state==NEIGHBOR && nx>=0 && nx<GW && ny>=0 && ny<GH && occupied[next_node] && !visited[next_node] && tail<CELLS;
 wire [AW-1:0] queue_write_address=queue_seed?{AW{1'b0}}:tail;
 wire [AW-1:0] queue_write_data=queue_seed?scan:next_node;
 always @* begin
  nx=$signed({2'b0,cx});ny=$signed({2'b0,cy});
  case(neighbor)
   0:begin nx=nx-1;ny=ny-1;end 1:ny=ny-1; 2:begin nx=nx+1;ny=ny-1;end
   3:nx=nx-1;4:nx=nx+1;5:begin nx=nx-1;ny=ny+1;end
   6:ny=ny+1;7:begin nx=nx+1;ny=ny+1;end
  endcase
  next_node=ny*GW+nx;
 end
 // Independent synchronous RAM read ports. No asynchronous frame-sized mux.
 always @(posedge clk)begin
  if(state==POP)queue_q<=queue[head];
  if(state==READCELL)cell_q<=cells[node];
  if(flush)cells[flush_base+flush_col]<={row_trusted[flush_col],row_count[flush_col],row_y1[flush_col],row_y0[flush_col],row_x1[flush_col],row_x0[flush_col]};
  if(queue_seed || queue_push)queue[queue_write_address]<=queue_write_data;
 end
 always @(posedge clk)begin
  publish<=0;
  if(reset)begin
   x<=0;y<=0;pd<=0;pv<=0;started<=0;pixels<=0;flush<=0;state<=IDLE;
   occupied<=0;visited<=0;boxes<=0;areas<=0;result_status<=0;bad<=0;frame_quality<=0;trusted_count<=0;
   for(i=0;i<GW;i=i+1)begin row_count[i]<=0;row_trusted[i]<=0;row_x0[i]<=0;row_x1[i]<=0;row_y0[i]<=0;row_y1[i]<=0;end
  end else begin
   pd<=de;pv<=vs;
   if(vs && !pv)begin x<=0;y<=0;frame_id<=frame_id+1'b1;pixels<=0;started<=1;end
   else begin
    if(de)begin x<=x+1'b1;pixels<=pixels+1'b1;end else x<=0;
    if(pd && !de)y<=y+1'b1;
   end
   if(de && state!=IDLE)bad<=1;
   // Sample policy at the first accepted pixel, after the pipeline has applied its frame configuration.
   if(de && started && pixels==0 && state==IDLE)frame_quality<=quality_enable;
   if(de && started && x<WIDTH && y<HEIGHT && mask && state==IDLE)begin
    occupied[cell_index]<=1;row_count[col]<=row_count[col]+1'b1;
    if(trusted_mask)row_trusted[col]<=row_trusted[col]+1'b1;
    if(row_count[col]==0)begin row_x0[col]<=x[SHIFT-1:0];row_x1[col]<=x[SHIFT-1:0];row_y0[col]<=y[SHIFT-1:0];row_y1[col]<=y[SHIFT-1:0];end
    else begin
     if(x[SHIFT-1:0]<row_x0[col])row_x0[col]<=x[SHIFT-1:0];
     if(x[SHIFT-1:0]>row_x1[col])row_x1[col]<=x[SHIFT-1:0];
     if(y[SHIFT-1:0]<row_y0[col])row_y0[col]<=y[SHIFT-1:0];
     if(y[SHIFT-1:0]>row_y1[col])row_y1[col]<=y[SHIFT-1:0];
    end
   end
   if(pd && !de && started && (y[SHIFT-1:0]==(1<<SHIFT)-1 || y==HEIGHT-1) && state==IDLE)begin
    flush<=1;flush_col<=0;flush_base<=(y>>SHIFT)*GW;flush_final<=y==HEIGHT-1;
    if(y==HEIGHT-1)begin working_seq<=frame_id;bad<=pixels!=WIDTH*HEIGHT;end
   end
   if(flush)begin
    row_count[flush_col]<=0;row_trusted[flush_col]<=0;
    if(flush_col==GW-1)begin
     flush<=0;
     if(flush_final)begin state<=SCAN;scan<=0;scan_x<=0;scan_y<=0;visited<=0;nbox<=0;overflow<=0;work_boxes<=0;work_areas<=0;end
    end else flush_col<=flush_col+1'b1;
   end
   case(state)
    SCAN:begin
     if(scan==CELLS)state<=DONE;
     else if(occupied[scan] && !visited[scan])begin
      visited[scan]<=1;head<=0;tail<=1;count<=0;trusted_count<=0;minx<=16'hffff;miny<=16'hffff;maxx<=0;maxy<=0;state<=POP;
     end else begin scan<=scan+1'b1;end
    end
    POP:begin if(head==tail)state<=FINISH;else state<=WAITQ;end
    WAITQ:begin node<=queue_q;cx<=queue_q%GW;cy<=queue_q/GW;head<=head+1'b1;state<=READCELL;end
    READCELL:state<=ADD;
    ADD:begin
     count<=count+cell_count;trusted_count<=trusted_count+cell_trusted;
     if(cell_x0<minx)minx<=cell_x0;if(cell_x1>maxx)maxx<=cell_x1;
     if(cell_y0<miny)miny<=cell_y0;if(cell_y1>maxy)maxy<=cell_y1;
     neighbor<=0;state<=NEIGHBOR;
    end
    NEIGHBOR:begin
     if(nx>=0 && nx<GW && ny>=0 && ny<GH && occupied[next_node] && !visited[next_node])begin
      if(tail<CELLS)begin visited[next_node]<=1;tail<=tail+1'b1;end else bad<=1;
     end
     if(neighbor==7)state<=POP;else neighbor<=neighbor+1'b1;
    end
    FINISH:begin
     if(count>=32 && (maxx-minx>=23 || maxy-miny>=23) && (!frame_quality || (trusted_count>=MIN_TRUSTED && (trusted_count<<EVIDENCE_SHIFT)>=count)))begin
      if(nbox<BOXES)begin work_boxes[nbox*64+:64]<={maxy,maxx,miny,minx};work_areas[nbox*32+:32]<=count;nbox<=nbox+1'b1;end
      else overflow<=1;
     end
     scan<=scan+1'b1;state<=SCAN;
    end
    DONE:begin
     boxes<=bad?0:work_boxes;areas<=bad?0:work_areas;result_seq<=working_seq;
     result_status<={bad,22'b0,overflow,4'b0,nbox};publish<=1;
     occupied<=0;visited<=0;state<=IDLE;
    end
   endcase
  end
 end
 localparam SW=BOXES*96+64;
 reg [SW-1:0] held=0;reg send=0;wire received;
 always @(posedge clk)begin
  if(send && received)send<=0;
  if(publish && !send && !received)begin held<={areas,boxes,result_status,result_seq};send<=1;end
 end
 xpm_cdc_handshake #(.DEST_EXT_HSK(0),.DEST_SYNC_FF(4),.SRC_SYNC_FF(4),.WIDTH(SW),.INIT_SYNC_FF(1))
 cdc(.src_clk(clk),.src_in(held),.src_send(send),.src_rcv(received),.dest_clk(control_clk),.dest_out(snapshot_ref),.dest_req(),.dest_ack(1'b0));
endmodule
