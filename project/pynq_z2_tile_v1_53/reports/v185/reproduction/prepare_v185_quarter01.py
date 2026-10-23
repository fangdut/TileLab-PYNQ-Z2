from pathlib import Path
import hashlib,json
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
base=P/'experimental/texture_v170/hls/frozen/v170_hls66.cpp';s=base.read_text();assert hashlib.sha256(base.read_bytes()).hexdigest()=='d76fd393161ba43ea1e8f912e7294aa5d37a6c94d6b6f035b81af238fc4b2713'
old='''static i8 quarter(i8 a,i8 b,i8 c,i8 d,ap_uint<2> fx,ap_uint<2> fy){
#pragma HLS INLINE
    // Quarter-pixel weights are only 0,1,2,3. Shift/add avoids spending two
    // DSPs per channel on the tool's automatic fused multiply-add mapping.
    ap_int<10> ab=ap_int<10>(b)-ap_int<10>(a),cd=ap_int<10>(d)-ap_int<10>(c);
    ap_int<12> top=(int(a)<<2)+(fx[0]?int(ab):0)+(fx[1]?(int(ab)<<1):0);
    ap_int<12> bottom=(int(c)<<2)+(fx[0]?int(cd):0)+(fx[1]?(int(cd)<<1):0);
    ap_int<13> diff=ap_int<13>(bottom)-ap_int<13>(top);
    ap_int<16> total=(int(top)<<2)+(fy[0]?int(diff):0)+(fy[1]?(int(diff)<<1):0);
    int v=total;return i8(v<0?-((-v+8)>>4):((v+8)>>4));
}'''
new='''// V185: preserve the exact shift/add arithmetic and final rounding, but
// cut the measured cross-channel quarter-pixel carry chain at module registers.
static ap_int<12> quarter_horizontal(i8 a,i8 b,ap_uint<2> f){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    ap_int<10> delta=ap_int<10>(b)-ap_int<10>(a);
    ap_int<12> value=(int(a)<<2)+(f[0]?int(delta):0)+(f[1]?(int(delta)<<1):0);
    return value;
}
static ap_int<16> quarter_vertical(ap_int<12> top,ap_int<12> bottom,ap_uint<2> f){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    ap_int<13> diff=ap_int<13>(bottom)-ap_int<13>(top);
    ap_int<16> total=(int(top)<<2)+(f[0]?int(diff):0)+(f[1]?(int(diff)<<1):0);
    return total;
}
static i8 quarter(i8 a,i8 b,i8 c,i8 d,ap_uint<2> fx,ap_uint<2> fy){
#pragma HLS INLINE
    ap_int<12> top=quarter_horizontal(a,b,fx),bottom=quarter_horizontal(c,d,fx);
    ap_int<16> total=quarter_vertical(top,bottom,fy);
    int v=total;return i8(v<0?-((-v+8)>>4):((v+8)>>4));
}'''
assert s.count(old)==1;s=s.replace(old,new)
b=P/'experimental/quarter_pipeline_v185';b.mkdir(exist_ok=False);source=b/'texture_quarter_pipeline.cpp';source.write_text(s)
frozen=P/'experimental/texture_v170/hls/frozen/v170_hls68.cpp';assert not frozen.exists();frozen.write_bytes(source.read_bytes())
tcl=(P/'experimental/row_address_v184/build_hls.tcl').read_text().replace('v170_hls66.cpp','v170_hls68.cpp').replace('row_address_v184/texture_row_address.cpp','quarter_pipeline_v185/texture_quarter_pipeline.cpp');(b/'build_hls.tcl').write_text(tcl)
for oldfile,newfile,pairs in [('start_v184_row_full_c.py','start_v185_quarter_full_c.py',[('v184_row_full_c.log','v185_quarter_full_c.log'),('row_address_v184/texture_row_address.cpp','quarter_pipeline_v185/texture_quarter_pipeline.cpp'),('v184_full_c01','v185_full_c01'),('v184_all_c01','v185_all_c01')]),('start_v184_hls66_synth.py','start_v185_hls68_synth.py',[('v170_hls66','v170_hls68'),('row_address_v184/build_hls.tcl','quarter_pipeline_v185/build_hls.tcl')])]:
 t=(W/oldfile).read_text()
 for a,c in pairs:assert a in t;t=t.replace(a,c)
 f=W/newfile;assert not f.exists();f.write_text(t)
proposal=dict(scope='ACTUAL_QUARTER_CRITICAL_PATH_PIPELINE_PROPOSAL_NOT_BOARD',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),base_source_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),model_changed=False,threshold_changed=False,input_resolution_changed=False,measured_path='V183 initial125MHz:tmp_28 bit0 to tmp_32 bit0 via quarter total_3,11levels/7CARRY4,8.041nsdata,-0.342nssetup',change='Same bounded row_offset plus explicit two-cycle horizontal and vertical quarter interpolation helpers; arithmetic and final signed rounding unchanged',accuracy_or_speed_claimed=False)
(b/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(json.dumps(proposal))
