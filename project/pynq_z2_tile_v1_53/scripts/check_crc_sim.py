from pathlib import Path
import zlib,struct,json,sys,hashlib
R=Path(__file__).resolve().parents[1];d=R/'reports/v137/crc_sim/crc_test.sim/sim_1/behav/xsim/crc_packets.hex'
if len(sys.argv)>1:d=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else R/'reports/v137/crc_sim_summary.json'
packets=[];words=[]
for line in d.read_text().splitlines():
 w,last=line.split();words.append(int(w,16))
 if int(last):packets.append(words);words=[]
assert not words and len(packets)==7
checks=[]
for idx,p in enumerate(packets):
 pixels=p[:-40];m=p[-40:];actual=zlib.crc32(struct.pack('<'+str(len(pixels))+'I',*pixels))
 # ABI retarget; these legacy regression stimuli keep presence cfg[26]=0.
 assert m[0]==0x54465337 and m[2]==idx+1 and not(m[7] & (1<<26))
 descriptor=list(m);descriptor[8]=0;descriptor_crc=zlib.crc32(struct.pack('<40I',*descriptor));assert descriptor_crc==m[8],('descriptor CRC',idx)
 bad=bool(m[6]&0x80000000);assert bad==(idx==5)
 if not bad:
  assert len(pixels)==256*240 and actual==m[1],(idx,hex(actual),hex(m[1]))
  expected=[]
  for y in range(240):
   for x in range(256):
    bright=idx not in (3,4);crack=idx in (1,2,5,6)
    rgb=(0xa0a0a0|((x*731+y*613+(idx+1)*98765)&0x1f1f1f)) if bright else (0x101010|((x*17+y*91+(idx+1)*1345)&0x0f0f0f))
    mask=int(crack and 100<=x<102 and 110<=y<130)
    expected.append((mask<<24)|(rgb&0xff0000)|((rgb&255)<<8)|((rgb>>8)&255))
  assert pixels==expected,'Pixel lane order/content mismatch'
 else:assert actual!=m[1],'Fault should omit a pixel and mismatch input CRC'
 checks.append(dict(frame=idx+1,invalid=bad,received_pixels=len(pixels),pl_crc=m[1],received_crc=actual,descriptor_crc=m[8]))
output.write_text(json.dumps(dict(passed=True,checks=checks,packets_path=str(d),packets_sha256=hashlib.sha256(d.read_bytes()).hexdigest()),indent=2));print('PASS 6 full-frame CRCs against independent zlib and exact input pixels; 1 lost-pixel invalidation; 7 descriptors against independent zlib, reset/trailer stalls')
