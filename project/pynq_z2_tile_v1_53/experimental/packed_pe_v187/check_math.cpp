// SPDX-License-Identifier: MIT
// Independent integer arithmetic proof. Not an integrated detector benchmark.
#include <cstdint>
#include <cstdio>
static int s16(unsigned v){return v<32768?int(v):int(v)-65536;}
int main(){
 uint64_t cases=0,missing_correction_errors=0;
 int64_t minimum=0,maximum=0;
 for(int a=-128;a<128;a++)for(int w0=-128;w0<128;w0++)for(int w1=-128;w1<128;w1++){
  int64_t packed=int64_t(w1)*65536+w0;
  if(packed<-(int64_t(1)<<24)||packed>=(int64_t(1)<<24))return 2;
  int64_t product=int64_t(a)*packed;
  uint64_t bits=uint64_t(product);int p0=s16(unsigned(bits&65535));
  int high=s16(unsigned((bits>>16)&65535));int p1=high+(p0<0);
  if(p0!=a*w0||p1!=a*w1)return 3;
  if(high!=a*w1)missing_correction_errors++;
  if(packed<minimum)minimum=packed;if(packed>maximum)maximum=packed;
  cases++;
 }
 uint64_t squares=0;
 for(int d=-65535;d<=65535;d++){
  int64_t a25=d,b18=d;uint64_t p=uint64_t(a25*b18),expected=uint64_t(int64_t(d)*d);
  if((p&((uint64_t(1)<<34)-1))!=expected)return 4;
  squares++;
 }
 if(cases!=16777216||squares!=131071||missing_correction_errors!=8323072)return 5;
 std::printf("{\"dual_signed8_cases\":%llu,\"nearest_difference_cases\":%llu,\"missing_correction_errors\":%llu,\"packed_minimum\":%lld,\"packed_maximum\":%lld}\n",
  (unsigned long long)cases,(unsigned long long)squares,(unsigned long long)missing_correction_errors,(long long)minimum,(long long)maximum);
}
