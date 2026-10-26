#include <vector>
#include <cstdint>
#include <fstream>
#include <algorithm>
#include <cstdio>
unsigned preprocess_integer(const uint32_t*,uint32_t*,unsigned,unsigned);
template<class T>std::vector<T> read(const char*path){std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)return {};size_t n=f.tellg();f.seekg(0);std::vector<T>r(n/sizeof(T));f.read((char*)r.data(),n);return r;}
int main(){
    std::vector<uint32_t>rgb(360448,0),actual(360448,0);auto input=read<uint32_t>("rgb.bin");auto expected=read<uint32_t>("channels.bin");
    if(input.size()!=4096||expected.size()!=4096)return 1;std::copy(input.begin(),input.end(),rgb.begin());
    if(preprocess_integer(rgb.data(),actual.data(),64,64))return 2;
    for(unsigned i=0;i<4096;i++)if(actual[i]!=expected[i])return 3;
    std::fill(rgb.begin(),rgb.end(),0x7b7b7b);if(preprocess_integer(rgb.data(),actual.data(),32,32))return 4;
    for(unsigned i=0;i<1024;i++)if(actual[i]!=0x7b7bf6)return 5;
    rgb[0]=0x123456;if(preprocess_integer(rgb.data(),actual.data(),32,32)!=5)return 6;
    if(preprocess_integer(rgb.data(),actual.data(),0,32)!=4)return 7;
    puts("INTEGER_HISTOGRAM_EQUALIZATION_SATURATED_CHANNELS_CONSTANT_COLOR_AND_GEOMETRY_PASS");return 0;
}
