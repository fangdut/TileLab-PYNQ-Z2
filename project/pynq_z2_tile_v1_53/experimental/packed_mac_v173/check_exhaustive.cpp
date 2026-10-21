// SPDX-License-Identifier: MIT
// Native integer mathematical proof. RTL and resource checks are separate.
#include <cstdint>
#include <cstdio>
int main(){
 uint64_t cases=0;
 for(int x=-128;x<128;x++)for(int a=-128;a<128;a++)for(int b=-128;b<128;b++){
  const int64_t packed=int64_t(b)*131072+uint8_t(a);
  if(packed<-(1ll<<24)||packed>=(1ll<<24))return 1;
  const int64_t p=packed*x;
  int64_t low=p&131071;if(low&65536)low-=131072;
  const int64_t high=(p>>17)+(low<0);
  const int64_t restored=low-(a<0?int64_t(x)*256:0);
  if(restored!=x*a||high!=x*b)return 2;
  ++cases;
 }
 for(int64_t d=-131072;d<131072;d++){
  const int64_t square=d*d;
  if(square<0||square>=(1ll<<35))return 3;
 }
 std::printf("PACKED_INT8_ALL_16777216_TRIPLES_AND_262144_DIFFERENCES_PASS cases=%llu\n",(unsigned long long)cases);
}
