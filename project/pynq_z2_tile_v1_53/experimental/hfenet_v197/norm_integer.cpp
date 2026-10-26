// SPDX-License-Identifier: MIT
// Experimental integer InstanceNorm unit, not a full detector or board image.
#include <ap_int.h>
#include <stdint.h>

static ap_uint<64> isqrt128(ap_uint<128> value){
#pragma HLS INLINE off
    ap_uint<66> rem=0;ap_uint<64> root=0;
    for(int bit=63;bit>=0;bit--){
#pragma HLS PIPELINE II=1
        rem=(rem<<2)|ap_uint<2>(value>>(2*bit));
        ap_uint<66> trial=(ap_uint<66>(root)<<2)|1;
        if(rem>=trial){rem-=trial;root=(root<<1)|1;}else root=root<<1;
    }
    return root;
}
static ap_int<128> div_even(ap_int<128> value,ap_uint<128> den){
#pragma HLS INLINE off
    bool negative=value<0;ap_uint<128> num=negative?ap_uint<128>(-value):ap_uint<128>(value);
    ap_uint<129> rem=0;ap_uint<128> q=0;
    for(int bit=127;bit>=0;bit--){
#pragma HLS PIPELINE II=1
        rem=(rem<<1)|ap_uint<1>(num>>bit);
        if(rem>=ap_uint<129>(den)){rem-=den;q[bit]=1;}
    }
    ap_uint<130> twice=ap_uint<130>(rem)<<1;
    if(twice>den||(twice==den&&q[0]))q++;
    if(negative)return ap_int<128>(-ap_int<128>(q));
    return ap_int<128>(q);
}
static ap_int<128> shift_even(ap_int<128> value,unsigned shift){
#pragma HLS INLINE
    bool negative=value<0;ap_uint<128> mag=negative?ap_uint<128>(-value):ap_uint<128>(value);
    ap_uint<128> base=mag>>shift;ap_uint<128> remainder=mag-(base<<shift);ap_uint<128> half=ap_uint<128>(1)<<(shift-1);
    if(remainder>half||(remainder==half&&base[0]))base++;
    if(negative)return ap_int<128>(-ap_int<128>(base));
    return ap_int<128>(base);
}
// Packet: N,S,Q,epsLo,epsHi,gammaQ30,betaQ30,outputExponent.
// Per-channel result: floorSqrtV,A(Q36),B(Q36),status,Vlo,Vhi.
// Mode0 generates coefficients; mode1 additionally applies them to channel-major
// signed16 data. Mode2 computes the moments from those pixels in PL as well.
// Geometry/configuration errors return before reading the invalid packet pixels.
unsigned norm_integer(const uint64_t *params,const int16_t *pixels,
                      uint64_t *coeff,int16_t *output,unsigned count,unsigned mode){
#pragma HLS INTERFACE m_axi port=params offset=slave bundle=controlmem depth=256 max_read_burst_length=16
#pragma HLS INTERFACE m_axi port=pixels offset=slave bundle=pixelmem depth=11534336 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=coeff offset=slave bundle=controlmem depth=192 max_write_burst_length=16
#pragma HLS INTERFACE m_axi port=output offset=slave bundle=pixelmem depth=11534336 max_write_burst_length=64
#pragma HLS INTERFACE s_axilite port=params bundle=control
#pragma HLS INTERFACE s_axilite port=pixels bundle=control
#pragma HLS INTERFACE s_axilite port=coeff bundle=control
#pragma HLS INTERFACE s_axilite port=output bundle=control
#pragma HLS INTERFACE s_axilite port=count bundle=control
#pragma HLS INTERFACE s_axilite port=mode bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    if(count==0||count>32||mode>2)return 4;
    unsigned pixel_offset=0;
    for(unsigned c=0;c<count;c++){
        uint64_t raw_n=params[8*c];ap_int<64> sum=params[8*c+1];uint64_t raw_q=params[8*c+2];
        ap_uint<128> epsilon=(ap_uint<128>(params[8*c+4])<<64)|params[8*c+3];
        ap_int<64> gamma=params[8*c+5],beta=params[8*c+6],exp=params[8*c+7];
        for(unsigned j=0;j<6;j++)coeff[6*c+j]=0;
        if(raw_n==0||raw_n>360448||exp< -38||exp>16||
           gamma< -(ap_int<64>(1)<<40)||gamma>(ap_int<64>(1)<<40)||
           beta< -(ap_int<64>(1)<<40)||beta>(ap_int<64>(1)<<40)){
            coeff[6*c+3]=4;return 4;
        }
        ap_uint<19> n=raw_n;
        if(mode==2){
            ap_int<36> computed_sum=0;ap_uint<50> computed_squares=0;
            for(unsigned i=0;i<raw_n;i++){
#pragma HLS PIPELINE II=1
                ap_int<16> p=pixels[pixel_offset+i];ap_int<32> square=p*p;
                computed_sum+=p;computed_squares+=ap_uint<32>(square);
            }
            sum=computed_sum;raw_q=uint64_t(computed_squares);
        }
        if(sum< -ap_int<64>(raw_n*32768ull)||sum>ap_int<64>(raw_n*32768ull)||raw_q>raw_n*1073741824ull){coeff[6*c+3]=4;return 4;}
        ap_int<36> s=sum;ap_uint<50> q=raw_q;
        ap_uint<72> n_q=n*q;ap_int<72> s_s=s*s;
        if(n_q<ap_uint<72>(s_s)){coeff[6*c+3]=4;return 4;}
        ap_uint<128> base=ap_uint<128>(n_q)-ap_uint<128>(s_s),variance=base+epsilon;
        if(variance<base){coeff[6*c+3]=5;return 5;}
        ap_uint<64> root=isqrt128(variance);int e=6-int(exp);
        ap_int<128> a=0,b=beta;
        if(e>=0){b=b<<e;if(root)a=div_even(ap_int<128>(gamma)<<e,ap_uint<128>(root));}
        else {b=shift_even(b,unsigned(-e));if(root)a=div_even(ap_int<128>(gamma),ap_uint<128>(root)<<unsigned(-e));}
        ap_int<128> min64=-(ap_int<128>(1)<<63),max64=(ap_int<128>(1)<<63)-1;
        if(a<min64||a>max64||b<min64||b>max64){coeff[6*c+3]=6;return 6;}
        coeff[6*c]=uint64_t(root);coeff[6*c+1]=uint64_t(ap_int<64>(a));coeff[6*c+2]=uint64_t(ap_int<64>(b));
        coeff[6*c+4]=uint64_t(variance);coeff[6*c+5]=uint64_t(variance>>64);
        if(mode!=0){
            ap_int<64> aa=a,bb=b;
            for(unsigned i=0;i<raw_n;i++){
#pragma HLS PIPELINE II=1
                ap_int<16> pixel=pixels[pixel_offset+i];ap_int<36> diff=ap_int<36>(n)*pixel-s;
                ap_int<100> product=diff*aa;
                ap_int<128> value=shift_even(ap_int<128>(product)+bb,36);
                if(value>32767)value=32767;if(value< -32768)value=-32768;
                output[pixel_offset+i]=int16_t(value);
            }
        }
        pixel_offset+=unsigned(raw_n);
    }
    return 0;
}
