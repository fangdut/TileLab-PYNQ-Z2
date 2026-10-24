// SPDX-License-Identifier: MIT
// Independent scalar oracle for the integrated HLS MAC, not a speed test.
#include "texture_spatial_pair.cpp"
#include <cstdio>
#include <cstdlib>
static unsigned rng=0x188510u;
static unsigned random32(){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static int signed8(unsigned x){return int(x&255)-128;}
static int signed16(unsigned x){return int(x&65535)-32768;}
static unsigned checks=0,cases=0;
static uint64_t memory[O][RD];
static pack_t pixels[LD],dw[9];static i16 query_data[64];
static void require(bool ok){checks++;if(!ok){std::fprintf(stderr,"Mismatch case=%u check=%u\n",cases,checks);std::exit(2);}}
static void convolution(int width,int channels,int kernel,int stride,int pad,bool depth,int head){
    ++cases;
    const int ow=(width+2*pad-kernel)/stride+1;
    const int taps=depth?kernel*kernel:((channels+7)/8)*kernel*kernel;
    require(ow>0&&taps<=RD&&((channels+15)/16)*kernel*width<=LD);
    for(int n=0;n<LD;n++){pack_t v=0;for(int c=0;c<16;c++)v.range(c*8+7,c*8)=i8(signed8(random32()));pixels[n]=v;}
    for(int n=0;n<9;n++){dw[n]=0;for(int c=0;c<16;c++)dw[n].range(c*8+7,c*8)=i8(signed8(random32()));}
    for(int c=0;c<16;c++)for(int t=0;t<taps;t++){
        uint64_t lo=0,hi=0;
        for(int j=0;j<8;j++){lo|=uint64_t(uint8_t(signed8(random32())))<<(j*8);hi|=uint64_t(uint8_t(signed8(random32())))<<(j*8);}
        memory[c][t]=lo;
    }
    hls::stream<sum_packet> output;
    mac_row(ow,channels,width,kernel,stride,pad,depth,head,memory,pixels,dw,false,query_data,1,output);
    for(int x=0;x<(depth?ow:(ow+1)/2);x++){
        require(!output.empty());sum_packet actual=output.read();
        for(int c=0;c<(depth?16:32);c++){
            int64_t expected=0;
            int pixel=depth?x:x*2+c/16;
            for(int t=0;t<taps&&pixel<ow;t++){
                int r=kernel==3?t/3:0,col=kernel==3?t%3:0;
                int ib=(depth||kernel==3)?0:t,ix=pixel*stride+col-pad;
                int row=depth?((r+head)%kernel):((ib/2)*kernel+r);
                pack_t a=(ix>=0&&ix<width)?pixels[row*width+ix]:pack_t(0);
                if(depth){expected+=int(i8(a.range(c*8+7,c*8)))*int(i8(dw[t].range(c*8+7,c*8)));}
                else {
                    uint64_t weights=memory[c%16][t];
                    uint64_t inputs=uint64_t(a>>(64*(ib&1)));
                    for(int j=0;j<8;j++){
                        int aa=int((inputs>>(j*8))&255);if(aa>=128)aa-=256;
                        int ww=int((weights>>(j*8))&255);if(ww>=128)ww-=256;
                        expected+=aa*ww;
                    }
                }
            }
            expected=int64_t((uint64_t(expected)+0x800000ULL)&0xffffffULL)-0x800000LL;
            require(int32_t(i32(actual.range(c*32+31,c*32)))==expected);
        }
    }
    require(output.empty());
}
static void nearest(int count){
    ++cases;
    for(int d=0;d<64;d++)query_data[d]=i16(d%3==0?-32768:d%3==1?32767:signed16(random32()));
    for(int c=0;c<16;c++)for(int n=0;n<count;n++){
        uint64_t word=0;
        for(int j=0;j<4;j++){int value=(n+j)%3==0?32767:(n+j)%3==1?-32768:signed16(random32());word|=uint64_t(uint16_t(value))<<(16*j);}
        memory[c][n]=word;
    }
    hls::stream<sum_packet> output;
    mac_row(1,64,1,1,1,0,false,0,memory,pixels,dw,true,query_data,count,output);
    for(int n=0;n<((count+63)/64)*64;n+=2){
        require(!output.empty());sum_packet actual=output.read();
        for(int c=0;c<2;c++){
            uint64_t expected=0;
            if(n+c>=count)expected=~uint64_t(0);
            else for(int d=0;d<64;d++){
                unsigned bits=(memory[d%16][n+c]>>((d/16)*16))&65535;
                int center=bits<32768?int(bits):int(bits)-65536;
                int64_t difference=int(query_data[d])-center;expected+=uint64_t(difference*difference);
            }
            require(uint64_t(actual.range(c*64+63,c*64))==expected);
        }
    }
    require(output.empty());
}
// The final consumer adds bias and truncates to signed24 before requantizing.
// This adversarial case crosses the signed24 boundary; nearest keeps64bit distances.
static void modular_overflow(){
    ++cases;const int channels=1016,taps=channels/8;
    pack_t pixel=0;for(int j=0;j<16;j++)pixel.range(j*8+7,j*8)=i8(-128);
    for(int n=0;n<LD;n++)pixels[n]=pixel;
    for(int lane=0;lane<O;lane++)for(int t=0;t<taps;t++)memory[lane][t]=0x8080808080808080ULL;
    hls::stream<sum_packet> output;
    mac_row(1,channels,1,1,1,0,false,0,memory,pixels,dw,false,query_data,1,output);
    require(!output.empty());sum_packet packet=output.read();require(output.empty());
    const int64_t full=int64_t(channels)*16384;
    const int64_t reduced=int64_t((uint64_t(full)+0x800000ULL)&0xffffffULL)-0x800000LL;
    require(full>0x7fffff&&reduced<0);
    for(int lane=0;lane<O;lane++){
        require(int32_t(i32(packet.range(lane*32+31,lane*32)))==reduced);
        require(int32_t(i32(packet.range((lane+O)*32+31,(lane+O)*32)))==0);
    }
    int32_t bias[O];uint32_t multiplier[O];pack_t result[224];uint64_t best=0;
    const int32_t biases[]={0,0x7fffff,-0x800000,0x7fffffff,int32_t(0x80000000U),131071,-131073,1};
    for(int lane=0;lane<O;lane++){bias[lane]=biases[lane%8];multiplier[lane]=(lane&1)?0x7ffffffU:0x100000U;}
    output.write(packet);quant_row(result,0,1,bias,multiplier,0,127,false,false,1,best,output);require(output.empty());
    for(int lane=0;lane<O;lane++){
        int64_t v=int64_t((uint64_t(full+int64_t(bias[lane]))+0x800000ULL)&0xffffffULL)-0x800000LL;
        int64_t product=v*multiplier[lane];uint64_t mag=product<0?uint64_t(-product):uint64_t(product);
        int64_t q=int64_t((mag+(1ULL<<27))>>28);if(product<0)q=-q;
        if(q<-127)q=-127;if(q>127)q=127;
        require(int(i8(result[0].range(lane*8+7,lane*8)))==q);
    }
}
int main(){
    const int widths[]={1,14,31,32,33,56,112,224};
    const int channels[]={8,16,24,72,576};
    for(int w:widths)for(int c:channels)if(((c+15)/16)*w<=LD)convolution(w,c,1,1,0,false,0);
    for(int w:widths)if(w>=3)for(int stride=1;stride<=2;stride++)for(int pad=0;pad<=1;pad++){
        convolution(w,3,3,stride,pad,false,0);
        for(int head=0;head<3;head++)convolution(w,16,3,stride,pad,true,head);
    }
    for(int n:{1,2,63,64,65,127,1023,1024})nearest(n);
    modular_overflow();
    std::printf("SPATIAL_INTEGRATED_MAC_SCALAR_PASS cases=%u checks=%u\n",cases,checks);
}
