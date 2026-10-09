from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
p=R/'sim/tb_capture_sg.sv';s=p.read_text().replace("32'h54465334","32'h54465335")
p.write_text(s)
s=s.replace('module tb_capture_sg;','module tb_capture_crc;')
s=s.replace('integer got=0,nword=0,i,j,k;', 'integer output_file; initial output_file=$fopen("crc_packets.hex","w");\n integer got=0,nword=0,i,j,k;')
s=s.replace('mem[nword]=data;nword=nword+1;','mem[nword]=data;nword=nword+1;\n    $fwrite(output_file,"%08x %01x\\n",data,last);')
s=s.replace("rgb=bright?24'hc0c0c0:24'h202020;", "rgb=bright?(24'ha0a0a0|((i*731+j*613+id*98765)&24'h1f1f1f)):(24'h101010|((i*17+j*91+id*1345)&24'h0f0f0f));")
s=s.replace('repeat(200)@(negedge clk);','repeat(9)@(negedge clk);ready=0;repeat(7)@(negedge clk);ready=1;repeat(200)@(negedge clk);')
s=s.replace('$display("PASS continuous SG', '$fclose(output_file);$display("PASS continuous SG')
(R/'sim/tb_capture_crc.sv').write_text(s)
p=R/'scripts/test_capture_sg.tcl';s=p.read_text().replace('sg_test','crc_test').replace('reports/v15/sg_sim','reports/v132/crc_sim').replace('tb_capture_sg','tb_capture_crc')
(R/'scripts/test_capture_crc.tcl').write_text(s)
plan=json.loads((R/'ITERATION_PLAN.json').read_text());plan['hardware']='V1.11 PL full-frame CRC, build pending';(R/'ITERATION_PLAN.json').write_text(json.dumps(plan,indent=2))
