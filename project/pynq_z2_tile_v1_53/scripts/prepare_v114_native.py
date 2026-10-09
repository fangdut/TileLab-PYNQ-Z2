from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'scripts/test_firmware_crc.py';s=p.read_text().replace('0x54465335','0x54465336').replace('consume(slot,w,987654000ULL);','w[8]=tile_descriptor_crc(w);consume(slot,w,987654000ULL);');p.write_text(s)
p=R/'scripts/test_sg_ownership.py';s=p.read_text().replace('0x54465335','0x54465336')
s=s.replace('int main(void){','static void crc_consume(unsigned slot,uint32_t *words,XTime now){words[8]=tile_descriptor_crc(words);consume(slot,words,now);}\nint main(void){')
for slot in (40,41,42):s=s.replace(f';consume({slot},w,0);',f';crc_consume({slot},w,0);')
p.write_text(s)
print('Legacy ownership regressions now generate valid new PL metadata CRCs')
