// SPDX-License-Identifier: MIT
// Candidate unit, NOT connected to the deployed detector yet.
// Input: 224 native-width Y rows supplied by a PL preprocessor. No CPU resize.
// Output: exact signed curvature sum, absolute energy and calibrated vote.
#include <ap_int.h>
#include <hls_stream.h>
#include <stdint.h>
static bool vote(ap_uint<18> n,ap_uint<17> e,ap_uint<18> t){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_uint<36> square=n*n;
#pragma HLS BIND_OP variable=square op=mul impl=dsp
    ap_uint<36> limit=ap_uint<18>(t+1)*ap_uint<18>(e+1);
#pragma HLS BIND_OP variable=limit op=mul impl=dsp
    // Exact equivalent of floor(n*n/(e+1)) > t, without a divider.
    return square>=limit;
}
void native_line(hls::stream<ap_uint<8>>& samples,uint64_t *stats,uint32_t *result,
                 unsigned width,unsigned threshold2,unsigned threshold4,unsigned threshold8){
#pragma HLS INTERFACE axis port=samples
#pragma HLS INTERFACE m_axi port=stats offset=slave bundle=statsmem depth=3072 max_write_burst_length=32
#pragma HLS INTERFACE m_axi port=result offset=slave bundle=resultmem depth=8 max_write_burst_length=8
#pragma HLS INTERFACE s_axilite port=return bundle=control
#pragma HLS INTERFACE s_axilite port=stats bundle=control
#pragma HLS INTERFACE s_axilite port=result bundle=control
#pragma HLS INTERFACE s_axilite port=width bundle=control
#pragma HLS INTERFACE s_axilite port=threshold2 bundle=control
#pragma HLS INTERFACE s_axilite port=threshold4 bundle=control
#pragma HLS INTERFACE s_axilite port=threshold8 bundle=control
#pragma HLS ALLOCATION function instances=vote limit=1
    ap_uint<35> accum[3][1024];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=1
#pragma HLS BIND_STORAGE variable=accum type=ram_t2p impl=bram
    static unsigned sequence=0;
    for(int i=0;i<8;i++)result[i]=0;
    result[0]=0x19600002u;result[1]=1;result[7]=sequence;
    if(width<17||width>1024||threshold2>114240||threshold4>114240||threshold8>114240){result[1]=4;return;}
    for(unsigned x=0;x<width;x++){
#pragma HLS PIPELINE II=1
        for(int s=0;s<3;s++){
#pragma HLS UNROLL
            accum[s][x]=0;
        }
    }
    for(int y=0;y<224;y++){
        ap_uint<8> window[17];
#pragma HLS ARRAY_PARTITION variable=window complete
        for(int i=0;i<17;i++){
#pragma HLS UNROLL
            window[i]=0;
        }
        for(unsigned x=0;x<width;x++){
#pragma HLS PIPELINE II=1
            ap_uint<8> pixel=samples.read();
            for(int i=0;i<16;i++){
#pragma HLS UNROLL
                window[i]=window[i+1];
            }
            window[16]=pixel;
            for(int s=0;s<3;s++){
#pragma HLS UNROLL
                const int d=2<<s;
                if(x>=unsigned(2*d)){
                    unsigned center=x-d;
                    ap_int<11> r=2*int(window[16-d])-int(window[16-2*d])-int(window[16]);
                    ap_uint<35> prior=accum[s][center],next=0;
                    ap_int<18> sum=prior.range(17,0);ap_uint<17> energy=prior.range(34,18);
                    sum+=r;energy+=ap_uint<11>(int(r)<0?-int(r):int(r));
                    next.range(17,0)=sum;next.range(34,18)=energy;accum[s][center]=next;
                }
            }
        }
    }
    unsigned count=0;
    for(unsigned x=0;x<width;x++)for(int s=0;s<3;s++){
#pragma HLS PIPELINE II=1
        ap_uint<35> packed=accum[s][x];ap_int<18> sum=packed.range(17,0);ap_uint<17> energy=packed.range(34,18);
        ap_uint<18> magnitude=sum<0?ap_uint<18>(-sum):ap_uint<18>(sum);
        ap_uint<18> threshold=s==0?threshold2:(s==1?threshold4:threshold8);
        bool alarm=vote(magnitude,energy,threshold);
        ap_uint<64> output=packed;output[35]=alarm;stats[x*3+s]=uint64_t(output);count+=alarm;
    }
    result[1]=0;result[2]=count!=0;result[3]=count;result[4]=width;result[5]=224;result[7]=++sequence;
}
