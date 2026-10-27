// SPDX-License-Identifier: MIT
// V198 complete frame interpreter. Candidate, not board-qualified.
#include <stdint.h>
#include "contract.hpp"
#include "norm_math.hpp"
#ifdef __SYNTHESIS__
typedef ap_int<48> acc_t;
#else
typedef int64_t acc_t;
void (*hfe_observer)(unsigned,const uint64_t*,unsigned,unsigned)=0;
#endif
// Dilated5x1 at128columns/32channels needs9*128*32=36864entries.
static const unsigned PE=32,TILE=32,LINE=40960;
struct Tensor{unsigned off,c,h,w,count;};
static uint32_t m32(const uint64_t*m,unsigned i){return uint32_t(m[i>>1]>>(32*(i&1)));}
static int16_t get16(const uint64_t*w,unsigned i){return int16_t(w[i>>2]>>(16*(i&3)));}
static int64_t even64(int64_t v,int shift){
#pragma HLS INLINE
    if(shift<=0)return v*(int64_t(1)<<(-shift));
    uint64_t mag=v<0?uint64_t(-v):uint64_t(v),base=mag>>shift,rem=mag-(base<<shift),half=uint64_t(1)<<(shift-1);
    if(rem>half||(rem==half&&(base&1)))base++;
    return v<0?-int64_t(base):int64_t(base);
}
static int16_t sat(int64_t v){return v>32767?int16_t(32767):(v< -32768?int16_t(-32768):int16_t(v));}
static void put16(uint64_t*w,unsigned i,int16_t value){
    unsigned s=16*(i&3);uint64_t old=w[i>>2];w[i>>2]=(old&~(uint64_t(65535)<<s))|(uint64_t(uint16_t(value))<<s);
}
static bool overlap(Tensor a,Tensor b){return a.off<b.off+b.count&&b.off<a.off+a.count;}
static unsigned gray_level(unsigned numerator,unsigned denominator){
#pragma HLS INLINE off
    unsigned q=0,r=numerator;
    for(int bit=7;bit>=0;bit--){
#pragma HLS PIPELINE II=1
        unsigned trial=denominator<<bit;if(r>=trial){r-=trial;q|=1u<<bit;}
    }
    if((r<<1)>denominator||((r<<1)==denominator&&(q&1)))q++;
    return q;
}
static unsigned preprocess(const uint32_t*rgb,uint64_t*work,Tensor t){
    uint32_t hist[256];uint8_t lut[256];
#pragma HLS BIND_STORAGE variable=hist type=ram_t2p impl=bram
    for(unsigned k=0;k<256;k++)hist[k]=0;
    unsigned n=t.h*t.w;
    for(unsigned i=0;i<n;i++){
#pragma HLS PIPELINE II=2
        unsigned p=rgb[i],r=(p>>16)&255,g=(p>>8)&255,b=p&255;if(r!=g||g!=b)return 5;hist[r]++;
    }
    unsigned first=0;bool found=false;for(unsigned k=0;k<256;k++)if(!found&&hist[k]){first=k;found=true;}
    unsigned den=n-hist[first],total=0;
    for(unsigned k=0;k<256;k++){total+=hist[k];lut[k]=!den?uint8_t(first):(k<first?uint8_t(0):uint8_t(gray_level((total-hist[first])*255,den)));}
    for(unsigned i=0;i<n;i+=4){
        uint64_t a=0,b=0,c=0;
        for(unsigned j=0;j<4;j++){
#pragma HLS PIPELINE II=1
            unsigned v=(rgb[i+j]>>16)&255,e=lut[v],sum=v+e;if(sum>255)sum=255;
            a|=uint64_t(v)<<(16*j);b|=uint64_t(e)<<(16*j);c|=uint64_t(sum)<<(16*j);
        }
        work[(t.off+i)/4]=a;work[(t.off+n+i)/4]=b;work[(t.off+2*n+i)/4]=c;
    }
    return 0;
}
static void load_row(uint64_t*work,Tensor t,unsigned row,unsigned span,int16_t line[LINE]){
    uint64_t cache[65];
#pragma HLS BIND_STORAGE variable=cache type=ram_1p impl=bram
    for(unsigned ic=0;ic<t.c;ic++){
        unsigned start=t.off+ic*t.h*t.w+row*t.w,skip=start&3,words=(skip+t.w+3)/4;
        for(unsigned k=0;k<words;k++){
#pragma HLS PIPELINE II=1
            cache[k]=work[(start>>2)+k];
        }
        for(unsigned x=0;x<t.w;x++){
#pragma HLS PIPELINE II=1
            line[((row%span)*t.w+x)*t.c+ic]=int16_t(cache[(x+skip)>>2]>>(16*((x+skip)&3)));
        }
    }
}
static void flush_tile(uint64_t*work,Tensor dst,unsigned y,unsigned x,unsigned size,int16_t out[PE][TILE]){
    for(unsigned oc=0;oc<dst.c;oc++){
        if(size%4==0){
            for(unsigned p=0;p<size;p+=4){
#pragma HLS PIPELINE II=1
                uint64_t word=0;for(unsigned j=0;j<4;j++)word|=uint64_t(uint16_t(out[oc][p+j]))<<(16*j);
                work[(dst.off+oc*dst.h*dst.w+y*dst.w+x+p)/4]=word;
            }
        }else for(unsigned p=0;p<size;p++)put16(work,dst.off+oc*dst.h*dst.w+y*dst.w+x+p,out[oc][p]);
    }
}
static void convolution(const uint64_t*model,uint64_t*work,Tensor src,Tensor dst,const unsigned op[32]){
#pragma HLS INLINE off
    int16_t weights[PE][800];int16_t line[LINE],out[PE][TILE];int shifts[PE];
#pragma HLS ARRAY_PARTITION variable=weights complete dim=1
#pragma HLS BIND_STORAGE variable=weights type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=line type=ram_t2p impl=bram
#pragma HLS ARRAY_PARTITION variable=out complete dim=1
#pragma HLS ARRAY_PARTITION variable=shifts complete
    unsigned kh=op[6],kw=op[7],dy=op[8],dx=op[9],py=op[10],px=op[11],terms=op[15],span=(kh-1)*dy+1;
    for(unsigned oc=0;oc<dst.c;oc++){
        shifts[oc]=int32_t(m32(model,op[4]+oc));
        for(unsigned k=0;k<terms;k++){
#pragma HLS PIPELINE II=1
            unsigned pos=op[5]+oc*op[16]+k;weights[oc][k]=int16_t(model[pos>>2]>>(16*(pos&3)));
        }
    }
    int loaded=-1;
    for(unsigned y=0;y<dst.h;y++){
        unsigned maxrow=y+py;if(maxrow>=src.h)maxrow=src.h-1;
        while(loaded<int(maxrow)){loaded++;load_row(work,src,unsigned(loaded),span,line);}
        for(unsigned xb=0;xb<dst.w;xb+=TILE){
            unsigned size=dst.w-xb;if(size>TILE)size=TILE;
            for(unsigned p=0;p<size;p++){
                acc_t acc[PE][4];
#pragma HLS ARRAY_PARTITION variable=acc complete dim=0
                for(unsigned lane=0;lane<PE;lane++)for(unsigned bank=0;bank<4;bank++)acc[lane][bank]=0;
                unsigned k=0;
                for(unsigned ky=0;ky<kh;ky++)for(unsigned kx=0;kx<kw;kx++)for(unsigned ic=0;ic<src.c;ic++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=acc inter RAW distance=4
                    int yy=int(y+ky*dy)-int(py),xx=int(xb+p+kx*dx)-int(px);
                    int16_t value=0;if(yy>=0&&yy<int(src.h)&&xx>=0&&xx<int(src.w))value=line[((unsigned(yy)%span)*src.w+unsigned(xx))*src.c+ic];
                    unsigned bank=k&3;
                    for(unsigned lane=0;lane<PE;lane++){
#pragma HLS UNROLL
                        int16_t weight=lane<dst.c?weights[lane][k]:int16_t(0);int32_t product=int32_t(value)*int32_t(weight);
#pragma HLS BIND_OP variable=product op=mul impl=dsp
                        acc[lane][bank]+=product;
                    }
                    k++;
                }
                for(unsigned lane=0;lane<PE;lane++){
#pragma HLS UNROLL
                    if(lane<dst.c){int64_t sum=int64_t(acc[lane][0])+int64_t(acc[lane][1])+int64_t(acc[lane][2])+int64_t(acc[lane][3]);out[lane][p]=sat(even64(sum,shifts[lane]));}
                }
            }
            flush_tile(work,dst,y,xb,size,out);
        }
    }
}
static void prewitt(uint64_t*work,Tensor src,Tensor dst){
#pragma HLS INLINE off
    unsigned n=src.h*src.w;int16_t line[4096];int loaded=-1;
#pragma HLS BIND_STORAGE variable=line type=ram_t2p impl=bram
    for(unsigned y=0;y<src.h;y++){
        unsigned end=y+2;if(end>=src.h)end=src.h-1;
        while(loaded<int(end)){loaded++;load_row(work,src,unsigned(loaded),5,line);}
        for(unsigned c=0;c<3;c++)for(unsigned xb=0;xb<src.w;xb+=4){
            uint64_t word=0;
            for(unsigned j=0;j<4;j++){
                int x=int(xb+j),sum=0;
                for(int ky=0;ky<5;ky++)for(int kx=0;kx<5;kx++){
#pragma HLS PIPELINE II=1
                    int yy=int(y)+ky-2,xx=x+kx-2;if(yy>=0&&yy<int(src.h)&&xx>=0&&xx<int(src.w))sum+=int(line[((unsigned(yy)%5)*src.w+unsigned(xx))*3+c])*(2-kx);
                }
                word|=uint64_t(uint16_t(sat(sum)))<<(16*j);
            }
            work[(dst.off+c*n+y*src.w+xb)/4]=word;
        }
    }
}
static unsigned normalization(const uint64_t*model,uint64_t*work,Tensor src,Tensor dst,unsigned params){
#pragma HLS INLINE off
    unsigned n=src.h*src.w;
    for(unsigned c=0;c<src.c;c++){
        ap_int<36> sum=0;ap_uint<50> squares=0;
        for(unsigned i=0;i<n;i+=4){
            uint64_t word=work[(src.off+c*n+i)/4];
            for(unsigned j=0;j<4;j++){
#pragma HLS PIPELINE II=1
                ap_int<16> v=int16_t(word>>(16*j));ap_int<32> square=v*v;sum+=v;squares+=ap_uint<32>(square);
            }
        }
        unsigned base=params/2+c*8;
        ap_uint<128> eps=(ap_uint<128>(model[base+4])<<64)|model[base+3];ap_int<64> gamma=model[base+5],beta=model[base+6];int exp=int(ap_int<64>(model[base+7]));
        ap_uint<128> base_variance=ap_uint<128>(ap_uint<19>(n)*squares)-ap_uint<128>(ap_int<72>(sum*sum)),variance=base_variance+eps;if(variance<base_variance)return 6;ap_uint<64> root=isqrt128(variance);int e=6-exp;ap_int<128> a=0,b=beta;
        if(e>=0){b=b<<e;if(root)a=div_even(ap_int<128>(gamma)<<e,ap_uint<128>(root));}
        else{b=shift_even(b,unsigned(-e));if(root)a=div_even(ap_int<128>(gamma),ap_uint<128>(root)<<unsigned(-e));}
        ap_int<128> minimum=-(ap_int<128>(1)<<63),maximum=(ap_int<128>(1)<<63)-1;
        if(a<minimum||a>maximum||b<minimum||b>maximum)return 6;
        int64_t aa=int64_t(a),bb=int64_t(b),s=int64_t(sum);
        for(unsigned i=0;i<n;i+=4){
            uint64_t word=work[(src.off+c*n+i)/4],packed=0;
            for(unsigned j=0;j<4;j++){
#pragma HLS PIPELINE II=1
                int16_t v=int16_t(word>>(16*j));int64_t diff=int64_t(n)*v-s;
#ifdef __SYNTHESIS__
                ap_int<100> product=ap_int<36>(diff)*ap_int<64>(aa);ap_int<128> value=shift_even(ap_int<128>(product)+bb,36);int16_t out=value>32767?int16_t(32767):(value< -32768?int16_t(-32768):int16_t(value));
#else
                __int128 value=__int128(diff)*aa+bb;bool neg=value<0;unsigned __int128 mag=neg?-value:value,whole=mag>>36,rem=mag-(whole<<36),half=(uint64_t(1)<<35);if(rem>half||(rem==half&&(whole&1)))whole++;__int128 rounded=neg?-__int128(whole):__int128(whole);int16_t out=rounded>32767?32767:(rounded< -32768?-32768:int16_t(rounded));
#endif
                packed|=uint64_t(uint16_t(out))<<(16*j);
            }
            work[(dst.off+c*n+i)/4]=packed;
        }
    }
    return 0;
}
static void elementwise(uint64_t*work,Tensor src,Tensor other,Tensor dst,const unsigned op[32]){
    for(unsigned i=0;i<dst.count;i+=4){
        uint64_t word=0,a=0,b=0;int selected_shift=0;
        if(op[0]==CAT){if(i<src.count){a=work[(src.off+i)/4];selected_shift=int(op[19]);}else{a=work[(other.off+i-src.count)/4];selected_shift=int(op[20]);}}
        else{a=work[(src.off+i)/4];if(op[0]==ADD)b=work[(other.off+i)/4];}
        for(unsigned j=0;j<4;j++){
#pragma HLS PIPELINE II=1
            int64_t v=0,va=int16_t(a>>(16*j)),vb=int16_t(b>>(16*j));
            if(op[0]==CAT)v=even64(va,selected_shift);
            else if(op[0]==ADD)v=even64(va*(int64_t(1)<<op[19])+vb*(int64_t(1)<<op[20]),int(op[21]));
            else{v=va;if(v<0)v=0;v=even64(v,int(op[19]));}
            word|=uint64_t(uint16_t(sat(v)))<<(16*j);
        }
        work[(dst.off+i)/4]=word;
    }
}
static void plane_row(uint64_t*work,Tensor src,unsigned channel,unsigned y,int16_t row[256]){
    unsigned begin=src.off+channel*src.h*src.w+y*src.w,skip=begin&3;uint64_t cache[65];
    for(unsigned k=0;k<(skip+src.w+3)/4;k++){
#pragma HLS PIPELINE II=1
        cache[k]=work[(begin>>2)+k];
    }
    for(unsigned x=0;x<src.w;x++){
#pragma HLS PIPELINE II=1
        row[x]=int16_t(cache[(skip+x)>>2]>>(16*((skip+x)&3)));
    }
}
static void spatial(uint64_t*work,Tensor src,Tensor dst,const unsigned op[32]){
    int16_t r0[256],r1[256];
#pragma HLS BIND_STORAGE variable=r0 type=ram_t2p impl=bram
#pragma HLS BIND_STORAGE variable=r1 type=ram_t2p impl=bram
    for(unsigned c=0;c<dst.c;c++)for(unsigned y=0;y<dst.h;y++){
        int y0=op[0]==POOL?int(2*y):(y==0?0:int((y-1)/2)),y1=op[0]==POOL?int(2*y+1):int((y+1)/2);if(y1>=int(src.h))y1=src.h-1;
        plane_row(work,src,c,unsigned(y0),r0);plane_row(work,src,c,unsigned(y1),r1);
        for(unsigned xb=0;xb<dst.w;xb+=4){
            uint64_t packed=0;unsigned size=dst.w-xb;if(size>4)size=4;
            for(unsigned j=0;j<size;j++){
#pragma HLS PIPELINE II=1
                unsigned x=xb+j;int64_t v=0;
                if(op[0]==POOL){v=r0[2*x];if(r0[2*x+1]>v)v=r0[2*x+1];if(r1[2*x]>v)v=r1[2*x];if(r1[2*x+1]>v)v=r1[2*x+1];}
                else{unsigned x0=x==0?0:(x-1)/2,x1=(x+1)/2;if(x1>=src.w)x1=src.w-1;int fy=(y&1)?1:3,fx=(x&1)?1:3;v=int64_t(r0[x0])*(4-fy)*(4-fx)+int64_t(r0[x1])*(4-fy)*fx+int64_t(r1[x0])*fy*(4-fx)+int64_t(r1[x1])*fy*fx;v=even64(v,int(op[19]));}
                packed|=uint64_t(uint16_t(sat(v)))<<(16*j);
            }
            unsigned target=dst.off+c*dst.h*dst.w+y*dst.w+xb;
            if(size==4)work[target/4]=packed;else for(unsigned j=0;j<size;j++)put16(work,target+j,int16_t(packed>>(16*j)));
        }
    }
}
void texture_integer(const uint64_t*model,uint64_t*work,const uint32_t*rgb,uint32_t*result,unsigned width,unsigned height){
// AXI depth annotations size the reduced-geometry co-sim transaction buffers.
// Actual DDR bounds are validated below against the sealed128MiB arena contract.
#pragma HLS INTERFACE m_axi port=model offset=slave bundle=modelmem depth=65536 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=work offset=slave bundle=workmem depth=131072 max_read_burst_length=64 max_write_burst_length=64
#pragma HLS INTERFACE m_axi port=rgb offset=slave bundle=inputmem depth=4096 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=result offset=slave bundle=outmem depth=4096 max_write_burst_length=64
#pragma HLS INTERFACE s_axilite port=return bundle=control
#pragma HLS INTERFACE s_axilite port=model bundle=control
#pragma HLS INTERFACE s_axilite port=work bundle=control
#pragma HLS INTERFACE s_axilite port=rgb bundle=control
#pragma HLS INTERFACE s_axilite port=result bundle=control
#pragma HLS INTERFACE s_axilite port=width bundle=control
#pragma HLS INTERFACE s_axilite port=height bundle=control
    static unsigned sequence=0;for(unsigned k=0;k<16;k++)result[k]=0;result[0]=HFE_MAGIC;result[1]=1;result[9]=sequence;
    unsigned h[64];for(unsigned k=0;k<64;k++)h[k]=m32(model,k);result[10]=1;
    if(h[0]!=0x17000001u||h[27]!=HFE_MAGIC||h[1]<256||h[1]>MAX_MODEL_BYTES||h[1]%8||h[2]==0||h[2]>96||h[17]!=h[2]+1||h[4]!=1||h[16]==0||h[16]>MAX_WORK_BYTES||h[16]%8||h[33]!=32||h[34]!=16||h[28]!=width||h[29]!=height||width<16||height<16||width>256||height>1408||width%16||height%16||h[30]!=0||h[31]!=h[2]){result[1]=4;return;}
    if(uint64_t(h[18])+h[17]*16u>h[1]/4||uint64_t(h[19])+h[2]*32u>h[1]/4){result[1]=4;return;}
    Tensor t[97];result[10]=2;
    for(unsigned k=0;k<h[17];k++){
        result[11]=k;unsigned b=h[18]+k*16;Tensor a;a.off=m32(model,b);a.c=m32(model,b+1);a.h=m32(model,b+2);a.w=m32(model,b+3);a.count=m32(model,b+7);
        if(!a.c||a.c>64||!a.h||a.h>1408||!a.w||a.w>256||a.count!=a.c*a.h*a.w||a.count%4||a.off%4||uint64_t(a.off)+a.count>h[16]/2){result[1]=4;return;}t[k]=a;
    }
    if(t[0].c!=3||t[0].h!=height||t[0].w!=width){result[1]=4;return;}
    // Validate the entire program before any image processing or work writes.
    for(unsigned k=0;k<h[2];k++){
        unsigned op[32];for(unsigned j=0;j<32;j++)op[j]=m32(model,h[19]+k*32+j);result[10]=10+op[0];result[11]=k;
        if(op[3]!=k+1||op[1]>k||op[0]<2||op[0]>10||((op[0]==ADD||op[0]==CAT)&&op[2]>k)||uint64_t(op[4])+op[22]>h[1]/4){result[1]=4;return;}
        Tensor a=t[op[1]],d=t[op[3]],b=t[op[2]];
        if(overlap(a,d)||((op[0]==ADD||op[0]==CAT)&&overlap(b,d))){result[1]=7;return;}
        if(op[0]==CONV){
            unsigned span=(op[6]-1)*op[8]+1;
            if(!op[6]||op[6]>5||!op[7]||op[7]>5||!op[8]||op[8]>2||!op[9]||op[9]>2||op[10]*2!=span-1||op[11]*2!=(op[7]-1)*op[9]||a.h!=d.h||a.w!=d.w||op[12]!=a.c||op[13]!=d.c||op[14]!=1||op[15]!=a.c*op[6]*op[7]||op[15]>800||d.c>PE||span*a.w*a.c>LINE||op[16]<op[15]||uint64_t(op[5])+op[16]*d.c>h[1]/2||op[22]!=d.c){result[1]=4;return;}
            for(unsigned c=0;c<d.c;c++){int shift=int32_t(m32(model,op[4]+c));if(shift< -16||shift>48){result[1]=4;return;}}
        }else if(op[0]==PREWITT){if(a.c!=3||d.c!=3||a.h!=d.h||a.w!=d.w){result[1]=4;return;}}
        else if(op[0]==NORM){
            if(a.c!=d.c||a.h!=d.h||a.w!=d.w||op[4]%2||op[22]!=a.c*16){result[1]=4;return;}
            for(unsigned c=0;c<a.c;c++){unsigned b=op[4]/2+c*8;ap_int<64> g=model[b+5],beta=model[b+6],e=model[b+7];if(model[b]!=a.h*a.w||g< -(ap_int<64>(1)<<40)||g>(ap_int<64>(1)<<40)||beta< -(ap_int<64>(1)<<40)||beta>(ap_int<64>(1)<<40)||e< -38||e>16){result[1]=4;return;}}
        }else if(op[0]==POOL){if(a.c!=d.c||a.h!=2*d.h||a.w!=2*d.w){result[1]=4;return;}}
        else if(op[0]==UP){if(a.c!=d.c||2*a.h!=d.h||2*a.w!=d.w||int(op[19])< -16||int(op[19])>48){result[1]=4;return;}}
        else if(op[0]==CAT){if(a.h!=d.h||a.w!=d.w||b.h!=d.h||b.w!=d.w||a.c+b.c!=d.c||int(op[19])< -16||int(op[19])>48||int(op[20])< -16||int(op[20])>48){result[1]=4;return;}}
        else if(op[0]==ADD){if(a.c!=d.c||a.h!=d.h||a.w!=d.w||b.c!=d.c||b.h!=d.h||b.w!=d.w||op[19]>16||op[20]>16||int(op[21])< -16||int(op[21])>48){result[1]=4;return;}}
        else if(op[0]==RELU){if(a.c!=d.c||a.h!=d.h||a.w!=d.w||int(op[19])< -16||int(op[19])>48){result[1]=4;return;}}
        else if(op[0]==MASK){if(k+1!=h[2]||a.c!=1||d.c!=1||a.h!=height||a.w!=width||d.h!=height||d.w!=width){result[1]=4;return;}}
    }
    result[10]=0;result[11]=0;unsigned status=preprocess(rgb,work,t[0]);if(status){result[1]=status;return;}
#ifndef __SYNTHESIS__
    if(hfe_observer)hfe_observer(0,work,t[0].off,t[0].count);
#endif
    for(unsigned k=0;k<h[2];k++){
        unsigned op[32];for(unsigned j=0;j<32;j++)op[j]=m32(model,h[19]+k*32+j);Tensor a=t[op[1]],b=t[op[2]],d=t[op[3]];
        switch(op[0]){
            case CONV:convolution(model,work,a,d,op);break;
            case PREWITT:prewitt(work,a,d);break;
            case NORM:{unsigned error=normalization(model,work,a,d,op[4]);if(error){result[1]=error;return;}break;}
            case RELU:case ADD:case CAT:elementwise(work,a,b,d,op);break;
            case POOL:case UP:spatial(work,a,d,op);break;
            case MASK:{
                unsigned positive=0,n=width*height;
                for(unsigned i=0;i<n;i+=4){uint64_t value=work[(a.off+i)/4],word=0;for(unsigned j=0;j<4;j++){unsigned flag=int16_t(value>>(16*j))>0;result[17+i+j]=flag;positive+=flag;word|=uint64_t(flag)<<(16*j);}work[(d.off+i)/4]=word;}
                result[2]=positive!=0;result[3]=positive;result[4]=0;result[5]=1;result[6]=positive;result[7]=n;result[16]=positive;break;
            }
        }
        result[8]=k+1;
#ifndef __SYNTHESIS__
        if(hfe_observer)hfe_observer(op[3],work,d.off,d.count);
#endif
    }
    result[9]=++sequence;result[1]=0;
}
