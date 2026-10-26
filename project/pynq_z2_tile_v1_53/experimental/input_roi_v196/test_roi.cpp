// SPDX-License-Identifier: MIT
// ROI before CNN, output-coordinate mapping, outside-background invariance,
// stale-state cleanup, and invalid-geometry rejection. Not accuracy evidence.
#include <stdint.h>
#include <cstdio>
#include <vector>
#include <fstream>
#include <ap_int.h>
typedef ap_uint<128> pack_t;
void texture_integer(const uint64_t*,pack_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
template<typename T> std::vector<T> read(const char*p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)return {};size_t n=f.tellg();f.seekg(0);std::vector<T>v(n/sizeof(T));f.read((char*)v.data(),n);return v;}
int main(){
    auto model=read<uint64_t>("test_model.bin");auto rgb=read<uint32_t>("test_rgb.bin");auto expected=read<uint32_t>("test_expected.bin");
    auto fa=read<uint32_t>("test_fa_expected.bin"),fb=read<uint32_t>("test_fb_expected.bin");
    if(model.empty()||rgb.size()!=95*81||expected.empty()||fa.empty()||fb.empty())return 1;
    model.resize(32768);rgb.resize(8192);auto h=reinterpret_cast<uint32_t*>(model.data());
    const unsigned end=16+h[4]*h[4];std::vector<pack_t>work(32768);std::vector<uint32_t>result(8192,0xdeadbeef);
    for(int launch=1;launch<=2;launch++){
        if(launch==2){
            h[15]=1u<<30;
            for(unsigned y=0;y<81;y++)for(unsigned x=0;x<95;x++)
                if(x<h[20]||x>=h[20]+h[22]||y<h[21]||y>=h[21]+h[23])rgb[y*95+x]=0xffffffu^rgb[y*95+x];
        }
        texture_integer(model.data(),work.data(),rgb.data(),result.data(),95,81);
        for(size_t i=0;i<expected.size();i++){
            uint32_t want=expected[i];
            if(launch==2){if(i==2||i==6||i>=end)want=0;if(i==4)want=1u<<30;if(i==9)want=2;}
            if(result[i]!=want){printf("ROI_RESULT_FAIL launch=%d word=%zu got=%u want=%u\n",launch,i,result[i],want);return 2;}
        }
        for(int tensor=0;tensor<2;tensor++){
            auto &reference=tensor?fb:fa;unsigned base=h[tensor?8:7];
            for(size_t i=0;i<reference.size();i++)if(uint32_t(work[base+i/4]>>((i%4)*32))!=reference[i]){printf("ROI_FEATURE_FAIL launch=%d tensor=%d word=%zu\n",launch,tensor,i);return 3;}
        }
    }
    // No silent clamp or fallback when fixture calibration cannot apply.
    h[20]=95;texture_integer(model.data(),work.data(),rgb.data(),result.data(),95,81);
    if(result[1]!=4||result[8]!=0||result[9]!=2)return 4;
    puts("INPUT_ROI_TWO_BACKGROUNDS_EXACT_AND_INVALID_REJECT_PASS");return 0;
}
