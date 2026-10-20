// SPDX-License-Identifier: MIT
// Complete integer MobileNetV2 + normal-codebook inference. No ARM vision.
#include <stdint.h>
#include <ap_int.h>
typedef ap_uint<128> pack_t;
typedef ap_int<8> i8;
typedef ap_int<16> i16;
typedef ap_int<32> i32;
typedef ap_int<64> i64;
typedef ap_uint<10> shape_t;
static const int O=16,I=8,RD=1024,LD=2048;
static int clampi(int v,int lo,int hi){return v<lo?lo:v>hi?hi:v;}
static int64_t rounded(int64_t v,int shift){
    if(!shift)return v;
    return v<0?-int64_t((uint64_t(-v)+(uint64_t(1)<<(shift-1)))>>shift):int64_t((uint64_t(v)+(uint64_t(1)<<(shift-1)))>>shift);
}
static int rq(ap_int<24> v,uint32_t m){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_int<57> product=v*ap_uint<32>(m);
#pragma HLS BIND_OP variable=product op=mul impl=dsp
    return int(rounded(int64_t(product),28));
}
static int rq8(i8 v,uint32_t m){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_int<41> product=v*ap_uint<32>(m);
#pragma HLS BIND_OP variable=product op=mul impl=fabric latency=2
    return int(rounded(int64_t(product),28));
}
static void dot128(const i8 input[I],const uint64_t weights[O],const i32 old[O],i32 out[O]){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS ARRAY_PARTITION variable=input complete
#pragma HLS ARRAY_PARTITION variable=weights complete
#pragma HLS ARRAY_PARTITION variable=old complete
#pragma HLS ARRAY_PARTITION variable=out complete
    for(int o=0;o<O;o++){
#pragma HLS UNROLL
        i16 p[I];
#pragma HLS ARRAY_PARTITION variable=p complete
        for(int k=0;k<I;k++){
#pragma HLS UNROLL
            i8 w=(weights[o]>>(8*k))&255;
            i16 product=input[k]*w;
#pragma HLS BIND_OP variable=product op=mul impl=dsp
            p[k]=product;
        }
        i32 a=i32(p[0])+p[1],b=i32(p[2])+p[3],c=i32(p[4])+p[5],d=i32(p[6])+p[7];
        out[o]=old[o]+(a+b)+(c+d);
    }
}
static void dw16(pack_t input,pack_t weight,const i32 old[O],i32 out[O]){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS ARRAY_PARTITION variable=old complete
#pragma HLS ARRAY_PARTITION variable=out complete
    for(int o=0;o<O;o++){
#pragma HLS UNROLL
        i8 a=input.range(o*8+7,o*8),b=weight.range(o*8+7,o*8);
        i16 p=a*b;
#pragma HLS BIND_OP variable=p op=mul impl=dsp
        out[o]=old[o]+p;
    }
}
static uint32_t word32(const uint64_t *m,unsigned offset){return uint32_t(m[offset/2]>>((offset&1)*32));}
static void load_line(const pack_t *work,unsigned src,shape_t ih,shape_t iw,shape_t ic,int k,int stride,int pad,int y,pack_t line[LD]){
    for(int cg=0;cg<(ic+15)/16;cg++)for(int r=0;r<k;r++)for(int x=0;x<iw;x++){
#pragma HLS PIPELINE II=1
        int iy=(y<<(stride==2))+r-pad;
        line[(cg*k+r)*iw+x]=(iy>=0&&iy<ih)?work[src+(cg*ih+iy)*iw+x]:pack_t(0);
    }
}
static bool conv(const uint64_t *model,pack_t *work,const unsigned t[24],uint64_t ram[O][RD],pack_t line[LD]){
    unsigned src=t[1],dst=t[2],wo=t[4],bo=t[5],mo=t[6];
    shape_t ih=t[7],iw=t[8],ic=t[9],oc=t[10];
    int k=t[11]&3,stride=t[12]&3,pad=t[13]&1,relu=t[14]&3,qmax=t[15]&127;
    bool depth=t[0]==2;
    if(k!=1&&k!=3)return false;
    if(stride!=1&&stride!=2)return false;
    shape_t oh=((int(ih)+2*pad-k)>>(stride==2))+1,ow=((int(iw)+2*pad-k)>>(stride==2))+1;
    int taps=((ic+7)/8)*k*k;
    if((ic+15)/16*k*iw>LD||(!depth&&taps>RD)||oc%8||ic<1||oc<1)return false;
    for(int ob=0;ob<(oc+15)/16;ob++){
        int32_t bias[O];uint32_t mul[O];
#pragma HLS ARRAY_PARTITION variable=bias complete
#pragma HLS ARRAY_PARTITION variable=mul complete
        for(int lane=0;lane<O;lane++){
            bias[lane]=ob*16+lane<oc?int32_t(word32(model,bo+ob*16+lane)):0;
            mul[lane]=ob*16+lane<oc?word32(model,mo+ob*16+lane):0;
        }
        if(!depth){
            for(int tap=0;tap<taps;tap++)for(int lane=0;lane<O;lane++){
#pragma HLS PIPELINE II=1
                ram[lane][tap]=model[wo+(ob*taps+tap)*16+lane];
            }
        }
        for(int y=0;y<oh;y++){
            load_line(work,src,ih,iw,ic,k,stride,pad,y,line);
            for(int x=0;x<ow;x++){
                i32 acc[O][8];
#pragma HLS ARRAY_PARTITION variable=acc complete dim=0
                for(int lane=0;lane<O;lane++)for(int s=0;s<8;s++){
#pragma HLS UNROLL
                    acc[lane][s]=0;
                }
                if(depth){
                    for(int tap=0;tap<k*k;tap++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=acc inter false
                        int r=k==3?tap/3:0,col=k==3?tap%3:0,ix=(x<<(stride==2))+col-pad;
                        pack_t a=(ix>=0&&ix<iw)?line[(ob*k+r)*iw+ix]:pack_t(0);
                        pack_t w=pack_t(model[wo+(ob*k*k+tap)*2])|(pack_t(model[wo+(ob*k*k+tap)*2+1])<<64);
                        i32 old[O],out[O];
#pragma HLS ARRAY_PARTITION variable=old complete
#pragma HLS ARRAY_PARTITION variable=out complete
                        for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                            old[lane]=acc[lane][tap&7];
                        }
                        dw16(a,w,old,out);
                        for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                            acc[lane][tap&7]=out[lane];
                        }
                    }
                }else{
                    for(int tap=0;tap<taps;tap++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=acc inter false
                        int ib=k==3?tap/9:tap,r=k==3?(tap%9)/3:0,col=k==3?tap%3:0,ix=(x<<(stride==2))+col-pad;
                        pack_t a=(ix>=0&&ix<iw)?line[((ib/2)*k+r)*iw+ix]:pack_t(0);
                        uint64_t v=uint64_t(a>>(64*(ib&1)));i8 input[I];uint64_t w[O];i32 old[O],out[O];
#pragma HLS ARRAY_PARTITION variable=input complete
#pragma HLS ARRAY_PARTITION variable=w complete
#pragma HLS ARRAY_PARTITION variable=old complete
#pragma HLS ARRAY_PARTITION variable=out complete
                        for(int j=0;j<I;j++){
#pragma HLS UNROLL
                            input[j]=(v>>(8*j))&255;
                        }
                        for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                            w[lane]=ram[lane][tap];old[lane]=acc[lane][tap&7];
                        }
                        dot128(input,w,old,out);
                        for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                            acc[lane][tap&7]=out[lane];
                        }
                    }
                }
                pack_t packed=0;
                for(int lane=0;lane<O;lane++){
#pragma HLS PIPELINE II=1
                    i32 sum=bias[lane];for(int s=0;s<8;s++){
#pragma HLS UNROLL
                        sum+=acc[lane][s];
                    }
                    int v=rq(int32_t(sum),mul[lane]);v=clampi(v,relu?0:-127,relu==2?qmax:127);
                    packed.range(lane*8+7,lane*8)=i8(v);
                }
                work[dst+(ob*oh+y)*ow+x]=packed;
            }
        }
    }
    return true;
}
static void add(pack_t *work,const unsigned t[24]){
    for(unsigned i=0;i<t[7];i++){
        pack_t a=work[t[1]+i],b=work[t[3]+i],o=0;
        for(int lane=0;lane<O;lane++){
            int v=rq8(i8(a.range(lane*8+7,lane*8)),t[4])+rq8(i8(b.range(lane*8+7,lane*8)),t[5]);
            o.range(lane*8+7,lane*8)=i8(clampi(v,-127,127));
        }work[t[2]+i]=o;
    }
}
static void pooled(const pack_t *work,unsigned src,shape_t h,shape_t w,int cg,int y,int x,i8 out[O]){
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=out complete
    ap_int<16> sum[O];
#pragma HLS ARRAY_PARTITION variable=sum complete
    for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
        sum[lane]=0;
    }
    for(int r=-1;r<=1;r++)for(int c=-1;c<=1;c++){
#pragma HLS PIPELINE II=1
        int yy=y+r,xx=x+c;
        pack_t p=(yy>=0&&yy<h&&xx>=0&&xx<w)?work[src+(cg*h+yy)*w+xx]:pack_t(0);
        for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
            sum[lane]+=i8(p.range(lane*8+7,lane*8));
        }
    }
    for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
        ap_int<12> v=sum[lane];ap_uint<12> magnitude=v<0?ap_uint<12>(-v):ap_uint<12>(v);
        ap_uint<24> prod=(magnitude+4)*ap_uint<12>(3641);
