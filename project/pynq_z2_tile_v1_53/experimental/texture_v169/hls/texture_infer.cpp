#include <stdint.h>
#include <math.h>
#include <ap_int.h>
typedef ap_uint<11> dim_t;
typedef ap_uint<17> tile_t;

// One inference launch runs the complete graph. PS only transports opaque
// model/RGB words, maintains cache ownership, and starts/polls this IP.
// Scratch is reused across convolution, projection and nearest-normal search.
static const int LANES=4, DEPTH=28672, MAX_DIM=64;
static float sf(uint32_t u){union{uint32_t u;float f;}v;v.u=u;return v.f;}
static uint32_t su(float f){union{uint32_t u;float f;}v;v.f=f;return v.u;}
static float get(const uint32_t *p,unsigned i){return sf(p[i]);}
static void put(uint32_t *p,unsigned i,float f){p[i]=su(f);}
static float clip(float v,float lo,float hi){return v<lo?lo:v>hi?hi:v;}

static void mac4(const float a[LANES],const float b[LANES],const float old[LANES],float out[LANES]) {
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS ARRAY_PARTITION variable=a complete
#pragma HLS ARRAY_PARTITION variable=b complete
#pragma HLS ARRAY_PARTITION variable=old complete
#pragma HLS ARRAY_PARTITION variable=out complete
    for(int i=0;i<LANES;i++) {
#pragma HLS UNROLL
        out[i]=old[i]+a[i]*b[i];
    }
}
static float lerp(float a,float b,float t) {
#pragma HLS INLINE off
#pragma HLS ALLOCATION instances=fmul limit=1 operation
#pragma HLS ALLOCATION instances=fadd limit=1 operation
    return a*(1.f-t)+b*t;
}
static float interp4(float a,float b,float c,float d,float fx,float fy) {
#pragma HLS INLINE off
#pragma HLS ALLOCATION instances=lerp limit=1 function
    float top=lerp(a,b,fx),bottom=lerp(c,d,fx);
    return lerp(top,bottom,fy);
}
static float addrelu(float a,float b) {
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    float v=a+b;
#pragma HLS BIND_OP variable=v op=fadd impl=fulldsp latency=5
    return v<0.f?0.f:v;
}

static bool convolution(const uint32_t *model,uint32_t *work,const unsigned t[16],float ram[LANES][DEPTH]){
    unsigned src=t[1],dst=t[2],wo=t[3],bo=t[4];
    dim_t ih=t[5],iw=t[6],ic=t[7],oc=t[8];
    int k=t[9]&7,stride=t[10]&3,pad=t[11]&7,relu=t[12]&1;
    if((stride!=1&&stride!=2)||(k!=1&&k!=3&&k!=7))return false;
    dim_t oh=((int(ih)+2*pad-k)>>(stride==2?1:0))+1,ow=((int(iw)+2*pad-k)>>(stride==2?1:0))+1;
    int tile=ic*k*iw,base=(tile+LANES-1)/LANES,taps=ic*k*k;
    if(base+taps>DEPTH || k<1 || k>7 || oc%LANES)return false;
    for(int y=0;y<oh;y++){
        for(int c=0;c<ic;c++)for(int r=0;r<k;r++)for(int x=0;x<iw;x++){
#pragma HLS PIPELINE II=1
            int iy=y*stride+r-pad;int index=(c*k+r)*iw+x;
            ram[index&(LANES-1)][index/ LANES]=(iy>=0&&iy<ih)?get(work,src+(c*ih+iy)*iw+x):0.f;
        }
        for(int o=0;o<oc;o+=LANES){
            float bias[LANES];
#pragma HLS ARRAY_PARTITION variable=bias complete
            for(int lane=0;lane<LANES;lane++){
                bias[lane]=get(model,bo+o+lane);
                for(int tap=0;tap<taps;tap++){
#pragma HLS PIPELINE II=1
                    ram[lane][base+tap]=get(model,wo+(o+lane)*taps+tap);
                }
            }
            for(int x=0;x<ow;x++){
                float sums[LANES][32];
#pragma HLS ARRAY_PARTITION variable=sums complete dim=0
                for(int lane=0;lane<LANES;lane++)for(int slot=0;slot<32;slot++){
#pragma HLS UNROLL
                    sums[lane][slot]=0;
                }
                for(int c=0;c<ic;c++)for(int r=0;r<k;r++)for(int col=0;col<k;col++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=sums inter false
                    int tap=(c*k+r)*k+col,ix=x*stride+col-pad,index=(c*k+r)*iw+ix;
                    float v=(ix>=0&&ix<iw)?ram[index&(LANES-1)][index/ LANES]:0.f;
                    float aa[LANES],bb[LANES],cc[LANES],dd[LANES];
#pragma HLS ARRAY_PARTITION variable=aa complete
#pragma HLS ARRAY_PARTITION variable=bb complete
#pragma HLS ARRAY_PARTITION variable=cc complete
#pragma HLS ARRAY_PARTITION variable=dd complete
                    for(int lane=0;lane<LANES;lane++){
#pragma HLS UNROLL
                        aa[lane]=v;bb[lane]=ram[lane][base+tap];cc[lane]=sums[lane][tap&31];
                    }
                    mac4(aa,bb,cc,dd);
                    for(int lane=0;lane<LANES;lane++){
#pragma HLS UNROLL
                        sums[lane][tap&31]=dd[lane];
                    }
                }
                for(int lane=0;lane<LANES;lane++){
                    float a=0.f;
                    for(int slot=0;slot<32;slot++)a+=sums[lane][slot];
                    float v=a+bias[lane];put(work,dst+((o+lane)*oh+y)*ow+x,(relu&&v<0)?0.f:v);
                }
            }
        }
    }
    return true;
}

