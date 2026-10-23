from pathlib import Path
import hashlib,json
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
base=P/'experimental/texture_v170/hls/frozen/v170_hls65.cpp';s=base.read_text()
assert hashlib.sha256(base.read_bytes()).hexdigest()=='c4391bbdd3da915836e2f6f63c97407bfd120456f3274d95a1fcf71e6ec4abbd'
helper='''// Only used after the original width/height/side validation. Clamped source
// rows are0..height-1<=1023, width1..1024. Their product is<=1047552.
// The previous int32 expression inferred a22x32 two-DSP cascade on the
// measured critical path. This exact10x11 multiply has explicit pipeline.
static ap_uint<21> row_offset(ap_uint<10> row,ap_uint<11> width){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_uint<21> offset=row*width;
#pragma HLS BIND_OP variable=offset op=mul impl=dsp latency=3
    return offset;
}
'''
needle='static int clampi(';assert s.count(needle)==1;s=s.replace(needle,helper+'\n'+needle)
needle='#pragma HLS ALLOCATION function instances=pooled limit=1';assert s.count(needle)==1;s=s.replace(needle,needle+'\n#pragma HLS ALLOCATION function instances=row_offset limit=1')
needle='        for(unsigned x=0;x<width;x++){';assert s.count(needle)==2
i=s.index(needle);s=s[:i]+'        ap_uint<21> row0_offset=row_offset(ap_uint<10>(y0),ap_uint<11>(width));\n        ap_uint<21> row1_offset=row_offset(ap_uint<10>(y1),ap_uint<11>(width));\n'+s[i:]
for a,b in [('rgb[y0*width+x]','rgb[unsigned(row0_offset)+x]'),('rgb[y1*width+x]','rgb[unsigned(row1_offset)+x]')]:assert s.count(a)==1;s=s.replace(a,b)
b=P/'experimental/row_address_v184';b.mkdir(exist_ok=False);source=b/'texture_row_address.cpp';source.write_text(s)
frozen=P/'experimental/texture_v170/hls/frozen/v170_hls66.cpp';assert not frozen.exists();frozen.write_bytes(source.read_bytes())
tcl=(P/'experimental/control_decode_v182/build_hls.tcl').read_text().replace('v170_hls64.cpp','v170_hls66.cpp').replace('control_decode_v182/texture_control_decode.cpp','row_address_v184/texture_row_address.cpp');(b/'build_hls.tcl').write_text(tcl)
for old,new,pairs in [('start_v182_decode_full_c.py','start_v184_row_full_c.py',[('v182_decode_full_c.log','v184_row_full_c.log'),('control_decode_v182/texture_control_decode.cpp','row_address_v184/texture_row_address.cpp'),('v182_full_c01','v184_full_c01'),('v182_all_c01','v184_all_c01')]),('start_v182_hls64_synth.py','start_v184_hls66_synth.py',[('v170_hls64','v170_hls66'),('control_decode_v182/build_hls.tcl','row_address_v184/build_hls.tcl')])]:
 t=(W/old).read_text()
 for a,c in pairs:assert a in t;t=t.replace(a,c)
 f=W/new;assert not f.exists();f.write_text(t)
proposal=dict(scope='MEASURED_ROW_ADDRESS_WIDTH_PROPOSAL_NOT_RTL_OR_BOARD',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),base_source_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),model_changed=False,threshold_changed=False,input_resolution_changed=False,measured_path='V182 repair: FSM43 to22x32 DSP cascade PCIN,-0.187ns setup',change='Exact bounded10x11 row offset, shared DSP with latency3, called only after original validation',accuracy_or_speed_claimed=False)
(b/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(json.dumps(proposal))
