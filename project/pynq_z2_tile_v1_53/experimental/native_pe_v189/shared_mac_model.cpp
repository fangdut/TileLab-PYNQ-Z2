// SPDX-License-Identifier: MIT
#include <ap_int.h>
ap_uint<960> shared_mac(bool nearest,ap_uint<64> activations,ap_uint<1024> centers0,ap_uint<1024> centers1,ap_uint<1024> query_bits){
    ap_uint<960> result=0;
    for(int lane=0;lane<16;lane++){
        ap_int<40> lo=0;ap_int<20> hi=0;
        for(int j=0;j<8;j++){
            if(nearest){
                int d=(lane%8)*8+j;
                ap_int<16> q=query_bits.range(d*16+15,d*16);
                ap_uint<1024> selected=lane<8?centers0:centers1;
                ap_int<16> c=selected.range((d%16)*64+(d/16)*16+15,(d%16)*64+(d/16)*16);
                ap_int<17> delta=ap_int<17>(q)-ap_int<17>(c);
                lo+=ap_int<40>(delta)*ap_int<40>(delta);
            }else{
                ap_int<8> a=activations.range(j*8+7,j*8);
                ap_int<8> w0=centers0.range(lane*64+j*8+7,lane*64+j*8);
                ap_int<8> w1=centers1.range(lane*64+j*8+7,lane*64+j*8);
                lo+=ap_int<16>(a)*ap_int<16>(w0);hi+=ap_int<16>(a)*ap_int<16>(w1);
            }
        }
        result.range(lane*40+39,lane*40)=lo;
        result.range(640+lane*20+19,640+lane*20)=hi;
    }
    return result;
}
