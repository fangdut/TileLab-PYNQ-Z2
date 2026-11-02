#include <stdint.h>
#include <stdio.h>
#include <vector>
#include <fstream>
#include <ap_int.h>
typedef ap_uint<128> pack_t;
#ifndef TILE_TEST_WIDTH
#define TILE_TEST_WIDTH 13
#endif
#ifndef TILE_TEST_HEIGHT
#define TILE_TEST_HEIGHT 9
#endif
#ifndef TILE_TEST_WORK_DEPTH
#define TILE_TEST_WORK_DEPTH 8192
#endif
#ifndef TILE_TEST_INPUT_DEPTH
#define TILE_TEST_INPUT_DEPTH 512
#endif
#ifndef TILE_TEST_RESULT_DEPTH
#define TILE_TEST_RESULT_DEPTH 512
#endif
void texture_integer(const uint64_t*,pack_t*,const uint32_t*,uint32_t*,unsigned,unsigned);
template<typename T>std::vector<T> read(const char *path){
    std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)return {};
    size_t n=f.tellg();f.seekg(0);std::vector<T> v(n/sizeof(T));f.read((char*)v.data(),n);return v;
}
int main(){
    auto model=read<uint64_t>("test_model.bin");auto rgb=read<uint32_t>("test_rgb.bin");auto expected=read<uint32_t>("test_expected.bin");
    if(model.empty())return 2;
    if(model.size()<32768)model.resize(32768);
    auto header=reinterpret_cast<const uint32_t*>(model.data());
    const unsigned pixels=TILE_TEST_WIDTH*TILE_TEST_HEIGHT,score_end=16+header[4]*header[4];
    if(rgb.size()!=pixels||expected.size()!=score_end+pixels)return 2;
    if(rgb.size()<TILE_TEST_INPUT_DEPTH)rgb.resize(TILE_TEST_INPUT_DEPTH);
    size_t words=header[16]/16,results=expected.size();
    if(words<TILE_TEST_WORK_DEPTH)words=TILE_TEST_WORK_DEPTH;
    if(results<TILE_TEST_RESULT_DEPTH)results=TILE_TEST_RESULT_DEPTH;
    std::vector<pack_t> work(words);std::vector<uint32_t> result(results,0xdeadbeef);
    texture_integer(model.data(),work.data(),rgb.data(),result.data(),TILE_TEST_WIDTH,TILE_TEST_HEIGHT);
    auto fa=read<uint32_t>("test_fa_expected.bin"),fb=read<uint32_t>("test_fb_expected.bin");
    for(int tensor=0;tensor<2;tensor++){
        auto &expected_feature=tensor?fb:fa;unsigned base=header[tensor?8:7];
        if(expected_feature.empty())return 6;
        for(size_t i=0;i<expected_feature.size();i++){
            uint32_t got=uint32_t(work[base+i/4]>>((i%4)*32));
            if(got!=expected_feature[i]){printf("CNN_FEATURE_FAIL tensor=%d word=%zu got=%u expected=%u\n",tensor,i,got,expected_feature[i]);return 7;}
        }
    }
    for(size_t i=0;i<expected.size();i++)if(result[i]!=expected[i]){printf("FAIL index=%zu got=%u expected=%u\n",i,result[i],expected[i]);return 3;}
    // A second launch checks stale score, state, alarm and mask cleanup.
    model[7]=(model[7]&0xffffffffULL)|(uint64_t(1u<<30)<<32);
    texture_integer(model.data(),work.data(),rgb.data(),result.data(),TILE_TEST_WIDTH,TILE_TEST_HEIGHT);
    if(result[1]||result[2]||result[6]||result[9]!=2)return 4;
    for(size_t i=score_end;i<expected.size();i++)if(result[i])return 5;
    printf("V170_COMPLETE_INTEGER_TWO_LAUNCH_PASS\n");return 0;
}
