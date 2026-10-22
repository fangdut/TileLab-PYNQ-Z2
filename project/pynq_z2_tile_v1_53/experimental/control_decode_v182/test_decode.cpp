// SPDX-License-Identifier: MIT
#include "kernel.cpp"
#include <cstdio>
static unsigned cases=0;
static bool check(uint32_t raw){
    unsigned expected=raw>=1&&raw<=3?1U<<(raw-1):0;
    unsigned actual=decode_operation(raw).to_uint();++cases;
    if(actual!=expected){std::printf("FAIL raw=%u expected=%u actual=%u\n",raw,expected,actual);return false;}
    return true;
}
int main(){
    for(uint32_t raw=0;raw<256;raw++)if(!check(raw))return 1;
    uint32_t edges[]={0,1,2,3,4,7,15,0x10000001U,0x80000002U,0xffff0003U,0xfffffffeU,0xffffffffU};
    for(auto raw:edges)if(!check(raw))return 1;
    uint32_t state=0x182204abU;
    for(unsigned i=0;i<100000;i++){state=1664525U*state+1013904223U;if(!check(state))return 1;}
    std::printf("RAW32_ONEHOT_DECODE_PASS cases=%u\n",cases);return 0;
}
