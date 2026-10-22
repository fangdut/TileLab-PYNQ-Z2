// Experimental row batches + interleaved exact projection. NOT board accepted.
// SPDX-License-Identifier: MIT
// Complete integer MobileNetV2 + normal-codebook inference. No ARM vision.
#include <stdint.h>
#include <ap_int.h>
#include <hls_stream.h>
typedef ap_uint<128> pack_t;
typedef ap_int<8> i8;
typedef ap_int<16> i16;
typedef ap_int<32> i32;
typedef ap_int<64> i64;
typedef ap_uint<10> shape_t;
static const int O=16,I=8,RD=1024,LD=2048;
static const int SPATIAL_3X3_IC_LIMIT=8;
static const int DW_SPAN=16;
// Geometry is validated before this lookup: side=8..224, grid=side/8.
// Packed 11-bit lengths replace a fabric multiply/add/compare critical path.
static ap_uint<22> feature_layout(shape_t grid){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    static const ap_uint<22> words[32]={0U,2U,12296U,12306U,49184U,49202U,110664U,110690U,196736U,196770U,307400U,307442U,442656U,442706U,602504U,602562U,786944U,787010U,995976U,996050U,1229600U,1229682U,1487816U,1487906U,1770624U,1770722U,2078024U,2078130U,2410016U,2410130U,2766600U,2766722U};
#pragma HLS BIND_STORAGE variable=words type=rom_1p impl=lutram
    return words[ap_uint<5>(grid)];
}
// This model has only the RGB first layer as a standard3x3 convolution.
// Runtime rejects unsupported standard3x3 input groups; nearest keeps its own
// center index and does not consume these spatial coordinates.
static ap_uint<4> spatial_tap_xy(ap_uint<4> tap){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    static const ap_uint<4> spatial_xy[16]={0,1,2,4,5,6,8,9,10,0,0,0,0,0,0,0};
#pragma HLS BIND_STORAGE variable=spatial_xy type=rom_1p impl=lutram
    return spatial_xy[tap];
}
// Split the27x37 input-normalization multiply before pipelining; a single
// fabric multiply merely followed by registers did not meet the clock goal.
static ap_uint<41> times4_37(ap_uint<4> value,ap_uint<37> multiplier){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=3 max=3
    ap_uint<41> a=value[0]?ap_uint<41>(multiplier):ap_uint<41>(0);
    ap_uint<41> b=value[1]?(ap_uint<41>(multiplier)<<1):ap_uint<41>(0);
    ap_uint<41> c=value[2]?(ap_uint<41>(multiplier)<<2):ap_uint<41>(0);
    ap_uint<41> d=value[3]?(ap_uint<41>(multiplier)<<3):ap_uint<41>(0);
    return (a+b)+(c+d);
}
static ap_int<64> normalize_fabric(ap_uint<27> value,ap_int<37> coefficient){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_uint<37> magnitude=coefficient<0?ap_uint<37>(-ap_int<38>(coefficient)):ap_uint<37>(coefficient);
    ap_uint<64> pieces[7];
#pragma HLS ARRAY_PARTITION variable=pieces complete
    for(int nibble=0;nibble<7;nibble++){
#pragma HLS UNROLL
        ap_uint<4> v=ap_uint<4>(value>>(4*nibble));
        pieces[nibble]=ap_uint<64>(times4_37(v,magnitude))<<(4*nibble);
    }
    ap_uint<64> a=pieces[0]+pieces[1],b=pieces[2]+pieces[3],c=pieces[4]+pieces[5];
    ap_uint<64> result=((a+b)+c)+pieces[6];
    ap_int<64> signed_result=result;
    if(coefficient<0)signed_result=-signed_result;
    return signed_result;
}
// Exact widths: den<=448, horizontal<=255*den<2^17,
// final<=255*den*den<=51179520<2^26. Weights are nonnegative remainders.
static ap_uint<27> bilinear_u27(ap_uint<8> a,ap_uint<8> b,ap_uint<8> c,ap_uint<8> d,
                               ap_uint<9> den,ap_uint<9> fx,ap_uint<9> fy){
#pragma HLS INLINE
    ap_uint<9> wx=den-fx,wy=den-fy;
    ap_uint<17> ax=a*wx,bx=b*fx,cx=c*wx,dx=d*fx;
    ap_uint<17> top=ax+bx,bottom=cx+dx;
    ap_uint<26> upper=top*wy,lower=bottom*fy;
    return ap_uint<27>(upper)+ap_uint<27>(lower);
}
// Decode the supported raw32-bit opcode once, before the long-lived control
// phase. Unsupported values map to0 and retain the original task error3.
static ap_uint<3> decode_operation(uint32_t raw){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    ap_uint<3> flags=0;
    if(raw==1)flags=1;
    else if(raw==2)flags=2;
    else if(raw==3)flags=4;
    return flags;
}

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
static ap_uint<36> times4(ap_uint<4> v,ap_uint<32> m){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    ap_uint<36> a=(v[0]?ap_uint<36>(m):ap_uint<36>(0))+(v[1]?(ap_uint<36>(m)<<1):ap_uint<36>(0));
    ap_uint<36> b=(v[2]?(ap_uint<36>(m)<<2):ap_uint<36>(0))+(v[3]?(ap_uint<36>(m)<<3):ap_uint<36>(0));
    return a+b;
}
static int rq8(i8 v,uint32_t m){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_uint<8> magnitude=v<0?ap_uint<8>(-v):ap_uint<8>(v);
    ap_uint<40> product=ap_uint<40>(times4(magnitude.range(3,0),m))+(ap_uint<40>(times4(magnitude.range(7,4),m))<<4);
    return int(rounded(v<0?-int64_t(product):int64_t(product),28));
}
static ap_uint<31> times4_27(ap_uint<4> v,ap_uint<27> m){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS LATENCY min=2 max=2
    ap_uint<31> a=(v[0]?ap_uint<31>(m):ap_uint<31>(0))+(v[1]?(ap_uint<31>(m)<<1):ap_uint<31>(0));
    ap_uint<31> b=(v[2]?(ap_uint<31>(m)<<2):ap_uint<31>(0))+(v[3]?(ap_uint<31>(m)<<3):ap_uint<31>(0));
    return a+b;
}
static int rq_fabric(ap_int<24> value,ap_uint<27> multiplier){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_uint<24> mag=value<0?ap_uint<24>(-value):ap_uint<24>(value);
    ap_uint<51> pieces[6];
#pragma HLS ARRAY_PARTITION variable=pieces complete
    for(int k=0;k<6;k++){
#pragma HLS UNROLL
        pieces[k]=ap_uint<51>(times4_27(mag.range(k*4+3,k*4),multiplier))<<(k*4);
    }
    ap_uint<51> a=pieces[0]+pieces[1],b=pieces[2]+pieces[3],c=pieces[4]+pieces[5];
    int64_t p=int64_t((a+b)+c);
    return int(rounded(value<0?-p:p,28));
}
typedef ap_int<18> pe_input;
typedef ap_int<40> pe_sum;
// Same 128 DSP multipliers execute convolution MACs and two 64-D distances.
static void dot128(const pe_input input[O][I],const pe_input weights[O][I],const pe_sum old[O],pe_sum out[O]){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
#pragma HLS ARRAY_PARTITION variable=input complete
#pragma HLS ARRAY_PARTITION variable=weights complete
#pragma HLS ARRAY_PARTITION variable=old complete
#pragma HLS ARRAY_PARTITION variable=out complete
    for(int o=0;o<O;o++){
#pragma HLS UNROLL
        ap_int<36> p[I];
#pragma HLS ARRAY_PARTITION variable=p complete
        for(int k=0;k<I;k++){
#pragma HLS UNROLL
            ap_int<36> product=input[o][k]*weights[o][k];
#pragma HLS BIND_OP variable=product op=mul impl=dsp
            p[k]=product;
        }
        pe_sum a=pe_sum(p[0])+p[1],b=pe_sum(p[2])+p[3],c=pe_sum(p[4])+p[5],d=pe_sum(p[6])+p[7];
        out[o]=old[o]+(a+b)+(c+d);
    }
}
static int rq_dsp(ap_int<24> value,ap_uint<27> multiplier){
#pragma HLS INLINE off
#pragma HLS PIPELINE II=1
    ap_int<52> product=value*multiplier;
#pragma HLS BIND_OP variable=product op=mul impl=dsp
    return int(rounded(int64_t(product),28));
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
static void burst_read_row(const pack_t *__restrict work,unsigned src,pack_t *__restrict line,unsigned dst,int width){
#pragma HLS INLINE off
    for(int x=0;x<width;x++){
#pragma HLS PIPELINE II=1
        line[dst+x]=work[src+x];
    }
}
static void load_line(const pack_t *work,unsigned src,shape_t ih,shape_t iw,shape_t ic,int k,int stride,int pad,int y,pack_t line[LD]){
    for(int cg=0;cg<(int(ic)+15)/16;cg++)for(int r=0;r<k;r++){
        int iy=(y<<(stride==2))+r-pad;
        unsigned dst=(cg*k+r)*int(iw);
        // Put the frame-boundary condition OUTSIDE the DDR transfer loop.
        if(iy>=0&&iy<ih)burst_read_row(work,src+(cg*int(ih)+iy)*int(iw),line,dst,int(iw));
        else for(int x=0;x<iw;x++){
#pragma HLS PIPELINE II=1
            line[dst+x]=0;
        }
    }
}
typedef ap_uint<512> sum_packet;
static void mac_row(shape_t ow,shape_t ic,shape_t iw,ap_uint<2> k,ap_uint<2> stride,ap_uint<1> pad,bool depth,ap_uint<2> row_head,
                    const uint64_t ram[O][RD],const pack_t line[LD],const pack_t dw_weight[9],bool nearest,const i16 query[64],int count,hls::stream<sum_packet>& output){
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=ram complete dim=1
#pragma HLS ARRAY_PARTITION variable=dw_weight complete
#pragma HLS ARRAY_PARTITION variable=query complete
#pragma HLS ALLOCATION function instances=dot128 limit=1
    i32 acc[O][32];
#pragma HLS ARRAY_PARTITION variable=acc complete dim=1
#pragma HLS BIND_STORAGE variable=acc type=ram_2p impl=bram
    int taps=nearest?(count+63)/64:(depth?int(k)*int(k):((int(ic)+7)/8)*int(k)*int(k));
    int span=(!nearest&&depth)?DW_SPAN:32;
    int blocks=nearest?1:(depth?(int(ow)+DW_SPAN-1)/DW_SPAN:(int(ow)+31)/32);
    // One pipelined loop and ONE dot128 call site prevent HLS loop outlining
    // from silently duplicating the CNN and distance-search DSP arrays.
    for(int block=0;block<blocks;block++)for(int tap=0;tap<taps;tap++)for(int p=0;p<span;p++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=acc inter false
        int center_index=(tap*32+p)*2;
        int x=(!nearest&&depth)?block*DW_SPAN+p:block*32+p;
        ap_uint<4> xy=spatial_tap_xy(ap_uint<4>(tap));
        int ib=(depth||k==3)?0:tap;
        int r=k==3?unsigned(xy.range(3,2)):0,col=k==3?unsigned(xy.range(1,0)):0;
        int ix=(x<<(stride==2))+col-pad;
        pe_input input[O][I],weights[O][I];pe_sum previous[O],next[O];
        i32 old_dw[O],out_dw[O];
#pragma HLS ARRAY_PARTITION variable=input complete
#pragma HLS ARRAY_PARTITION variable=weights complete
#pragma HLS ARRAY_PARTITION variable=previous complete
#pragma HLS ARRAY_PARTITION variable=next complete
#pragma HLS ARRAY_PARTITION variable=old_dw complete
#pragma HLS ARRAY_PARTITION variable=out_dw complete
        int shifted_row=r+int(row_head);
        ap_uint<2> depth_row=(k==3&&shifted_row>=3)?shifted_row-3:shifted_row;
        pack_t a=(x<ow&&ix>=0&&ix<iw)?line[(depth?int(depth_row):((ib/2)*int(k)+r))*iw+ix]:pack_t(0);
        uint64_t v=uint64_t(a>>(64*(ib&1)));
        uint64_t centers[O][2];
#pragma HLS ARRAY_PARTITION variable=centers complete
        for(int bank=0;bank<O;bank++){
#pragma HLS UNROLL
            centers[bank][0]=nearest?(center_index<count?ram[bank][center_index]:uint64_t(0)):ram[bank][tap];
            centers[bank][1]=nearest&&center_index+1<count?ram[bank][center_index+1]:uint64_t(0);
        }
        for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
            i32 old=(nearest||tap==0)?i32(0):acc[lane][p];previous[lane]=old;old_dw[lane]=old;
            for(int j=0;j<I;j++){
#pragma HLS UNROLL
                int d=(lane%8)*8+j;
                i16 center=(centers[d%16][lane/8]>>((d/16)*16))&65535;
                pe_input difference=pe_input(query[d])-pe_input(center);
                input[lane][j]=nearest?difference:pe_input(i8((v>>(j*8))&255));
                weights[lane][j]=nearest?difference:pe_input(i8((centers[lane][0]>>(j*8))&255));
            }
        }
        if(depth&&!nearest)dw16(a,dw_weight[tap],old_dw,out_dw);
        else dot128(input,weights,previous,next);
        sum_packet packet=0;
        if(nearest){
            for(int c=0;c<2;c++){
#pragma HLS UNROLL
                pe_sum a0=next[c*8]+next[c*8+1],b0=next[c*8+2]+next[c*8+3];
                pe_sum c0=next[c*8+4]+next[c*8+5],d0=next[c*8+6]+next[c*8+7];
                uint64_t distance=uint64_t((a0+b0)+(c0+d0));
                packet.range(c*64+63,c*64)=center_index+c>=count?~uint64_t(0):distance;
            }
            output.write(packet);
        }else{
            for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                i32 out=depth?out_dw[lane]:i32(next[lane]);acc[lane][p]=out;
                packet.range(lane*32+31,lane*32)=out;
            }
            if(tap==taps-1&&x<ow)output.write(packet);
        }
    }
}
static void quant_row(pack_t *work,unsigned dst,shape_t ow,const int32_t bias[O],const uint32_t mul[O],int relu,int qmax,bool nearest,int count,uint64_t &best,hls::stream<sum_packet>& input){
#pragma HLS INLINE off
#pragma HLS ARRAY_PARTITION variable=bias complete
#pragma HLS ARRAY_PARTITION variable=mul complete
#pragma HLS ALLOCATION function instances=rq_dsp limit=4
    if(nearest){
        uint64_t minimum=~uint64_t(0);
        for(int n=0;n<((count+63)/64)*32;n++){
#pragma HLS PIPELINE II=1
            sum_packet v=input.read();uint64_t a=v.range(63,0),b=v.range(127,64);
            uint64_t d=a<b?a:b;if(d<minimum)minimum=d;
        }
        best=minimum;return;
    }
    pack_t row[224];
#pragma HLS BIND_STORAGE variable=row type=ram_2p impl=bram
    sum_packet values=0;pack_t packed=0;
    for(int group=0;group<int(ow)*4;group++){
#pragma HLS PIPELINE II=1
        int part=group&3;
        if(part==0)values=input.read();
        ap_uint<32> word=0;
        for(int j=0;j<4;j++){
#pragma HLS UNROLL
            int lane=part*4+j;i32 v=i32(values.range(lane*32+31,lane*32))+bias[lane];
            int q=j==3?rq_fabric(ap_int<24>(v),ap_uint<27>(mul[lane])):rq_dsp(ap_int<24>(v),ap_uint<27>(mul[lane]));
            word.range(j*8+7,j*8)=i8(clampi(q,relu?0:-127,relu==2?qmax:127));
        }
        packed.range(part*32+31,part*32)=word;
        if(part==3)row[group/4]=packed;
    }
    for(int x=0;x<ow;x++){
#pragma HLS PIPELINE II=1
        work[dst+x]=row[x];
    }
}
static void process_row(pack_t *work,unsigned dst,shape_t ow,shape_t ic,shape_t iw,ap_uint<2> k,ap_uint<2> stride,ap_uint<1> pad,bool depth,ap_uint<2> row_head,
                        const uint64_t ram[O][RD],const pack_t line[LD],const pack_t dw_weight[9],
                        const int32_t bias[O],const uint32_t mul[O],int relu,int qmax,bool nearest,const i16 query[64],int count,uint64_t &best){
#pragma HLS INLINE off
#pragma HLS DATAFLOW
#pragma HLS ARRAY_PARTITION variable=ram complete dim=1
#pragma HLS ARRAY_PARTITION variable=dw_weight complete
#pragma HLS ARRAY_PARTITION variable=bias complete
#pragma HLS ARRAY_PARTITION variable=mul complete
    hls::stream<sum_packet> sums;
#pragma HLS STREAM variable=sums depth=16
#pragma HLS BIND_STORAGE variable=sums type=fifo impl=srl
    mac_row(ow,ic,iw,k,stride,pad,depth,row_head,ram,line,dw_weight,nearest,query,count,sums);
    quant_row(work,dst,ow,bias,mul,relu,qmax,nearest,count,best,sums);
}
static void cache_pointwise_input(const pack_t *__restrict work,unsigned src,pack_t *__restrict cache,int groups,int ih,int iw,int ybase,int rows){
#pragma HLS INLINE off
    for(int cg=0;cg<groups;cg++)for(int i=0;i<rows*iw;i++){
#pragma HLS PIPELINE II=1
        cache[cg*rows*iw+i]=work[src+(cg*ih+ybase)*iw+i];
    }
}
static bool conv(const uint64_t *model,pack_t *work,const unsigned t[24],uint64_t ram[O][RD],pack_t line[LD],pack_t *__restrict cache,bool nearest,bool depth,const i16 query[64],int count,uint64_t &best){
#pragma HLS INLINE off
#pragma HLS ALLOCATION function instances=process_row limit=1
#pragma HLS ARRAY_PARTITION variable=query complete
    unsigned src=t[1],dst=t[2],wo=t[4],bo=t[5],mo=t[6];
    shape_t ih=t[7],iw=t[8],ic=t[9],oc=t[10];
    int k=t[11]&3,stride=t[12]&3,pad=t[13]&1,relu=t[14]&3,qmax=t[15]&127;
    if(!nearest&&!depth&&k==3&&ic>SPATIAL_3X3_IC_LIMIT)return false;
    if(!nearest&&k!=1&&k!=3)return false;
    if(!nearest&&stride!=1&&stride!=2)return false;
    shape_t oh=((int(ih)+2*pad-k)>>(stride==2))+1,ow=((int(iw)+2*pad-k)>>(stride==2))+1;
    int taps=((ic+7)/8)*k*k;
    if(!nearest&&((ic+15)/16*k*iw>LD||(!depth&&taps>RD)||oc%8||ic<1||oc<1||iw<1||ih<1))return false;
    bool cached=!nearest&&!depth&&k==1&&stride==1&&pad==0&&oc>16;
    int groups=(int(ic)+15)/16,rows_per_tile=nearest?1:int(oh);
    if(cached)rows_per_tile=clampi(8192/(groups*int(iw)),1,clampi(int(oh),1,16));
    // Reuse the projection RAM, which is not live until the CNN has finished.
    // Sixteen rows bound the tile and exercise multi-tile transfer in RTL tests.
    for(int ybase=0;ybase<(nearest?1:int(oh));ybase+=rows_per_tile){
        int active_rows=clampi((nearest?1:int(oh))-ybase,1,rows_per_tile);
        if(cached)cache_pointwise_input(work,src,cache,groups,int(ih),int(iw),ybase,active_rows);
    for(int ob=0;ob<(nearest?1:(int(oc)+15)/16);ob++){
        int32_t bias[O];uint32_t mul[O];
        pack_t dw_weight[9];
#pragma HLS ARRAY_PARTITION variable=dw_weight complete
#pragma HLS ARRAY_PARTITION variable=bias complete
#pragma HLS ARRAY_PARTITION variable=mul complete
        for(int lane=0;lane<O;lane++){
            bias[lane]=!nearest&&ob*16+lane<oc?int32_t(word32(model,bo+ob*16+lane)):0;
            mul[lane]=!nearest&&ob*16+lane<oc?word32(model,mo+ob*16+lane):0;
        }
        if(!nearest&&!depth){
            for(int tap=0;tap<taps;tap++)for(int lane=0;lane<O;lane++){
#pragma HLS PIPELINE II=1
                ram[lane][tap]=model[wo+(ob*taps+tap)*16+lane];
            }
        }else if(!nearest){
            for(int tap=0;tap<k*k;tap++){
#pragma HLS PIPELINE II=2
                dw_weight[tap]=pack_t(model[wo+(ob*k*k+tap)*2])|(pack_t(model[wo+(ob*k*k+tap)*2+1])<<64);
            }
        }
        ap_uint<2> row_head=0;
        // Batch cached 1x1 rows without enlarging any RAM or PE array.
        // Power-of-two batches use shifts, retaining the 32-slot MAC recurrence.
        // Bound both line RAM words and the existing 224-word quantization row.
        unsigned group_words=unsigned(groups)*unsigned(iw);
        for(int local_y=0;local_y<active_rows;){
            int y=ybase+local_y,available=active_rows-local_y;
            ap_uint<3> batch_shift=0;
            if(cached){
                if(available>=2 && iw<=112 && group_words<=LD/2)batch_shift=1;
                if(available>=4 && iw<=56 && group_words<=LD/4)batch_shift=2;
                if(available>=8 && iw<=28 && group_words<=LD/8)batch_shift=3;
                if(available>=16 && iw<=14 && group_words<=LD/16)batch_shift=4;
            }
            int row_batch=1<<batch_shift;
            shape_t packed_iw=iw<<batch_shift,packed_ow=ow<<batch_shift;
            if(cached){
                for(int cg=0;cg<groups;cg++)for(int x=0;x<packed_iw;x++){
#pragma HLS PIPELINE II=1
                    line[cg*int(packed_iw)+x]=cache[(cg*active_rows+local_y)*int(iw)+x];
                }
            }else if(!nearest&&depth){
                // A three-row circular buffer retains overlapping DW rows.
                // Stride 1 reads only one fresh row; stride 2 reads two.
                if(y>0&&k==3){int next=int(row_head)+stride;row_head=next>=3?next-3:next;}
                for(int r=0;r<k;r++)if(y==0||r>=k-stride){
                    int shifted=r+int(row_head),slot=k==3&&shifted>=3?shifted-3:shifted;
                    int iy=(y<<(stride==2))+r-pad;
                    if(iy>=0&&iy<ih)burst_read_row(work,src+(ob*int(ih)+iy)*int(iw),line,slot*int(iw),int(iw));
                    else for(int x=0;x<iw;x++){
#pragma HLS PIPELINE II=1
                        line[slot*int(iw)+x]=0;
                    }
                }
            }else if(!nearest)load_line(work,src,ih,iw,ic,k,stride,pad,y,line);
            process_row(work,dst+(ob*int(oh)+y)*int(ow),packed_ow,int(ic),int(packed_iw),k,stride,pad,depth,row_head,ram,line,dw_weight,bias,mul,relu,qmax,nearest,query,count,best);
            local_y+=row_batch;
        }
    }
    }
    return true;
}
static void add(pack_t *work,const unsigned t[24]){
    pack_t left[256],right[256],output[256];
#pragma HLS BIND_STORAGE variable=left type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=right type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=output type=ram_2p impl=bram
    for(unsigned base=0;base<t[7];base+=256){
        int count=t[7]-base<256?t[7]-base:256;
        for(int i=0;i<count;i++){
#pragma HLS PIPELINE II=1
            left[i]=work[t[1]+base+i];
        }
        for(int i=0;i<count;i++){
#pragma HLS PIPELINE II=1
            right[i]=work[t[3]+base+i];
        }
        // One stream across all packed words avoids restarting a16-iteration
        // pipeline for each word. Same two requantizers, RAMs and exact bytes.
        pack_t packed=0;
        for(unsigned step=0;step<unsigned(count)*16;step++){
#pragma HLS PIPELINE II=1
            unsigned word=step>>4,lane=step&15;
            pack_t a=left[word],b=right[word];
            int v=rq8(i8(a.range(lane*8+7,lane*8)),t[4])+rq8(i8(b.range(lane*8+7,lane*8)),t[5]);
            ap_uint<8> byte=ap_uint<8>(i8(clampi(v,-127,127)));
            packed=(packed>>8)|(pack_t(byte)<<120);
            if(lane==15)output[word]=packed;
        }
        for(int i=0;i<count;i++){
#pragma HLS PIPELINE II=1
            work[t[2]+base+i]=output[i];
        }
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
#pragma HLS INTERFACE m_axi port=work offset=slave bundle=workmem depth=16384 max_read_burst_length=64 max_write_burst_length=64
#pragma HLS INTERFACE m_axi port=rgb offset=slave bundle=inputmem depth=8192 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=result offset=slave bundle=outmem depth=8192 max_write_burst_length=64
#pragma HLS INTERFACE s_axilite port=return bundle=control
#pragma HLS INTERFACE s_axilite port=model bundle=control
#pragma HLS INTERFACE s_axilite port=work bundle=control
#pragma HLS INTERFACE s_axilite port=rgb bundle=control
#pragma HLS INTERFACE s_axilite port=result bundle=control
#pragma HLS INTERFACE s_axilite port=width bundle=control
#pragma HLS INTERFACE s_axilite port=height bundle=control
#pragma HLS ALLOCATION function instances=rq limit=1
#pragma HLS ALLOCATION function instances=rq8 limit=1
#pragma HLS ALLOCATION function instances=conv limit=1
#pragma HLS ALLOCATION function instances=dw16 limit=1
#pragma HLS ALLOCATION function instances=pooled limit=1
    uint64_t ram[O][RD];pack_t line[LD];uint32_t row0[1024],row1[1024];unsigned raw[3136],smooth[3136];
    pack_t feature_cache[4096],projection_cache[8192];int64_t projection_bias[64];
#pragma HLS BIND_STORAGE variable=feature_cache type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=projection_cache type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=projection_bias type=ram_1p impl=lutram
#pragma HLS ARRAY_PARTITION variable=ram complete dim=1
#pragma HLS BIND_STORAGE variable=ram type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=line type=ram_2p impl=bram
    static uint32_t completed_frames=0;
    // Keep the completion sequence readable throughout auto-restarted frames.
    for(int i=0;i<16;i++)if(i!=9)result[i]=0;
    result[0]=0x17000001;result[1]=1;
    unsigned h[32];for(int i=0;i<32;i++)h[i]=word32(model,i);
    shape_t side=h[3],grid=h[4],dim=h[5],ca=h[9],cb=h[10];ap_uint<11> count=h[6];
    if(h[0]!=0x17000001||!width||!height||width>1024||height>1024||side<8||side>224||grid!=side/8||dim!=64||count<1||count>1024||ca!=32||cb!=96||h[2]>96)return;
    int den=int(side)*2;ap_int<37> im[3];int64_t ib[3];for(int c=0;c<3;c++){im[c]=int64_t(model[h[17]+c]);ib[c]=int64_t(model[h[18]+c]);}
    ap_uint<32> input_x[224];
#pragma HLS BIND_STORAGE variable=input_x type=ram_1p impl=lutram
    // Geometry depends on the column, not the row: divide 224 times, not 50176.
    for(int x=0;x<side;x++){
        int xx=clampi((2*x+1)*int(width)-side,0,(int(width)-1)*den),x0=xx/den;
        int x1=x0+1<int(width)?x0+1:x0,fx=xx-x0*den;
        input_x[x]=uint32_t(x0)|(uint32_t(x1)<<10)|(uint32_t(fx)<<20);
    }
    for(int y=0;y<side;y++){
        int yy=clampi((2*y+1)*int(height)-side,0,(int(height)-1)*den),y0=yy/den,y1=y0+1<int(height)?y0+1:y0,fy=yy-y0*den;
        for(unsigned x=0;x<width;x++){
#pragma HLS PIPELINE II=1
            row0[x]=rgb[y0*width+x];
        }
        for(unsigned x=0;x<width;x++){
#pragma HLS PIPELINE II=1
            row1[x]=rgb[y1*width+x];
        }
        pack_t normalized=0;
        // One colour component/cycle; the pipeline spans consecutive pixels.
        // Reuse the CNN line BRAM as a normalized-row staging buffer.
        for(ap_uint<10> group=0;group<int(side)*3;group++){
#pragma HLS PIPELINE II=1
            int x=group/3,c=group%3;ap_uint<32> map=input_x[x];
            unsigned x0=uint32_t(map)&1023,x1=(uint32_t(map)>>10)&1023;int fx=(uint32_t(map)>>20)&511;
            int shift=16-8*c;
            int64_t a=(row0[x0]>>shift)&255,b=(row0[x1]>>shift)&255,c0=(row1[x0]>>shift)&255,d=(row1[x1]>>shift)&255;
            ap_uint<27> v=bilinear_u27(ap_uint<8>(a),ap_uint<8>(b),ap_uint<8>(c0),ap_uint<8>(d),ap_uint<9>(den),ap_uint<9>(fx),ap_uint<9>(fy));
            ap_int<64> product=normalize_fabric(v,im[c]);
            int q=clampi(int(rounded(int64_t(product)+ib[c],48)),-127,127);
            if(c==0)normalized=0;
            normalized.range(c*8+7,c*8)=i8(q);
            if(c==2)line[x]=normalized;
        }
        for(int x=0;x<side;x++){
#pragma HLS PIPELINE II=1
            work[y*side+x]=line[x];
        }
    }

    i16 query[64];uint64_t best=0;unsigned t[24];
#pragma HLS ARRAY_PARTITION variable=query complete
    for(int j=0;j<64;j++)query[j]=0;
    for(unsigned phase=0;phase<h[2]+unsigned(grid)*unsigned(grid);phase++){
        bool nearest=phase>=h[2];
        ap_uint<3> operation=0;
        if(phase==h[2]){
    // PCA coefficients occupy 128 words per bank; this storage is then reused
    // for the nominal codebook. Tensor buffers remain entirely in PL-owned DDR.
    ap_uint<22> layout=feature_layout(grid);
    int fa_words=unsigned(layout.range(10,0)),fb_words=unsigned(layout.range(21,11));
    // Exhaustive legal-header proof: max total=2744 < feature_cache[4096].
    for(int i=0;i<fa_words;i++){
#pragma HLS PIPELINE II=1
        feature_cache[i]=work[h[7]+i];
    }
    for(int i=0;i<fb_words;i++){
#pragma HLS PIPELINE II=1
        feature_cache[fa_words+i]=work[h[8]+i];
    }
    for(int i=0;i<64;i++){
#pragma HLS PIPELINE II=1
        projection_bias[i]=int64_t(model[h[12]+i]);
    }
    load_ram(model,h[11],128,ram);
    for(int y=0;y<grid;y++)for(int x=0;x<grid;x++){
        i8 feature[128];
#pragma HLS ARRAY_PARTITION variable=feature cyclic factor=16
        for(int cg=0;cg<2;cg++){
            i8 v[O];
#pragma HLS ARRAY_PARTITION variable=v complete
            pooled(feature_cache,0,grid,grid,cg,y,x,v);
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
            pooled(feature_cache,fa_words,grid/2,grid/2,cg,y0,x0,a);pooled(feature_cache,fa_words,grid/2,grid/2,cg,y0,x1,b);
            pooled(feature_cache,fa_words,grid/2,grid/2,cg,y1,x0,c);pooled(feature_cache,fa_words,grid/2,grid/2,cg,y1,x1,d);
            for(int lane=0;lane<O;lane++){
#pragma HLS UNROLL
                feature[32+cg*16+lane]=quarter(a[lane],b[lane],c[lane],d[lane],ap_uint<2>(fx),ap_uint<2>(fy));
            }
        }
        // Interleave 64 independent projection accumulators. Consecutive
        // updates to one sum are 64 iterations apart, allowing one long
        // pipeline instead of filling/draining a 16-step loop per output.
        // 128 signed8* signed16 terms fit signed32 for the entire domain.
        // Keep the original signed64 bias and rounding only at the end.
        i32 projection_sums[64];
#pragma HLS BIND_STORAGE variable=projection_sums type=ram_2p impl=bram
        for(int step=0;step<512;step++){
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=projection_sums inter false
            int o=step&63,k=(step>>6)*16;
            i32 delta=0;
            for(int lane=0;lane<16;lane++){
#pragma HLS UNROLL
                int j=k+lane,index=o*8+j/16;
                i16 w=(ram[j%16][index/4]>>((index%4)*16))&65535;
                ap_int<24> dsp_product=feature[j]*w;
#pragma HLS BIND_OP variable=dsp_product op=mul impl=dsp
                delta+=i32(dsp_product);
            }
            projection_sums[o]=(k==0?i32(0):projection_sums[o])+delta;
        }
        pack_t packed=0;
        for(int o=0;o<64;o++){
#pragma HLS PIPELINE II=1
            int64_t acc=projection_bias[o]+int64_t(projection_sums[o]);
            int v=clampi(int(rounded(acc,h[14])),-32767,32767);packed.range((o%8)*16+15,(o%8)*16)=i16(v);
            if(o%8==7)projection_cache[((y*grid+x)*8)+o/8]=packed;
        }
    }
    load_ram(model,h[13],1024,ram);
        }
        if(nearest){
            int q=phase-h[2];
            for(int j=0;j<24;j++)t[j]=0;
            for(int j=0;j<8;j++){
                pack_t packed=projection_cache[q*8+j];
                for(int l=0;l<8;l++)query[j*8+l]=packed.range(l*16+15,l*16);
            }
        }else{
            for(int i=0;i<24;i++)t[i]=word32(model,64+phase*24+i);
            operation=decode_operation(t[0]);
            if(operation[2])add(work,t);
        }
        if(nearest||operation[0]||operation[1]){
            if(!conv(model,work,t,ram,line,projection_cache,nearest,bool(operation[1]),query,int(count),best)){result[1]=2;return;}
        }else if(!operation[2]){result[1]=3;return;}
        if(nearest)raw[phase-h[2]]=root(best);else result[8]=phase+1;
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
        // Exact distributive rearrangement: cache vertical interpolation once
        // per grid column, then consume two cached values for each output pixel.
        // For score <2^20 and width/height <=1024, row fits 32 bits and the
        // final bilinear numerator fits 44 bits, with no intermediate rounding.
        ap_uint<32> vertical[64];
#pragma HLS BIND_STORAGE variable=vertical type=ram_2p impl=lutram
        for(int c=0;c<grid;c++){
#pragma HLS PIPELINE II=1
            vertical[c]=ap_uint<20>(smooth[y0*grid+c])*(yd-fy)+ap_uint<20>(smooth[y1*grid+c])*fy;
        }
        for(int x=0;x<ww;x++){
#pragma HLS PIPELINE II=1
            ap_uint<6> x0=mx[x],x1=x0+1<int(grid)?ap_uint<6>(x0+1):x0;
            ap_uint<12> fx=mf[x],dx=xd-fx;
            ap_uint<44> value=vertical[x0]*dx+vertical[x1]*fx;
            bool alarm=h[15]<(1u<<20)&&value>limit;result[16+int(grid)*int(grid)+y*int(ww)+x]=alarm;pixels+=alarm;
        }
    }
    result[1]=0;result[2]=peak>h[15];result[3]=peak;result[4]=h[15];result[5]=grid;result[6]=pixels;result[7]=width*height;
    result[9]=++completed_frames;
}
