#include <stdint.h>
#include <vector>
#include <fstream>
#include <iostream>
#include <cmath>
extern void texture_infer(const uint32_t*,uint32_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
static std::vector<uint32_t> read(const char *name){std::ifstream f(name,std::ios::binary|std::ios::ate);if(!f)throw name;size_t n=f.tellg();std::vector<uint32_t> v(n/4);f.seekg(0);f.read((char*)v.data(),n);return v;}
static float ff(uint32_t v){union{float f;uint32_t u;}x;x.u=v;return x.f;}
int main(){
    auto model=read("test_model.bin"),rgb=read("test_rgb.bin"),expected=read("test_expected.bin");
    model.resize(4096);rgb.resize(512);std::vector<uint32_t> work(8192),out(512);
    texture_infer(model.data(),work.data(),rgb.data(),out.data(),13,9);
    if(out[0]!=expected[0]||out[1]||out[2]!=expected[2]||out[5]!=4||out[6]!=expected[6]||out[8]!=model[2])return 1;
    float error=std::fabs(ff(out[3])-ff(expected[3]));
    for(unsigned i=16;i<32;i++)error=std::fmax(error,std::fabs(ff(out[i])-ff(expected[i])));
    for(unsigned i=32;i<expected.size();i++)if(out[i]!=expected[i])return 2;
    if(error>0.0001f){std::cerr<<"max float error "<<error<<"\n";return 3;}
    std::cout<<"PASS complete FPGA graph: convolution/residual/max/mean/projection/NN/smoothing/decision/mask, max error="<<error<<"\n";
    // A second hardware launch must not retain previous state.
    model[16]=0x42c80000; // threshold 100
    texture_infer(model.data(),work.data(),rgb.data(),out.data(),13,9);
    if(out[1]||out[2]||out[6])return 4;
    return 0;
}
