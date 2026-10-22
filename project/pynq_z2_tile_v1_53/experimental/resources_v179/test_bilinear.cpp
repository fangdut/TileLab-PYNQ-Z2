// SPDX-License-Identifier: MIT
#include "kernel.cpp"
#include <cstdio>
#include <cstdint>
static unsigned cases=0;
static bool check(unsigned a,unsigned b,unsigned c,unsigned d,unsigned den,unsigned fx,unsigned fy){
    uint64_t expected=(uint64_t(a)*(den-fx)+uint64_t(b)*fx)*(den-fy)
                     +(uint64_t(c)*(den-fx)+uint64_t(d)*fx)*fy;
    uint64_t actual=bilinear_u27(a,b,c,d,den,fx,fy).to_uint64();
    ++cases;
    if(actual!=expected || actual>255ULL*den*den || actual>=(1ULL<<26)){
        std::printf("FAIL den=%u fx=%u fy=%u pixels=%u,%u,%u,%u actual=%llu expected=%llu\n",den,fx,fy,a,b,c,d,(unsigned long long)actual,(unsigned long long)expected);return false;
    }
    return true;
}
int main(){
    for(unsigned side=8;side<=224;side++){
        unsigned den=2*side,edges[]={0,den-1,den/2};
        for(unsigned pattern=0;pattern<16;pattern++)for(auto fx:edges)for(auto fy:edges)
            if(!check((pattern&1)?255:0,(pattern&2)?255:0,(pattern&4)?255:0,(pattern&8)?255:0,den,fx,fy))return 1;
    }
    uint64_t random=0x183ab625d94c10efULL;
    auto next=[&](){random^=random<<13;random^=random>>7;random^=random<<17;return random;};
    for(unsigned i=0;i<100000;i++){
        unsigned den=2*(8+next()%217),fx=next()%den,fy=next()%den;
        unsigned a=next()&255,b=next()&255,c=next()&255,d=next()&255;
        if(!check(a,b,c,d,den,fx,fy))return 1;
    }
    std::printf("BOUNDED_BILINEAR_SCALAR_PASS cases=%u\n",cases);return 0;
}
