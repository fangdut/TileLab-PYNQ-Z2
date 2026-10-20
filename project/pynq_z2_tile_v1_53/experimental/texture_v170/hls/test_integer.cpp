#include <stdint.h>
#include <stdio.h>
#include <vector>
#include <fstream>
#include <ap_int.h>
typedef ap_uint<128> pack_t;
void texture_integer(const uint64_t*,pack_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
template<typename T>std::vector<T> read(const char *path){
    std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)return {};
    size_t n=f.tellg();f.seekg(0);std::vector<T> v(n/sizeof(T));f.read((char*)v.data(),n);return v;
}
int main(){
    auto model=read<uint64_t>("test_model.bin");auto rgb=read<uint32_t>("test_rgb.bin");auto expected=read<uint32_t>("test_expected.bin");
    if(model.empty()||rgb.size()!=117||expected.size()!=149)return 2;
    std::vector<pack_t> work(8192);std::vector<uint32_t> result(512,0xdeadbeef);
    texture_integer(model.data(),work.data(),rgb.data(),result.data(),13,9);
    for(size_t i=0;i<expected.size();i++)if(result[i]!=expected[i]){printf("FAIL index=%zu got=%u expected=%u\n",i,result[i],expected[i]);return 3;}
    // A second launch checks stale score, state, alarm and mask cleanup.
    model[7]=(model[7]&0xffffffffULL)|(uint64_t(1u<<30)<<32);
    texture_integer(model.data(),work.data(),rgb.data(),result.data(),13,9);
    if(result[1]||result[2]||result[6])return 4;
    for(int i=32;i<149;i++)if(result[i])return 5;
    printf("V170_COMPLETE_INTEGER_TWO_LAUNCH_PASS\n");return 0;
}