static bool pooling(uint32_t *work,const unsigned t[16],float ram[LANES][DEPTH]){
    unsigned src=t[1],dst=t[2];dim_t h=t[5],w=t[6],channels=t[7];int stride=t[10]&3,pad=1;
    if(stride!=1&&stride!=2)return false;
    dim_t oh=((int(h)+2*pad-3)>>(stride==2?1:0))+1,ow=((int(w)+2*pad-3)>>(stride==2?1:0))+1;
    if(channels*3*w>LANES*DEPTH)return false;
    for(int y=0;y<oh;y++){
        for(int c=0;c<channels;c++)for(int r=0;r<3;r++)for(int x=0;x<w;x++){
#pragma HLS PIPELINE II=1
            int iy=y*stride+r-1,index=(c*3+r)*w+x;
            ram[index&(LANES-1)][index/ LANES]=(iy>=0&&iy<h)?get(work,src+(c*h+iy)*w+x):(t[0]==2?-3.402823e38f:0.f);
        }
        for(int c=0;c<channels;c++)for(int x=0;x<ow;x++){
            float value=t[0]==2?-3.402823e38f:0.f;
            for(int r=0;r<3;r++)for(int col=0;col<3;col++){
                int ix=x*stride+col-1,index=(c*3+r)*w+ix;
                float v=(ix>=0&&ix<w)?ram[index&(LANES-1)][index/ LANES]:(t[0]==2?-3.402823e38f:0.f);
                value=t[0]==2?(value>v?value:v):value+v;
            }
            put(work,dst+(c*oh+y)*ow+x,t[0]==2?value:value*(1.f/9.f));
        }
    }
    return true;
}

static float bilinear(const uint32_t *p,unsigned offset,int h,int w,float y,float x){
#pragma HLS INLINE off
    x=clip(x,0.f,float(w-1));y=clip(y,0.f,float(h-1));int x0=int(x),y0=int(y);
    int x1=x0+1<w?x0+1:x0,y1=y0+1<h?y0+1:y0;float fx=x-x0,fy=y-y0;
    float a=get(p,offset+y0*w+x0),b=get(p,offset+y0*w+x1),c=get(p,offset+y1*w+x0),d=get(p,offset+y1*w+x1);
    return interp4(a,b,c,d,fx,fy);
}

