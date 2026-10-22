// SPDX-License-Identifier: MIT
// Independent signed64 scalar reference; include the actual candidate helpers.
#include "kernel.cpp"
#include <cstdio>
#include <cstdint>
static unsigned cases=0;
static bool check(int32_t value,uint32_t multiplier){
    int64_t product=int64_t(value)*int64_t(multiplier);
    uint64_t magnitude=product<0?uint64_t(-product):uint64_t(product);
    int64_t expected=int64_t((magnitude+(uint64_t(1)<<27))>>28);
    if(product<0)expected=-expected;
    int a=rq_fabric(ap_int<24>(value),ap_uint<27>(multiplier));
    int b=rq_dsp(ap_int<24>(value),ap_uint<27>(multiplier));
    ++cases;
    if(a!=expected||b!=expected){std::printf("FAIL value=%d multiplier=%u fabric=%d dsp=%d expected=%lld\n",value,multiplier,a,b,(long long)expected);return false;}
    return true;
}
int main(){
    int32_t values[]={-8388608,-8388607,-1048576,-128,-1,0,1,127,1048575,8388606,8388607};
    uint32_t multipliers[]={0,1,2,134217727,67108864,67108863,67108865,1234567};
    for(auto value:values)for(auto multiplier:multipliers)if(!check(value,multiplier))return 1;
    uint32_t random=0x63a4e321;
    for(unsigned i=0;i<100000;i++){
        random=1664525U*random+1013904223U;uint32_t raw=random&0xffffffU;
        int32_t value=(raw&0x800000U)?int32_t(raw)-0x1000000:int32_t(raw);
        random=1664525U*random+1013904223U;
        if(!check(value,random&0x7ffffffU))return 1;
    }
    std::printf("FABRIC_DSP_SCALAR_REQUANT_PASS cases=%u\n",cases);return 0;
}
