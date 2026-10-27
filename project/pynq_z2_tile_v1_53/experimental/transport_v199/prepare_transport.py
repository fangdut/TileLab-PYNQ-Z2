"""Clone accepted firmware with only transport CRC implementation replaced."""
from pathlib import Path
import argparse,hashlib,json
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source=a.bundle/'verified_hdmi/source/experimental/texture_v170/firmware/main.c'
    build=json.loads((a.bundle/'verified_hdmi/software/BUILD_RESULT.json').read_text())
    assert sha(source)==build['sources']['main.c']
    text=source.read_text();old='static uint32_t table[256];';assert text.count(old)==1;text=text.replace(old,'#include "transport_crc32.h"')
    old='const unsigned char *s=p;while(n--)c=table[(c^*s++)&255]^(c>>8);return c;';assert text.count(old)==1;text=text.replace(old,'return transport_crc_update(c,p,n);')
    old='for(i=0;i<256;i++){uint32_t c=i;for(j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);table[i]=c;}';assert text.count(old)==1;text=text.replace(old,'transport_crc_init();')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'main.c').write_text(text)
    (a.out/'transport_crc32.h').write_bytes((Path(__file__).parent/'transport_crc32.h').read_bytes())
    proof=dict(scope='CANDIDATE_TRANSPORT_CRC_ONLY_NOT_ACCEPTED',source_sha256=sha(source),candidate_sha256=sha(a.out/'main.c'),helper_sha256=sha(a.out/'transport_crc32.h'),unchanged_wire_protocol=True,unchanged_pl_and_model=True,changes=['replace256-entry byte CRC with4x256-entry slicing-by-four CRC','CRC table initialization'],image_arithmetic_added=False)
    (a.out/'change_proof.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
if __name__=='__main__':main()
