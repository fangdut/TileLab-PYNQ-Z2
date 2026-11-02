/* SPDX-License-Identifier: MIT
 * IEEE CRC32 transport integrity only. No image detection computation.
 * Slicing-by-four keeps exactly the legacy reflected CRC state convention.
 */
#ifndef TILELAB_TRANSPORT_CRC32_H
#define TILELAB_TRANSPORT_CRC32_H
#include <stdint.h>
static uint32_t transport_crc_table[4][256];
static void transport_crc_init(void) {
    unsigned i,j;
    for(i=0;i<256;i++) {
        uint32_t c=i;
        for(j=0;j<8;j++) c=(c>>1)^((0u-(c&1u))&0xedb88320u);
        transport_crc_table[0][i]=c;
    }
    for(j=1;j<4;j++) for(i=0;i<256;i++) {
        uint32_t c=transport_crc_table[j-1][i];
        transport_crc_table[j][i]=transport_crc_table[0][c&255u]^(c>>8);
    }
}
static uint32_t transport_crc_update(uint32_t c,const void *p,unsigned n) {
    const unsigned char *s=(const unsigned char *)p;
    while(n>=4u) {
        /* Byte assembly has defined behavior for every alignment and endian. */
        uint32_t q=c^(uint32_t)s[0]^((uint32_t)s[1]<<8)^((uint32_t)s[2]<<16)^((uint32_t)s[3]<<24);
        c=transport_crc_table[3][q&255u]^transport_crc_table[2][(q>>8)&255u]
         ^transport_crc_table[1][(q>>16)&255u]^transport_crc_table[0][q>>24];
        s+=4;n-=4;
    }
    while(n--) c=transport_crc_table[0][(c^*s++)&255u]^(c>>8);
    return c;
}
#endif