void texture_infer(const uint32_t *model,uint32_t *work,const uint32_t *rgb,uint32_t *result,unsigned width,unsigned height){
#pragma HLS INTERFACE m_axi port=model offset=slave bundle=modelmem depth=4096 max_read_burst_length=64
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
#pragma HLS ALLOCATION instances=mac4 limit=1 function
#pragma HLS ALLOCATION instances=interp4 limit=1 function
    // Interface depths size the small RTL unit-test adapters; AXI addresses
    // remain 64-bit and firmware validates the full external DDR allocations.
    float ram[LANES][DEPTH];
#pragma HLS ARRAY_PARTITION variable=ram complete dim=1
#pragma HLS BIND_STORAGE variable=ram type=ram_2p impl=bram
    for(int i=0;i<16;i++)result[i]=0;
    result[0]=0x16900001;result[1]=1;
    unsigned header[32];
    for(int i=0;i<32;i++)header[i]=model[i];
    dim_t side=header[3],grid=header[4],dim=header[5],centers=header[6],ca=header[20],cb=header[21],fd=ca+cb;
    if(header[0]!=0x16900001 || width<1||height<1||width>1024||height>1024||side<4||side>448||dim<1||dim>64||centers<1||centers>1024||fd<1||fd>1536||grid<2||grid>56||header[2]>96)return;
    if(((fd+LANES-1)/LANES)+((dim+LANES-1)/LANES)*fd>DEPTH || centers*dim>LANES*DEPTH)return;
    // Raw RGB decoding is transport-only on the PC. Resize and normalization
    // are done here, before the first convolution.
    for(int y=0;y<side;y++)for(int x=0;x<side;x++){
        float sx=clip((x+.5f)*(float(width)/side)-.5f,0.f,float(width-1));
        float sy=clip((y+.5f)*(float(height)/side)-.5f,0.f,float(height-1));
        int x0=int(sx),y0=int(sy),x1=x0+1<int(width)?x0+1:x0,y1=y0+1<int(height)?y0+1:y0;
        float fx=sx-x0,fy=sy-y0;uint32_t a=rgb[y0*width+x0],b=rgb[y0*width+x1],c=rgb[y1*width+x0],d=rgb[y1*width+x1];
        for(int ch=0;ch<3;ch++){
            int shift=16-8*ch;
            float v=interp4((a>>shift)&255,(b>>shift)&255,(c>>shift)&255,(d>>shift)&255,fx,fy);
            float mean=ch==0?.485f:ch==1?.456f:.406f,std=ch==0?.229f:ch==1?.224f:.225f;
            put(work,header[7]+(ch*side+y)*side+x,(v*(1.f/255.f)-mean)/std);
        }
    }
    for(unsigned task=0;task<header[2];task++){
        unsigned t[16];for(int i=0;i<16;i++)t[i]=model[64+task*16+i];
        if(t[0]==1){if(!convolution(model,work,t,ram)){result[1]=2;return;}}
        else if(t[0]==2||t[0]==4){if(!pooling(work,t,ram)){result[1]=3;return;}}
        else if(t[0]==3){
            for(unsigned i=0;i<t[5];i++){
#pragma HLS PIPELINE off
                float v=addrelu(get(work,t[1]+i),get(work,t[3]+i));put(work,t[2]+i,v);
            }
        }else{result[1]=4;return;}
        result[8]=task+1;
    }
    // PCA matrix is normal-data-derived and loaded once into the reused RAM.
    int prefix=(fd+LANES-1)/LANES;
    for(int o=0;o<dim;o++)for(int k=0;k<fd;k++){
#pragma HLS PIPELINE II=1
        ram[o&(LANES-1)][prefix+(o/LANES)*fd+k]=get(model,header[13]+o*fd+k);
    }
    for(int y=0;y<grid;y++)for(int x=0;x<grid;x++){
        for(int k=0;k<fd;k++){
            float v=k<ca?get(work,header[11]+(k*grid+y)*grid+x):bilinear(work,header[12]+(k-ca)*(grid/2)*(grid/2),grid/2,grid/2,(y+.5f)*.5f-.5f,(x+.5f)*.5f-.5f);
            ram[k&(LANES-1)][k/LANES]=v-get(model,header[14]+k);
        }
        for(int o=0;o<dim;o+=LANES){
            float acc[LANES][8];
#pragma HLS ARRAY_PARTITION variable=acc complete dim=0
            for(int lane=0;lane<LANES;lane++)for(int slot=0;slot<8;slot++){
#pragma HLS UNROLL
                acc[lane][slot]=0.f;
            }
            for(int k=0;k<fd;k++){
#pragma HLS PIPELINE II=1
                float v=ram[k&(LANES-1)][k/LANES];
                float aa[LANES],bb[LANES],cc[LANES],dd[LANES];
#pragma HLS ARRAY_PARTITION variable=aa complete
#pragma HLS ARRAY_PARTITION variable=bb complete
#pragma HLS ARRAY_PARTITION variable=cc complete
#pragma HLS ARRAY_PARTITION variable=dd complete
                for(int lane=0;lane<LANES;lane++){
#pragma HLS UNROLL
                    aa[lane]=v;bb[lane]=(o+lane<dim)?ram[lane][prefix+((o+lane)/LANES)*fd+k]:0.f;cc[lane]=acc[lane][k&7];
                }
                mac4(aa,bb,cc,dd);
                for(int lane=0;lane<LANES;lane++){
#pragma HLS UNROLL
                    acc[lane][k&7]=dd[lane];
                }
            }
            for(int lane=0;lane<LANES;lane++)if(o+lane<dim){float v=0;for(int slot=0;slot<8;slot++)v+=acc[lane][slot];put(work,header[8]+(y*grid+x)*dim+o+lane,v);}
        }
    }
    // The compressed nominal bank fits wholly in the same on-chip memory.
    for(int i=0;i<centers*dim;i++){
#pragma HLS PIPELINE II=1
        ram[i&(LANES-1)][i/LANES]=get(model,header[15]+i);
    }
    for(int q=0;q<grid*grid;q++){
        float query[64];
#pragma HLS ARRAY_PARTITION variable=query cyclic factor=4
        for(int k=0;k<dim;k++)query[k]=get(work,header[8]+q*dim+k);
        float best=3.402823e38f;
        for(int n=0;n<centers;n++){
            float acc[LANES][8];
#pragma HLS ARRAY_PARTITION variable=acc complete dim=0
            for(int lane=0;lane<LANES;lane++)for(int slot=0;slot<8;slot++){
#pragma HLS UNROLL
                acc[lane][slot]=0;
            }
            for(int k=0;k<dim;k+=LANES){
#pragma HLS PIPELINE II=1
                float aa[LANES],bb[LANES],cc[LANES],dd[LANES];
#pragma HLS ARRAY_PARTITION variable=aa complete
#pragma HLS ARRAY_PARTITION variable=bb complete
#pragma HLS ARRAY_PARTITION variable=cc complete
#pragma HLS ARRAY_PARTITION variable=dd complete
                for(int lane=0;lane<LANES;lane++){
#pragma HLS UNROLL
                    int index=n*dim+k+lane;float d=(k+lane<dim)?query[k+lane]-ram[index&(LANES-1)][index/ LANES]:0.f;
                    aa[lane]=d;bb[lane]=d;cc[lane]=acc[lane][(k/LANES)&7];
                }
                mac4(aa,bb,cc,dd);
                for(int lane=0;lane<LANES;lane++){
#pragma HLS UNROLL
                    acc[lane][(k/LANES)&7]=dd[lane];
                }
            }
            float sum=0;for(int lane=0;lane<LANES;lane++)for(int slot=0;slot<8;slot++)sum+=acc[lane][slot];
            best=sum<best?sum:best;
        }
        put(work,header[9]+q,sqrtf(best));
    }
    float peak=0.f,threshold=sf(header[16]);
    for(int y=0;y<grid;y++)for(int x=0;x<grid;x++){
        float sum=0;
        for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){
            int iy=y+dy<0?0:y+dy>=grid?int(grid)-1:y+dy,ix=x+dx<0?0:x+dx>=grid?int(grid)-1:x+dx;
            sum+=get(work,header[9]+iy*grid+ix);
        }
        float v=sum*(1.f/9.f);put(work,header[10]+y*grid+x,v);put(result,16+y*grid+x,v);peak=v>peak?v:peak;
    }
    unsigned count=0;
    for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++){
        float sy=(y+.5f)*(float(grid)/height)-.5f,sx=(x+.5f)*(float(grid)/width)-.5f;
        float v=bilinear(work,header[10],grid,grid,sy,sx);unsigned alarm=v>threshold?1:0;
        result[16+grid*grid+y*width+x]=alarm;count+=alarm;
    }
    result[1]=0;result[2]=peak>threshold?1:0;result[3]=su(peak);result[4]=header[16];result[5]=grid;result[6]=count;result[7]=width*height;
}
