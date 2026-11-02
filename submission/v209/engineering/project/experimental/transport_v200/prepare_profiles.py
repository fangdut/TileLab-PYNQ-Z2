"""Prepare two sealed normal-reference profiles and control-only firmware.

The accepted CNN, projection, PL bitstream and network protocol stay fixed.
Only the previously verified reference bank and threshold differ per profile.
"""
from pathlib import Path
import argparse,json,hashlib,struct,zlib,shutil
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--roof',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--firmware',type=Path,required=True);p.add_argument('--xadapter',type=Path,required=True);a=p.parse_args()
    baseline=a.bundle/'verified_hdmi/model';base=(baseline/'model.bin').read_bytes();other=(a.roof/'model.bin').read_bytes();header=struct.unpack_from('<64I',base);start=header[13]*8;stop=start+1024*64*2
    if len(base)!=len(other) or base[:60]!=other[:60] or base[64:start]!=other[64:start] or base[stop:]!=other[stop:]:raise ValueError('参照之间改变了CNN、投影或ABI')
    expected=['1501e32e733b566e17d125613d0989c04291b658459d63b826e418f6f713ed65','0b54cea7f92572b31ae0667c74e3f29a3efef4a4fca2ec4fa50be71567fab485']
    if [sha(baseline/'model.bin'),sha(a.roof/'model.bin')]!=expected:raise ValueError('不是已验证的两套冻结参照')
    a.out.mkdir(parents=True,exist_ok=False);a.firmware.mkdir(parents=True,exist_ok=False);rows=[]
    for source,key,name,note in [(baseline,'texture','纹理瓷砖参照','原有纹理瓷砖开发场景'),(a.roof,'roof','陶瓦参照（实验）','仅公开陶瓦照片的迁移试验，未验证彩绘地砖')]:
        folder=a.out/key;folder.mkdir();graph=json.loads((source/'graph.json').read_text());blob=(source/'model.bin').read_bytes()
        if zlib.crc32(blob)!=graph['crc32'] or hashlib.sha256(blob).hexdigest()!=graph['sha256']:raise ValueError('参照身份校验失败')
        for file in ['model.bin','graph.json']:shutil.copy2(source/file,folder/file)
        rows.append(dict(id=key,name=name,note=note,path=key,model_sha256=graph['sha256'],model_crc32=graph['crc32'],model_bytes=len(blob),graph_sha256=sha(folder/'graph.json')))
    (a.out/'index.json').write_text(json.dumps(dict(version=200,default='texture',profiles=rows),ensure_ascii=False,indent=2),encoding='utf8')
    source=a.bundle/'verified_hdmi/source/experimental/texture_v170/firmware/main.c';build=json.loads((a.bundle/'verified_hdmi/software/BUILD_RESULT.json').read_text())
    if sha(source)!=build['sources']['main.c']:raise ValueError('传输基线源代码与已验收ELF不匹配')
    text=source.read_text()
    replacements=[('#include "model_identity.h"','#include "model_identity.h"\n#include "profile_allowlist.h"\nstatic uint32_t expected_model_crc=MODEL_CRC;'),
      ('reply[6]=model_ready?MODEL_CRC:0;','reply[6]=model_ready?expected_model_crc:0;'),
      ('if(req[1]==1){respond(0,0,0);return;}','if(req[1]==1){profile_status[7]=tilelab_phy_retry_count;respond(0,profile_status,sizeof(profile_status));return;}'),
      ('if(req[1]==2){upload_pos=0;model_ready=0;respond(0,0,0);return;}','if(req[1]==2){upload_pos=0;model_ready=0;expected_model_crc=req[8];last_width=last_height=0;source_crc=0;elapsed=0;respond(0,0,0);return;}'),
      ('crc((const void*)MODEL,MODEL_BYTES)!=MODEL_CRC','crc((const void*)MODEL,MODEL_BYTES)!=expected_model_crc'),
      ('req[8]!=MODEL_CRC','!profile_crc_allowed(req[8])')]
    for old,new in replacements:
        if text.count(old)!=1:raise ValueError('传输源代码结构变化，拒绝自动修改：'+old)
        text=text.replace(old,new)
    (a.firmware/'main.c').write_text(text)
    shutil.copy2(source.parent/'transport_crc32.h',a.firmware/'transport_crc32.h')
    crcs=[r['model_crc32'] for r in rows]
    allow='''/* SPDX-License-Identifier: MIT; explicit profile upload allowlist. */
#ifndef TILELAB_PROFILE_ALLOWLIST_H
#define TILELAB_PROFILE_ALLOWLIST_H
static int profile_crc_allowed(uint32_t crc) { return crc==%du || crc==%du; }
extern uint32_t tilelab_phy_retry_count;
static uint32_t profile_status[8]={0x2000c001u,2u,%du,%du,MODEL_BYTES,MODEL_GRID,47u,0u};
#endif
'''%(crcs[0],crcs[1],crcs[0],crcs[1])
    (a.firmware/'profile_allowlist.h').write_text(allow)
    # Keep the vendor license verbatim. Override the BSP archive object with
    # the same adapter API plus one checked transition; never suppress asserts.
    vendor=a.xadapter.read_text();needle='\t\t\t\tXEmacPs_SetOperatingSpeed(xemacp, link_speed);'
    if vendor.count(needle)!=1:raise ValueError('Unexpected BSP link transition source')
    guarded=vendor.replace(needle,'''                /* TileLab: an unresolved PHY speed must remain negotiating.
                 * Calling the MAC driver with XST_FAILURE would assert forever. */
                if (link_speed !=10 && link_speed !=100 && link_speed !=1000) {
                    tilelab_phy_retry_count++;
                    netif_set_link_down(netif);
                    xemacs->eth_link_status = ETH_LINK_NEGOTIATING;
                    return;
                }
'''+needle)
    include='#include "lwipopts.h"'
    if guarded.count(include)!=1:raise ValueError('Unexpected vendor include layout')
    guarded=guarded.replace(include,include+'\n/* TileLab addition: diagnostic counter only. */\nunsigned int tilelab_phy_retry_count;')
    setup='\t\t\t\tlink_speed = phy_setup_emacps(xemacp,\n\t\t\t\t\t\tphyaddrforemac);'
    if guarded.count(setup)!=1:raise ValueError('Unexpected PHY reconfiguration site')
    guarded=guarded.replace(setup,'''                {
                    u16_t phy_id=0, negotiated=0;
                    if (XEmacPs_PhyRead(xemacp,phyaddrforemac,2,&phy_id)==XST_SUCCESS && phy_id==0x001c) {
                        /* Realtek link is already negotiated here. Do not reset
                         * and renegotiate it a second time inside the TCP loop. */
                        link_speed=0;
                        if (XEmacPs_PhyRead(xemacp,phyaddrforemac,17,&negotiated)==XST_SUCCESS && (negotiated&0x0400)) {
                            switch(negotiated&0xc000) {
                                case 0x8000:link_speed=1000;break;
                                case 0x4000:link_speed=100;break;
                                case 0:link_speed=10;break;
                                default:break;
                            }
                        }
                        if(link_speed) tilelab_SetUpSLCRDivisors(xemacp,link_speed);
                    } else link_speed=phy_setup_emacps(xemacp,phyaddrforemac);
                }''')
    declaration='void emacps_link_status(struct netif *netif, xemacpsif_s *xemacs, XEmacPs *xemacp)'
    guarded=guarded.replace(declaration,'extern void tilelab_SetUpSLCRDivisors(XEmacPs *, s32);\n'+declaration)
    phy_source=a.xadapter.with_name('xemacpsif_physpeed.c');phy=phy_source.read_text()
    if phy.count('static void SetUpSLCRDivisors')!=2:raise ValueError('Unexpected vendor clock helper declarations')
    phy=phy.replace('SetUpSLCRDivisors','tilelab_SetUpSLCRDivisors').replace('static void tilelab_SetUpSLCRDivisors','void tilelab_SetUpSLCRDivisors')
    (a.firmware/'xemacpsif_physpeed_guarded.c').write_text(phy)
    (a.firmware/'xadapter_guarded.c').write_text(guarded)
    (a.firmware/'link_guard_proof.json').write_text(json.dumps(dict(vendor_source_sha256=sha(a.xadapter),guarded_source_sha256=sha(a.firmware/'xadapter_guarded.c'),phy_vendor_source_sha256=sha(phy_source),phy_guarded_source_sha256=sha(a.firmware/'xemacpsif_physpeed_guarded.c'),change='Read already negotiated Realtek speed without blocking renegotiation; export unchanged vendor clock helper; reject invalid speed before MAC assertion and retry later',vendor_license_preserved=True),indent=2))
    (a.firmware/'profiles_binding.json').write_text(json.dumps(dict(profiles=rows,registry_sha256=sha(a.out/'index.json'),base_source_sha256=sha(source),candidate_source_sha256=sha(a.firmware/'main.c'),pl_and_cnn_unchanged=True),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(profiles=len(rows),profile_crc32=crcs,firmware_source_sha256=sha(a.firmware/'main.c'),runtime_image_inference='FPGA_PL')))
if __name__=='__main__':main()
