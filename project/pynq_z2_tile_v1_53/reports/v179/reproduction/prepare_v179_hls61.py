from pathlib import Path
import hashlib,json,re
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');b=P/'experimental/resources_v179';W=Path('D:/Vivado/TileLab_RealPhotos_20261020')
s=(P/'experimental/texture_v170/hls/frozen/v170_hls60.cpp').read_text()
start=s.index('static ap_uint<27> bilinear_u27(');end=s.index('\nstatic int clampi(',start)
old=s[start:end];new=old.replace('#pragma HLS INLINE off\n#pragma HLS PIPELINE II=1','#pragma HLS INLINE')
new=re.sub(r'^#pragma HLS BIND_OP.*\n','',new,flags=re.M)
assert old!=new and 'BIND_OP' not in new;s=s[:start]+new+s[end:]
source=b/'texture_bounded_inline.cpp';assert not source.exists();source.write_text(s)
frozen=P/'experimental/texture_v170/hls/frozen/v170_hls61.cpp';assert not frozen.exists();frozen.write_bytes(source.read_bytes())
tcl=(b/'build_bounded_hls.tcl').read_text().replace('v170_hls60.cpp','v170_hls61.cpp').replace('texture_bounded_bilinear.cpp','texture_bounded_inline.cpp')
(b/'build_bounded_inline_hls.tcl').write_text(tcl)
for oldfile,newfile,changes in [
 ('start_v179_bounded_full_c.py','start_v179_inline_full_c.py',[("'v179_bounded_full_c.log'","'v179_inline_full_c.log'"),('texture_bounded_bilinear.cpp','texture_bounded_inline.cpp'),("'v179_full_c04'","'v179_full_c05'"),("'v179_all_c04'","'v179_all_c05'")]),
 ('start_v179_hls60_synth.py','start_v179_hls61_synth.py',[("'v170_hls60'","'v170_hls61'"),("'v170_hls60_console.log'","'v170_hls61_console.log'"),('build_bounded_hls.tcl','build_bounded_inline_hls.tcl')])]:
    text=(W/oldfile).read_text()
    for a,c in changes:assert a in text,(oldfile,a);text=text.replace(a,c)
    out=W/newfile;assert not out.exists();out.write_text(text)
print(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),previous60='C passes but HLS legacy frontend crashed before scheduling; no RTL or board result',change='Same exact bounded arithmetic; inline helper and remove explicit per-variable DSP bindings to avoid optimizer crash')))
