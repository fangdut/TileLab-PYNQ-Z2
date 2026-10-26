#include <vector>
#include <fstream>
#include <cstdio>
#include <cstdint>
#include <algorithm>
unsigned norm_integer(const uint64_t*,const int16_t*,uint64_t*,int16_t*,unsigned,unsigned);
template<class T>std::vector<T> load(const char*path){std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)return {};size_t n=f.tellg();f.seekg(0);std::vector<T>r(n/sizeof(T));f.read((char*)r.data(),n);return r;}
int main(){
    uint64_t coeff[192];std::vector<uint64_t> padded_params(256,0);
    // AXI co-sim copies the entire declared depth, including mode0/invalid calls.
    // Give its wrapper valid backing memory rather than a short logical fixture.
    std::vector<int16_t> padded_pixels(11534336,0),output(11534336,0);
    for(int frame=0;frame<2;frame++){
        auto params=load<uint64_t>(frame?"params2.bin":"params.bin");auto expected=load<uint64_t>(frame?"coeff2.bin":"coeff.bin");
        auto pixels=load<int16_t>(frame?"pixels2.bin":"pixels.bin");auto expected_pixels=load<int16_t>(frame?"output2.bin":"output.bin");
        if(params.size()!=32||expected.size()!=24||pixels.size()!=256||expected_pixels.size()!=256)return 1;
        std::copy(params.begin(),params.end(),padded_params.begin());std::copy(pixels.begin(),pixels.end(),padded_pixels.begin());
        if(norm_integer(padded_params.data(),padded_pixels.data(),coeff,output.data(),4,2))return 2;
        for(unsigned i=0;i<expected.size();i++)if(coeff[i]!=expected[i]){printf("COEFF_FAIL frame%d index%u\n",frame,i);return 3;}
        for(unsigned i=0;i<expected_pixels.size();i++)if(output[i]!=expected_pixels[i]){printf("PIXEL_FAIL frame%d index%u actual%d expected%d\n",frame,i,int(output[i]),int(expected_pixels[i]));return 4;}
    }
    auto params=load<uint64_t>("coefficient_params.bin");auto expected=load<uint64_t>("coefficient_expected.bin");
    if(params.size()!=48||expected.size()!=36)return 5;
    std::copy(params.begin(),params.end(),padded_params.begin());
    if(norm_integer(padded_params.data(),padded_pixels.data(),coeff,output.data(),6,0))return 6;
    for(unsigned i=0;i<expected.size();i++)if(coeff[i]!=expected[i]){printf("EXTREME_COEFF_FAIL %u actual%llu expected%llu\n",i,(unsigned long long)coeff[i],(unsigned long long)expected[i]);return 7;}
    if(norm_integer(padded_params.data(),padded_pixels.data(),coeff,output.data(),0,0)!=4)return 8;
    padded_params[0]=0;if(norm_integer(padded_params.data(),padded_pixels.data(),coeff,output.data(),1,2)!=4||coeff[3]!=4)return 9;
    puts("INTEGER_INSTANCE_NORM_PL_MOMENTS_COEFFICIENTS_PIXELS_RESET_128BIT_AND_INVALID_PASS");return 0;
}
