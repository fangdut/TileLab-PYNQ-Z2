#pragma once
// Exact helper prefix from the verified V197 normalization unit.
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
