#include <ap_int.h>
#include <cstdint>
#include <cstdio>
void packed_pair(ap_int<8>,ap_int<8>,ap_int<8>,ap_int<18>,bool,ap_int<18>&,ap_int<18>&,ap_uint<35>&);
int main(){
 uint32_t state=173;unsigned checked=0;
 for(int n=0;n<4096;n++){
  state=state*1664525u+1013904223u;int8_t x=int8_t(state);
  state=state*1664525u+1013904223u;int8_t a=int8_t(state>>8);
  state=state*1664525u+1013904223u;int8_t b=int8_t(state>>16);
  state=state*1664525u+1013904223u;int d=int(state&262143u);if(d&131072)d-=262144;
  bool mode=n&1;
  if(n<512){x=int8_t(n);a=-128;b=-128;d=-131072;}
  if(n>=512&&n<1024){x=int8_t(n);a=-1;b=127;d=131071;}
  ap_int<18> low,high;ap_uint<35> square;
  packed_pair(x,a,b,d,mode,low,high,square);
  if(low!=(mode?0:int(x)*int(a))||high!=(mode?0:int(x)*int(b))||square!=uint64_t(mode?int64_t(d)*d:0))return 1;
  checked++;
 }
 std::printf("HLS_PACKED_PAIR_INDEPENDENT_SCALAR_REFERENCE_PASS cases=%u\n",checked);
}
