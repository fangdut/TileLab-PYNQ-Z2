// SPDX-License-Identifier: MIT
// Independent scalar PW reference: bank/half selection, tile offset and row tail.
// Compiles the actual kernel. Offline arithmetic evidence, not RTL or FPGA speed.
#ifndef TILE_PW_SOURCE
#define TILE_PW_SOURCE "texture_direct_cache_separate_dw.cpp"
#endif
#include TILE_PW_SOURCE
#include <cstdio>
#include <cstdlib>
static int pixel(int channel,int y,int x){return ((channel*53+y*37+x*29)&255)-128;}
static int weight(int lane,int channel){return ((lane*47+channel*19)&255)-128;}
int main(){
    static uint64_t ram[16][1024]={};static pack_t cache[8192],line[LD];
    pack_t dw_weight[9]={};i16 query[64]={};
    unsigned calls=0,outputs=0;
    for(int iw:{1,7,14,28,56,112,224})for(int ic:{1,8,9,16,17,48,96,144,256})
    for(int active:{1,3,16}){
        int groups=(ic+15)/16;
        if(groups*active*iw>8192)continue;
        int local=active==1?0:1;
        int rows=1;
        while(rows*2<=active-local&&rows*iw*2<=224)rows*=2;
        int ow=iw*rows;
        for(int cg=0;cg<groups;cg++)for(int y=0;y<active;y++)for(int x=0;x<iw;x++){
            pack_t v=0;
            for(int lane=0;lane<16;lane++)if(cg*16+lane<ic)
                v.range(lane*8+7,lane*8)=i8(pixel(cg*16+lane,y,x));
            cache[(cg*active+y)*iw+x]=v;
        }
        for(int lane=0;lane<16;lane++)for(int ib=0;ib<(ic+7)/8;ib++){
            uint64_t w=0;
            for(int j=0;j<8;j++)if(ib*8+j<ic)
                w|=uint64_t(uint8_t(weight(lane,ib*8+j)))<<(j*8);
            ram[lane][ib]=w;
        }
        hls::stream<sum_packet> output;
        mac_row(ow,ic,ow,1,1,0,false,0,ram,line,cache,true,active*iw,local*iw,
                dw_weight,false,query,0,output);
        for(int x=0;x<ow;x++){
            if(output.empty()){std::fprintf(stderr,"Missing PW output\n");return 1;}
            sum_packet actual=output.read();
            for(int lane=0;lane<16;lane++){
                int expected=0;
                for(int c=0;c<ic;c++)expected+=pixel(c,local+x/iw,x%iw)*weight(lane,c);
                int got=int(i32(actual.range(lane*32+31,lane*32)));
                if(got!=expected){std::fprintf(stderr,"PW mismatch iw=%d ic=%d active=%d local=%d x=%d lane=%d got=%d expected=%d\n",iw,ic,active,local,x,lane,got,expected);return 2;}
                outputs++;
            }
        }
        if(!output.empty()){std::fprintf(stderr,"Extra PW output\n");return 3;}
        calls++;
    }
    std::printf("DIRECT_PW_SCALAR_EXACT mac_calls=%u lane_outputs=%u\n",calls,outputs);
}
