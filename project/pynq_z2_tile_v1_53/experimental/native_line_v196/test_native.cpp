#include <ap_int.h>
#include <hls_stream.h>
#include <vector>
#include <fstream>
#include <cstdio>
#include <stdint.h>
void native_line(hls::stream<ap_uint<8>>&,uint64_t*,uint32_t*,unsigned,unsigned,unsigned,unsigned);
template<class T>std::vector<T> read(const char*p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)return {};size_t n=f.tellg();f.seekg(0);std::vector<T>v(n/sizeof(T));f.read((char*)v.data(),n);return v;}
int main(){
    auto pixels=read<uint8_t>("pixels.bin");auto expected=read<uint64_t>("expected.bin");
    if(pixels.size()!=224*79||expected.size()!=79*3)return 1;
    uint64_t stats[3072];uint32_t result[8];hls::stream<ap_uint<8>> input;
    for(auto v:pixels)input.write(v);
    native_line(input,stats,result,79,1264,1858,2586);
    if(result[1]||result[7]!=1)return 2;
    unsigned count=0;
    for(size_t i=0;i<expected.size();i++){if(stats[i]!=expected[i]){printf("NATIVE_FAIL %zu %llu %llu\n",i,(unsigned long long)stats[i],(unsigned long long)expected[i]);return 3;}count+=(expected[i]>>35)&1;}
    if(result[2]!=(count!=0)||result[3]!=count)return 4;
    for(unsigned i=0;i<224*79;i++)input.write(128);
    native_line(input,stats,result,79,1264,1858,2586);
    if(result[1]||result[2]||result[3]||result[7]!=2)return 5;
    for(unsigned i=0;i<79*3;i++)if(stats[i])return 6;
    native_line(input,stats,result,0,1264,1858,2586);
    if(result[1]!=4||result[7]!=2)return 7;
    puts("NATIVE_LINE_INTEGER_STATS_TWO_FRAMES_CLEAR_AND_BAD_WIDTH_PASS");return 0;
}
