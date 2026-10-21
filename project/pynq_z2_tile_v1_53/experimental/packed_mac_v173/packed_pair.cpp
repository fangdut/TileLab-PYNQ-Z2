// SPDX-License-Identifier: MIT
// HLS form of the isolated packed_product RTL arithmetic. Not the full CNN.
#include <ap_int.h>
void packed_pair(ap_int<8> x,ap_int<8> a,ap_int<8> b,ap_int<18> difference,bool nearest,
                 ap_int<18>& low,ap_int<18>& high,ap_uint<35>& square){
#pragma HLS PIPELINE II=1
    ap_int<25> packed=(ap_int<25>(b)<<17)+ap_uint<8>(a);
    ap_int<25> u=nearest?ap_int<25>(difference):packed;
    ap_int<18> v=nearest?difference:ap_int<18>(x);
    ap_int<43> product=u*v;
#pragma HLS BIND_OP variable=product op=mul impl=dsp latency=3
    ap_int<17> raw=product.range(16,0);
    ap_int<18> correction=a[7]?(ap_int<18>(x)<<8):ap_int<18>(0);
    ap_int<18> corrected=ap_int<18>(raw)-correction;
#pragma HLS BIND_OP variable=corrected op=sub impl=fabric
    ap_int<26> upper=(product>>17)+ap_int<26>(raw<0);
#pragma HLS BIND_OP variable=upper op=add impl=fabric
    low=nearest?ap_int<18>(0):corrected;
    high=nearest?ap_int<18>(0):ap_int<18>(upper);
    square=nearest?ap_uint<35>(product):ap_uint<35>(0);
}
