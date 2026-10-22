// SPDX-License-Identifier: MIT
#include "kernel.cpp"
#include <cstdio>
#include <cstdint>
static unsigned cases=0;
static bool check(uint32_t value,int64_t coefficient){
    int64_t expected=int64_t(value)*coefficient; // Entire u27*s37 domain fits i64.
    int64_t actual=normalize_fabric(ap_uint<27>(value),ap_int<37>(coefficient)).to_int64();
    ++cases;
    if(actual!=expected){std::printf("FAIL v=%u c=%lld actual=%lld expected=%lld\n",value,(long long)coefficient,(long long)actual,(long long)expected);return false;}
    return true;
}
int main(){
    uint32_t values[]={0,1,2,15,16,255,256,67108864,134217727};
    int64_t coefficients[]={-(1LL<<36),-(1LL<<36)+1,-123456789,-1,0,1,123456789,(1LL<<36)-1};
    for(auto v:values)for(auto c:coefficients)if(!check(v,c))return 1;
    uint64_t random=0x9e3779b97f4a7c15ULL;
    for(unsigned i=0;i<100000;i++){
        random^=random<<13;random^=random>>7;random^=random<<17;
        uint32_t value=random&0x7ffffffU;
        random^=random<<13;random^=random>>7;random^=random<<17;
        uint64_t raw=random&((1ULL<<37)-1);
        int64_t coefficient=(raw&(1ULL<<36))?int64_t(raw)-(1LL<<37):int64_t(raw);
        if(!check(value,coefficient))return 1;
    }
    std::printf("SEGMENTED_NORMALIZATION_SCALAR_PASS cases=%u\n",cases);return 0;
}
