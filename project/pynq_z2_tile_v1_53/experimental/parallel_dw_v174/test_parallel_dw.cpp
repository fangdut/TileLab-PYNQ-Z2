// SPDX-License-Identifier: MIT
// Independent scalar depthwise reference vs the actual candidate MAC/window.
// Offline C check only; HLS RTL and physical verification remain required.
#ifndef TILE_DW_SOURCE
#define TILE_DW_SOURCE "texture_bounded_dw.cpp"
#endif
#include TILE_DW_SOURCE
#include <cstdio>
#include <cstdlib>
static void require(bool v,const char *why){if(!v){fprintf(stderr,"FAIL %s\n",why);std::exit(1);}}
int main(){
    pack_t line[3][1024];static uint64_t ram[16][1024]={};
    unsigned bank_checks=0,outputs=0,calls=0;
    for(int width=1;width<=224;width++){
        int rows=2048/width;
        for(int r=0;r<rows;r++)for(int x=0;x<width;x++)line_write(line,r,width,x,pack_t(r*257+x));
        for(int r=0;r<rows;r++)for(int x=0;x<width;x++){require(line_read(line,r,width,x)==pack_t(r*257+x),"logical line bank alias");bank_checks++;}
    }
    int widths[]={1,2,3,7,8,13,14,28,56,112,224};
    for(int width:widths)for(int stride=1;stride<=2;stride++)for(int k:{1,3})for(int pad=0;pad<=1;pad++){
        if((k==1&&pad)||width+2*pad<k)continue;
        int ow=(width+2*pad-k)/stride+1;
        for(int head=0;head<(k==3?3:1);head++)for(int trial=0;trial<3;trial++){
            pack_t image[3][224],weight[9];i16 query[64]={};
            for(int r=0;r<3;r++)for(int x=0;x<width;x++){
                pack_t word=0;
                for(int lane=0;lane<16;lane++)word.range(lane*8+7,lane*8)=i8(trial==1?-128:((r*51+x*23+lane*17+trial*111)&255)-128);
                image[r][x]=word;line_write(line,(r+head)%3,width,x,word);
            }
            for(int tap=0;tap<9;tap++){
                pack_t word=0;
                for(int lane=0;lane<16;lane++)word.range(lane*8+7,lane*8)=i8(tap<k*k?(trial==1?-128:((tap*29+lane*41+trial*79)&255)-128):0);
                weight[tap]=word;
            }
            hls::stream<sum_packet> output;
            mac_row(ow,16,width,k,stride,pad,true,head,ram,line,weight,false,query,0,output);
            for(int x=0;x<ow;x++){
                require(!output.empty(),"missing output");sum_packet result=output.read();
                for(int lane=0;lane<16;lane++){
                    int expected=0;
                    for(int r=0;r<k;r++)for(int col=0;col<k;col++){
                        int ix=x*stride+col-pad;
                        if(ix>=0&&ix<width)expected+=int(i8(image[r][ix].range(lane*8+7,lane*8)))*int(i8(weight[r*k+col].range(lane*8+7,lane*8)));
                    }
                    int actual=int(i32(result.range(lane*32+31,lane*32)));
                    if(actual!=expected){fprintf(stderr,"width=%d k=%d stride=%d pad=%d head=%d trial=%d x=%d lane=%d got=%d expected=%d\n",width,k,stride,pad,head,trial,x,lane,actual,expected);return 2;}
                    outputs++;
                }
            }
            require(output.empty(),"extra output");calls++;
        }
    }
    printf("PARALLEL_DW_SCALAR_EXACT bank_words=%u mac_calls=%u lane_outputs=%u\n",bank_checks,calls,outputs);
}
