from pathlib import Path
import hashlib,json,ctypes
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
s=(P/'experimental/texture_v170/hls/frozen/v170_hls62.cpp').read_text()
old='''        for(int i=0;i<count;i++){
            pack_t a=left[i],b=right[i],o=0;
            for(int lane=0;lane<O;lane++){
#pragma HLS PIPELINE II=1
                int v=rq8(i8(a.range(lane*8+7,lane*8)),t[4])+rq8(i8(b.range(lane*8+7,lane*8)),t[5]);
                o.range(lane*8+7,lane*8)=i8(clampi(v,-127,127));
            }
            output[i]=o;
        }'''
new='''        // One stream across all packed words avoids restarting a16-iteration
        // pipeline for each word. Same two requantizers, RAMs and exact bytes.
        pack_t packed=0;
        for(unsigned step=0;step<unsigned(count)*16;step++){
#pragma HLS PIPELINE II=1
            unsigned word=step>>4,lane=step&15;
            pack_t a=left[word],b=right[word];
            int v=rq8(i8(a.range(lane*8+7,lane*8)),t[4])+rq8(i8(b.range(lane*8+7,lane*8)),t[5]);
            ap_uint<8> byte=ap_uint<8>(i8(clampi(v,-127,127)));
            packed=(packed>>8)|(pack_t(byte)<<120);
            if(lane==15)output[word]=packed;
        }'''
assert s.count(old)==1;s=s.replace(old,new)
b=P/'experimental/residual_stream_v181';b.mkdir(exist_ok=False)
source=b/'texture_residual_stream.cpp';source.write_text(s)
frozen=P/'experimental/texture_v170/hls/frozen/v170_hls63.cpp';assert not frozen.exists();frozen.write_bytes(source.read_bytes())
tcl=(P/'experimental/resources_v179/build_bounded_inline_hls.tcl').read_text().replace('v170_hls61.cpp','v170_hls63.cpp').replace('resources_v179/texture_bounded_inline.cpp','residual_stream_v181/texture_residual_stream.cpp')
(b/'build_hls.tcl').write_text(tcl)
text=(W/'start_v179_inline_full_c.py').read_text()
for a,c in [('v179_inline_full_c.log','v181_residual_full_c.log'),('resources_v179/texture_bounded_inline.cpp','residual_stream_v181/texture_residual_stream.cpp'),('v179_full_c05','v181_full_c01'),('v179_all_c05','v181_all_c01')]:assert a in text;text=text.replace(a,c)
(W/'start_v181_residual_full_c.py').write_text(text)
text=(W/'start_v179_hls61_synth.py').read_text()
for a,c in [('v170_hls61','v170_hls63'),('resources_v179/build_bounded_inline_hls.tcl','residual_stream_v181/build_hls.tcl')]:assert a in text;text=text.replace(a,c)
(W/'start_v181_hls63_synth.py').write_text(text)
proposal=dict(scope='EXACT_RESIDUAL_STREAM_PROPOSAL_NOT_HLS_RTL_BOARD_OR_FPS',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),base_source_sha256=hashlib.sha256((P/'experimental/texture_v170/hls/frozen/v170_hls62.cpp').read_bytes()).hexdigest(),model_changed=False,threshold_changed=False,change='Flatten residual requantization across up to256 packed words; reuse same two rq8 functions and three RAMs; shift-packed16 bytes preserves lane order',accuracy_or_speed_claimed=False)
(b/'proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');print(json.dumps(proposal))
