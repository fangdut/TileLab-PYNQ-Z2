// Complete generated frame-engine AXI C/RTL test, synthetic network only.
#include <vector>
#include <fstream>
#include <cstdint>
#include <algorithm>
#include <cstdio>
#include <cstring>
void texture_integer(const uint64_t*,uint64_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
template<class T>std::vector<T> read(const char*path){std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)return {};size_t n=f.tellg();f.seekg(0);std::vector<T>r(n/sizeof(T));f.read((char*)r.data(),n);return r;}
int main(){
    std::vector<uint64_t>model(65536,0),work(131072,0xccccccccccccccccull);std::vector<uint32_t>rgb(4096,0),result(4096,0xdeadbeef);
    auto input=read<uint32_t>("rgb.bin");if(input.size()!=256)return 1;std::copy(input.begin(),input.end(),rgb.begin());
    for(unsigned launch=1;launch<=2;launch++){
        auto m=read<uint64_t>(launch==1?"model1.bin":"model2.bin");auto expected=read<uint32_t>(launch==1?"expected1.bin":"expected2.bin");auto features=read<uint64_t>(launch==1?"work1.bin":"work2.bin");
        if(m.empty()||m.size()>model.size()||expected.size()!=273||features.size()>work.size())return 2;
        std::fill(model.begin(),model.end(),0);std::copy(m.begin(),m.end(),model.begin());std::fill(result.begin(),result.end(),0xdeadbeef);
        texture_integer(model.data(),work.data(),rgb.data(),result.data(),16,16);expected[9]=launch;
        for(unsigned i=0;i<expected.size();i++)if(result[i]!=expected[i]){printf("FRAME_RESULT_FAIL launch%u word%u got%u expected%u\n",launch,i,result[i],expected[i]);return 3;}
        for(unsigned i=0;i<features.size();i++)if(work[i]!=features[i]){printf("FRAME_FEATURE_FAIL launch%u word%u got%llx expected%llx\n",launch,i,(unsigned long long)work[i],(unsigned long long)features[i]);return 4;}
    }
    texture_integer(model.data(),work.data(),rgb.data(),result.data(),32,16);if(result[1]!=4||result[9]!=2||result[8]!=0)return 5;
    model[13]^=uint64_t(1)<<32;texture_integer(model.data(),work.data(),rgb.data(),result.data(),16,16);if(result[1]!=4||result[9]!=2)return 6;
    puts("HFE_FULL_71_OPS_72_TENSORS_TWO_FRAMES_MASK_CLEANUP_AND_BAD_CONTRACT_PASS");return 0;
}
