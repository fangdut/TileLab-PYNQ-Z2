#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "transport_crc32.h"
static unsigned char data[65552];
static uint32_t reference(uint32_t c,const unsigned char *p,unsigned n) {
    unsigned i;
    while(n--) {c^=*p++;for(i=0;i<8;i++)c=(c>>1)^((0u-(c&1u))&0xedb88320u);}
    return c;
}
int main(void) {
    unsigned i,n,off,cases=0;uint32_t seed=199,expected,got;
    transport_crc_init();
    if((~transport_crc_update(~0u,"123456789",9))!=0xcbf43926u)return 1;
    if((~transport_crc_update(~0u,data,0))!=0u)return 2;
    for(i=0;i<sizeof(data);i++){seed=1664525u*seed+1013904223u;data[i]=(unsigned char)(seed>>24);}
    for(off=0;off<8;off++) for(n=0;n<2049;n++) {
        expected=reference(~0u,data+off,n);got=transport_crc_update(~0u,data+off,n);
        if(expected!=got)return 3;
        cases++;
    }
    for(i=0;i<1024;i++) {
        unsigned split,remain,pos;uint32_t state=~0u;
        seed=1664525u*seed+1013904223u;n=seed%65536u;off=(seed>>16)&7u;
        expected=reference(~0u,data+off,n);remain=n;pos=0;
        while(remain) {split=1u+((pos*17u+seed)%1025u);if(split>remain)split=remain;state=transport_crc_update(state,data+off+pos,split);pos+=split;remain-=split;}
        if(expected!=state||state!=transport_crc_update(~0u,data+off,n))return 4;
        cases++;
    }
    printf("{\"passed\":true,\"cases\":%u,\"unaligned_offsets\":8,\"split_updates\":1024,\"scope\":\"NATIVE_C_TRANSPORT_CRC_NOT_BOARD\"}\n",cases);
    return 0;
}