#pragma HLS BIND_OP variable=prod op=mul impl=fabric
        int q=int(prod>>15);out[lane]=v<0?-q:q;
    }
}
static void load_ram(const uint64_t *m,unsigned offset,int words,uint64_t ram[O][RD]){
    for(int a=0;a<words;a++)for(int bank=0;bank<O;bank++){
#pragma HLS PIPELINE II=1
        ram[bank][a]=m[offset+a*16+bank];
    }
}
static uint64_t distance16(const i16 q[O],const i16 c[O]){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS ARRAY_PARTITION variable=q complete
#pragma HLS ARRAY_PARTITION variable=c complete
    ap_uint<34> sq[O];
#pragma HLS ARRAY_PARTITION variable=sq complete
    for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
        ap_int<17> diff=ap_int<17>(q[lane])-ap_int<17>(c[lane]);
        ap_int<34> p=diff*diff;
#pragma HLS BIND_OP variable=p op=mul impl=dsp
        sq[lane]=p;
    }
    uint64_t s=0;for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
        s+=sq[lane];
    }return s;
}
static unsigned root(uint64_t v){
    uint64_t result=0,bit=uint64_t(1)<<40;
    for(int i=0;i<21;i++){
        uint64_t z=result+bit;
        if(v>=z){v-=z;result=(result>>1)+bit;}else result>>=1;
        bit>>=2;
    }return unsigned(result);
}
static i8 quarter(i8 a,i8 b,i8 c,i8 d,ap_uint<2> fx,ap_uint<2> fy){
#pragma HLS INLINE
    // Quarter-pixel weights are only 0,1,2,3. Shift/add avoids spending two
    // DSPs per channel on the tool's automatic fused multiply-add mapping.
    ap_int<10> ab=ap_int<10>(b)-ap_int<10>(a),cd=ap_int<10>(d)-ap_int<10>(c);
    ap_int<12> top=(int(a)<<2)+(fx[0]?int(ab):0)+(fx[1]?(int(ab)<<1):0);
    ap_int<12> bottom=(int(c)<<2)+(fx[0]?int(cd):0)+(fx[1]?(int(cd)<<1):0);
    ap_int<13> diff=ap_int<13>(bottom)-ap_int<13>(top);
    ap_int<16> total=(int(top)<<2)+(fy[0]?int(diff):0)+(fy[1]?(int(diff)<<1):0);
    int v=total;return i8(v<0?-((-v+8)>>4):((v+8)>>4));
}

