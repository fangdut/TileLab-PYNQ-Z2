from pathlib import Path
R=Path(__file__).resolve().parents[1]
for name in ('test_sg_ownership.py','test_descriptor_firmware.py','test_firmware_crc.py'):
 p=R/'scripts'/name;s=p.read_text().replace('m[64]','m[META_WORDS]').replace('meta_mem[64]','meta_mem[META_WORDS]')
 s=s.replace('d[(queue.head%12)*40+37]','queue_front(&queue)[37]').replace('d[(queue.head%12)*40+38]','queue_front(&queue)[38]')
 p.write_text(s,encoding='utf-8')
print('Native acceptance buffers follow authored metadata size; old independent baseline is untouched')
