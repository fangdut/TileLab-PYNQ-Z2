from pathlib import Path
import hashlib,json,re
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
s=(P/'experimental/texture_v170/hls/frozen/v170_hls63.cpp').read_text()
helper='''// Decode the supported raw32-bit opcode once, before the long-lived control
// phase. Unsupported values map to0 and retain the original task error3.
static ap_uint<3> decode_operation(uint32_t raw){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    ap_uint<3> flags=0;
    if(raw==1)flags=1;
    else if(raw==2)flags=2;
    else if(raw==3)flags=4;
    return flags;
}
'''
needle='static int clampi(';assert s.count(needle)==1;s=s.replace(needle,helper+'\n'+needle)
old='pack_t *__restrict cache,bool nearest,const i16 query[64],int count,uint64_t &best){';assert s.count(old)==1;s=s.replace(old,'pack_t *__restrict cache,bool nearest,bool depth,const i16 query[64],int count,uint64_t &best){')
old='    bool depth=t[0]==2;\n';assert s.count(old)==1;s=s.replace(old,'')
old='        bool nearest=phase>=h[2];';assert s.count(old)==1;s=s.replace(old,old+'\n        ap_uint<3> operation=0;')
old='            if(t[0]==3)add(work,t);';assert s.count(old)==1;s=s.replace(old,'            operation=decode_operation(t[0]);\n            if(operation[2])add(work,t);')
old='        if(nearest||t[0]==1||t[0]==2){';assert s.count(old)==1;s=s.replace(old,'        if(nearest||operation[0]||operation[1]){')
old='conv(model,work,t,ram,line,projection_cache,nearest,query,int(count),best)';assert s.count(old)==1;s=s.replace(old,'conv(model,work,t,ram,line,projection_cache,nearest,bool(operation[1]),query,int(count),best)')
old='        }else if(t[0]!=3){result[1]=3;return;}';assert s.count(old)==1;s=s.replace(old,'        }else if(!operation[2]){result[1]=3;return;}')
assert len(re.findall(r'\bt\[0\]',s))==1
b=P/'experimental/control_decode_v182';b.mkdir(exist_ok=False);source=b/'texture_control_decode.cpp';source.write_text(s)
frozen=P/'experimental/texture_v170/hls/frozen/v170_hls64.cpp';assert not frozen.exists();frozen.write_bytes(source.read_bytes())
tcl=(P/'experimental/residual_stream_v181/build_hls.tcl').read_text().replace('v170_hls63.cpp','v170_hls64.cpp').replace('residual_stream_v181/texture_residual_stream.cpp','control_decode_v182/texture_control_decode.cpp');(b/'build_hls.tcl').write_text(tcl)
for oldfile,newfile,pairs in [
 ('start_v181_residual_full_c.py','start_v182_decode_full_c.py',[('v181_residual_full_c.log','v182_decode_full_c.log'),('residual_stream_v181/texture_residual_stream.cpp','control_decode_v182/texture_control_decode.cpp'),('v181_full_c01','v182_full_c01'),('v181_all_c01','v182_all_c01')]),
 ('start_v181_hls63_synth.py','start_v182_hls64_synth.py',[('v170_hls63','v170_hls64'),('residual_stream_v181/build_hls.tcl','control_decode_v182/build_hls.tcl')])]:
    text=(W/oldfile).read_text()
    for a,c in pairs:assert a in text;text=text.replace(a,c)
    out=W/newfile;assert not out.exists();out.write_text(text)
report=W/'v180_hw01/timing_summary.rpt';text=report.read_text();assert 't_1_load_reg_11896_reg[27]' in text and 'ram_U/ram_reg_0/WEA[0]' in text
proposal=dict(scope='CRITICAL_PATH_DRIVEN_CONTROL_DECODE_PROPOSAL_NOT_RTL_OR_BOARD',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),base_source_sha256=hashlib.sha256((P/'experimental/texture_v170/hls/frozen/v170_hls63.cpp').read_bytes()).hexdigest(),model_changed=False,threshold_changed=False,input_resolution_changed=False,measured_failure=dict(clock_mhz=125,setup_slack_ns=-.598,source_register='t_1_load_reg_11896_reg[27]',destination='ram_U/ram_reg_0/WEA[0]',data_path_ns=7.641,route_fraction=.83143,report_sha256=hashlib.sha256(report.read_bytes()).hexdigest()),change='Register a three-bit one-hot decode of supported raw32 opcodes; pass decoded depth explicitly; invalid opcodes retain error3',accuracy_or_speed_claimed=False)
(b/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(json.dumps(proposal))
