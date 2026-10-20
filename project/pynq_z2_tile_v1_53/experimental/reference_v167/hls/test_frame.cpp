#include <ap_int.h>
#include <cstdio>
#include <cstdint>
void reference_frame(const ap_uint<64>*,ap_uint<32>*,unsigned,unsigned,unsigned,int,int,int,unsigned,unsigned);
static ap_uint<64> pixels[250000];
static ap_uint<32> result[250000];
static uint32_t rng=0x167bac31;
static uint32_t next(){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static int clamp(int n,int lo,int hi){return n<lo?lo:n>hi?hi:n;}
static int ab(int n){return n<0?-n:n;}
static void feature(uint32_t rgb,int &y,int &co,int &cg){int r=rgb>>16&255,g=rgb>>8&255,b=rgb&255;y=(r+2*g+b+2)>>2;co=(r-b+256)>>1;cg=(-r+2*g-b+512)>>2;}
int main(){
  for(int trial=0;trial<2;trial++) {
    unsigned gain[3]={trial?320u:256u,trial?205u:256u,trial?287u:256u};int offset[3]={trial?-20:0,trial?20:0,trial?-3:0};
    for(int i=0;i<250000;i++)pixels[i]=ap_uint<64>(next())|(ap_uint<64>(next()&0xffffff)<<32);
    reference_frame(pixels,result,gain[0],gain[1],gain[2],offset[0],offset[1],offset[2],18,9);
    for(int y=0;y<500;y++)for(int x=0;x<500;x++) {
      int sum[4]={0,0,0,0},low[2]={255,255},high[2]={0,0},ay=0,by=0,aco=0,acg=0,bco=0,bcg=0;
      for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++) {
        uint64_t v=pixels[clamp(y+dy,0,499)*500+clamp(x+dx,0,499)].to_uint64();uint32_t a=v&0xffffff,b=0;
        for(int c=0;c<3;c++){int shift=16-8*c;int n=((((v>>(32+shift))&255)*gain[c]+128)>>8)+offset[c];b|=clamp(n,0,255)<<shift;}
        int ya,ca,ga,yb,cb,gb;feature(a,ya,ca,ga);feature(b,yb,cb,gb);
        low[0]=ca<low[0]?ca:low[0];high[0]=ca>high[0]?ca:high[0];low[1]=ga<low[1]?ga:low[1];high[1]=ga>high[1]?ga:high[1];
        if(ab(dx)<=1 && ab(dy)<=1){sum[0]+=ca;sum[1]+=ga;sum[2]+=cb;sum[3]+=gb;}
        if(dx==0 && dy==0){ay=ya;by=yb;aco=ca;acg=ga;bco=cb;bcg=gb;}
      }
      int score=ab(ay-by),d[4]={ab((sum[0]+4)/9-(sum[2]+4)/9),ab((sum[1]+4)/9-(sum[3]+4)/9),ab(aco-bco)-(high[0]-low[0]),ab(acg-bcg)-(high[1]-low[1])};for(int j=0;j<4;j++)if(d[j]>score)score=d[j];
      unsigned edge=(pixels[y*500+x].to_uint64()>>24)&255;
      unsigned expected=score|((score>18+edge)<<8)|((score>9+(edge>>1))<<9);
      if(result[y*500+x]!=expected){printf("FAIL trial%d x%d y%d actual%u expected%u\n",trial,x,y,result[y*500+x].to_uint(),expected);return 1;}
    }
  }
  puts("PASS: 500000 native full-frame pixels, all borders, Q8 gain/offset and saturation");return 0;
}
