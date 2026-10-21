// SPDX-License-Identifier: MIT
// Model-specific symmetric INT8 weight bound is recorded separately.
#include <cstdint>
#include <cstdio>
int main(){
 uint64_t count=0;
 for(int x=-128;x<128;x++)for(int a=-127;a<=127;a++)for(int b=-127;b<=127;b++){
  int64_t packed=int64_t(b)*131072+a;
  if(packed<-(1ll<<24)||packed>=(1ll<<24))return 1;
  int64_t product=packed*x;
  int64_t low=product&65535;if(low&32768)low-=65536;
  int64_t high=(product>>17)+(low<0);
  if(low!=x*a||high!=x*b)return 2;
  count++;
 }
 std::printf("CENTERED_SYMMETRIC_INT8_ALL_TRIPLES_PASS cases=%llu\n",(unsigned long long)count);
}