void texture_integer(const uint64_t *model,pack_t *work,const uint32_t *rgb,uint32_t *result,unsigned width,unsigned height){
#pragma HLS INTERFACE m_axi port=model offset=slave bundle=modelmem depth=32768 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=work offset=slave bundle=workmem depth=8192 max_read_burst_length=64 max_write_burst_length=64
#pragma HLS INTERFACE m_axi port=rgb offset=slave bundle=inputmem depth=512 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=result offset=slave bundle=outmem depth=512 max_write_burst_length=64
#pragma HLS INTERFACE s_axilite port=return bundle=control
#pragma HLS INTERFACE s_axilite port=model bundle=control
#pragma HLS INTERFACE s_axilite port=work bundle=control
#pragma HLS INTERFACE s_axilite port=rgb bundle=control
#pragma HLS INTERFACE s_axilite port=result bundle=control
#pragma HLS INTERFACE s_axilite port=width bundle=control
#pragma HLS INTERFACE s_axilite port=height bundle=control
#pragma HLS ALLOCATION function instances=rq limit=1
#pragma HLS ALLOCATION function instances=rq8 limit=1
#pragma HLS ALLOCATION function instances=dot128 limit=1
#pragma HLS ALLOCATION function instances=dw16 limit=1
#pragma HLS ALLOCATION function instances=pooled limit=1
    uint64_t ram[O][RD];pack_t line[LD];uint32_t row0[1024],row1[1024];unsigned raw[3136],smooth[3136];
#pragma HLS ARRAY_PARTITION variable=ram complete dim=1
#pragma HLS BIND_STORAGE variable=ram type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=line type=ram_2p impl=bram
    for(int i=0;i<16;i++)result[i]=0;
    result[0]=0x17000001;result[1]=1;
    unsigned h[32];for(int i=0;i<32;i++)h[i]=word32(model,i);
    shape_t side=h[3],grid=h[4],dim=h[5],ca=h[9],cb=h[10];ap_uint<11> count=h[6];
    if(h[0]!=0x17000001||!width||!height||width>1024||height>1024||side<8||side>224||grid!=side/8||dim!=64||count<1||count>1024||ca!=32||cb!=96||h[2]>96)return;
    int den=int(side)*2;ap_int<37> im[3];int64_t ib[3];for(int c=0;c<3;c++){im[c]=int64_t(model[h[17]+c]);ib[c]=int64_t(model[h[18]+c]);}
    for(int y=0;y<side;y++){
        int yy=clampi((2*y+1)*int(height)-side,0,(int(height)-1)*den),y0=yy/den,y1=y0+1<int(height)?y0+1:y0,fy=yy%den;
        for(unsigned x=0;x<width;x++){
#pragma HLS PIPELINE II=1
            row0[x]=rgb[y0*width+x];row1[x]=rgb[y1*width+x];
        }
        for(int x=0;x<side;x++){
            int xx=clampi((2*x+1)*int(width)-side,0,(int(width)-1)*den),x0=xx/den,x1=x0+1<int(width)?x0+1:x0,fx=xx%den;
            pack_t p=0;
            for(int c=0;c<3;c++){
#pragma HLS PIPELINE II=1
                int shift=16-8*c;
                int64_t a=(row0[x0]>>shift)&255,b=(row0[x1]>>shift)&255,c0=(row1[x0]>>shift)&255,d=(row1[x1]>>shift)&255;
                ap_uint<27> v=(a*(den-fx)+b*fx)*(den-fy)+(c0*(den-fx)+d*fx)*fy;
                ap_int<64> product=v*im[c];
#pragma HLS BIND_OP variable=product op=mul impl=dsp
                int q=clampi(int(rounded(int64_t(product)+ib[c],48)),-127,127);p.range(c*8+7,c*8)=i8(q);
            }work[y*side+x]=p;
        }
    }
    for(unsigned task=0;task<h[2];task++){
        unsigned t[24];for(int i=0;i<24;i++)t[i]=word32(model,64+task*24+i);
        if(t[0]==1||t[0]==2){if(!conv(model,work,t,ram,line)){result[1]=2;return;}}
        else if(t[0]==3)add(work,t);
        else{result[1]=3;return;}
        result[8]=task+1;
    }
    // PCA coefficients occupy 128 words per bank; this storage is then reused
    // for the nominal codebook. Tensor buffers remain entirely in PL-owned DDR.
    load_ram(model,h[11],128,ram);
    for(int y=0;y<grid;y++)for(int x=0;x<grid;x++){
        i8 feature[128];
#pragma HLS ARRAY_PARTITION variable=feature cyclic factor=16
        for(int cg=0;cg<2;cg++){
            i8 v[O];
#pragma HLS ARRAY_PARTITION variable=v complete
            pooled(work,h[7],grid,grid,cg,y,x,v);
            for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                feature[cg*16+lane]=v[lane];
            }
        }
        int xx=clampi(2*x-1,0,(grid/2-1)*4),yy=clampi(2*y-1,0,(grid/2-1)*4),x0=xx/4,y0=yy/4;
        int x1=x0+1<grid/2?x0+1:x0,y1=y0+1<grid/2?y0+1:y0,fx=xx%4,fy=yy%4;
        for(int cg=0;cg<6;cg++){
            i8 a[O],b[O],c[O],d[O];
#pragma HLS ARRAY_PARTITION variable=a complete
#pragma HLS ARRAY_PARTITION variable=b complete
#pragma HLS ARRAY_PARTITION variable=c complete
#pragma HLS ARRAY_PARTITION variable=d complete
            pooled(work,h[8],grid/2,grid/2,cg,y0,x0,a);pooled(work,h[8],grid/2,grid/2,cg,y0,x1,b);
            pooled(work,h[8],grid/2,grid/2,cg,y1,x0,c);pooled(work,h[8],grid/2,grid/2,cg,y1,x1,d);
            for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                feature[32+cg*16+lane]=quarter(a[lane],b[lane],c[lane],d[lane],ap_uint<2>(fx),ap_uint<2>(fy));
            }
        }
        pack_t packed=0;
        for(int o=0;o<64;o++){
            int64_t acc=int64_t(model[h[12]+o]);
            for(int k=0;k<128;k+=8){
#pragma HLS PIPELINE II=1
                for(int lane=0;lane<8;lane++){
#pragma HLS UNROLL
                    int j=k+lane,index=o*8+j/16;
                    i16 w=(ram[j%16][index/4]>>((index%4)*16))&65535;
                    ap_int<24> product;
                    if(lane<4){
                        ap_int<24> dsp_product=feature[j]*w;
#pragma HLS BIND_OP variable=dsp_product op=mul impl=dsp
                        product=dsp_product;
                    }else{
                        ap_int<24> fabric_product=feature[j]*w;
#pragma HLS BIND_OP variable=fabric_product op=mul impl=fabric latency=2
                        product=fabric_product;
                    }
                    acc+=product;
                }
            }
            int v=clampi(int(rounded(acc,h[14])),-32767,32767);packed.range((o%8)*16+15,(o%8)*16)=i16(v);
            if(o%8==7)work[h[19]+((y*grid+x)*8)+o/8]=packed;
        }
    }
    load_ram(model,h[13],1024,ram);
    for(int q=0;q<grid*grid;q++){
        i16 query[64];
#pragma HLS ARRAY_PARTITION variable=query cyclic factor=16
        for(int j=0;j<8;j++){
            pack_t p=work[h[19]+q*8+j];for(int l=0;l<8;l++)query[j*8+l]=p.range(l*16+15,l*16);
        }
        uint64_t best=~uint64_t(0),part[3]={0,0,0};
#pragma HLS ARRAY_PARTITION variable=part complete
        for(int nk=0;nk<count*4;nk++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=part inter false
            int n=nk/4,k=nk%4;i16 a[O],b[O];
#pragma HLS ARRAY_PARTITION variable=a complete
#pragma HLS ARRAY_PARTITION variable=b complete
            for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                a[lane]=query[k*16+lane];b[lane]=(ram[lane][n]>>(k*16))&65535;
            }
            uint64_t d=distance16(a,b);
            if(k<3)part[k]=d;
            else{uint64_t total=d+part[0]+part[1]+part[2];if(total<best)best=total;}
        }
        raw[q]=root(best);
    }
    unsigned peak=0;
    for(int y=0;y<grid;y++)for(int x=0;x<grid;x++){
        unsigned sum=0;for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++)sum+=raw[clampi(y+dy,0,grid-1)*grid+clampi(x+dx,0,grid-1)];
        unsigned v=(sum+4)/9;smooth[y*grid+x]=v;result[16+y*grid+x]=v;if(v>peak)peak=v;
    }
    // Divide only while building coordinate tables, never once per pixel.
    // Integer nearest-codebook distances are <2**20 for 64 signed16 features.
    ap_uint<11> ww=width,hh=height;ap_uint<12> xd=ww*2,yd=hh*2;
    ap_uint<6> mx[1024];ap_uint<12> mf[1024];
    for(int x=0;x<ww;x++){
        ap_uint<16> xx=clampi((2*x+1)*int(grid)-int(ww),0,(int(grid)-1)*2*int(ww));
        ap_uint<6> x0=xx/xd;mx[x]=x0;mf[x]=xx-x0*xd;
    }
    ap_uint<44> limit=ap_uint<20>(h[15])*xd*yd;unsigned pixels=0;
    for(int y=0;y<hh;y++){
        ap_uint<16> yy=clampi((2*y+1)*int(grid)-int(hh),0,(int(grid)-1)*2*int(hh));
        ap_uint<6> y0=yy/yd,y1=y0+1<int(grid)?ap_uint<6>(y0+1):y0;
        ap_uint<12> fy=yy-y0*yd;
        for(int x=0;x<ww;x++){
#pragma HLS PIPELINE II=2
            ap_uint<6> x0=mx[x],x1=x0+1<int(grid)?ap_uint<6>(x0+1):x0;
            ap_uint<12> fx=mf[x],dx=xd-fx,dy=yd-fy;
            ap_uint<32> top=ap_uint<20>(smooth[y0*grid+x0])*dx+ap_uint<20>(smooth[y0*grid+x1])*fx;
            ap_uint<32> bottom=ap_uint<20>(smooth[y1*grid+x0])*dx+ap_uint<20>(smooth[y1*grid+x1])*fx;
            ap_uint<44> value=top*dy+bottom*fy;
            bool alarm=h[15]<(1u<<20)&&value>limit;result[16+int(grid)*int(grid)+y*int(ww)+x]=alarm;pixels+=alarm;
        }
    }
    result[1]=0;result[2]=peak>h[15];result[3]=peak;result[4]=h[15];result[5]=grid;result[6]=pixels;result[7]=width*height;
}
