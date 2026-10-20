#include <ap_int.h>

// Each DDR word: reference RGB[23:0], tolerance[31:24], current RGB[55:32].
// Registration/matched-reference generation precedes this boundary. Current
// photometric normalization and every scored pixel are computed by this IP.
static ap_uint<8> co(ap_uint<24> p) {
    return (int(p.range(23,16))-int(p.range(7,0))+256)>>1;
}
static ap_uint<8> cg(ap_uint<24> p) {
    return (-int(p.range(23,16))+2*int(p.range(15,8))-int(p.range(7,0))+512)>>2;
}
static ap_uint<8> yy(ap_uint<24> p) {
    return (int(p.range(23,16))+2*int(p.range(15,8))+int(p.range(7,0))+2)>>2;
}
static int dist(int a,int b) {return a>b?a-b:b-a;}
static int maximum(int a,int b) {return a>b?a:b;}

void reference_frame(const ap_uint<64>* paired,ap_uint<32>* scores,
    unsigned gain_r,unsigned gain_g,unsigned gain_b,
    int offset_r,int offset_g,int offset_b,unsigned high,unsigned low) {
#pragma HLS INTERFACE m_axi port=paired offset=slave bundle=readmem depth=250000 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=scores offset=slave bundle=writemem depth=250000 max_write_burst_length=64
#pragma HLS INTERFACE s_axilite port=return bundle=control
#pragma HLS INTERFACE s_axilite port=paired bundle=control
#pragma HLS INTERFACE s_axilite port=scores bundle=control
#pragma HLS INTERFACE s_axilite port=gain_r bundle=control
#pragma HLS INTERFACE s_axilite port=gain_g bundle=control
#pragma HLS INTERFACE s_axilite port=gain_b bundle=control
#pragma HLS INTERFACE s_axilite port=offset_r bundle=control
#pragma HLS INTERFACE s_axilite port=offset_g bundle=control
#pragma HLS INTERFACE s_axilite port=offset_b bundle=control
#pragma HLS INTERFACE s_axilite port=high bundle=control
#pragma HLS INTERFACE s_axilite port=low bundle=control
    ap_uint<64> line[4][504];
    ap_uint<64> win[5][5];
#pragma HLS ARRAY_PARTITION variable=line complete dim=1
#pragma HLS BIND_STORAGE variable=line type=ram_2p impl=bram
#pragma HLS ARRAY_PARTITION variable=win complete dim=0
    // Replicated boundaries inspect all 250000 pixels; no cropped border.
    for(int y=0;y<504;y++) {
        for(int x=0;x<504;x++) {
#pragma HLS PIPELINE II=1
            int iy=y<2?0:y>501?499:y-2;
            int ix=x<2?0:x>501?499:x-2;
            ap_uint<64> v=paired[iy*500+ix];
            ap_uint<24> cur=v.range(55,32);
            const unsigned gains[3]={gain_b,gain_g,gain_r};
            const int offsets[3]={offset_b,offset_g,offset_r};
#pragma HLS ARRAY_PARTITION variable=gains complete
#pragma HLS ARRAY_PARTITION variable=offsets complete
            for(int c=0;c<3;c++) {
#pragma HLS UNROLL
                int n=((unsigned(cur.range(c*8+7,c*8))*gains[c]+128)>>8)+offsets[c];
                cur.range(c*8+7,c*8)=n<0?0:n>255?255:n;
            }
            v.range(55,32)=cur;
            ap_uint<64> col[5];
#pragma HLS ARRAY_PARTITION variable=col complete
            for(int r=0;r<4;r++) {
#pragma HLS UNROLL
                col[r]=line[r][x];
            }
            col[4]=v;
            for(int r=0;r<4;r++) {
#pragma HLS UNROLL
                line[r][x]=col[r+1];
            }
            for(int r=0;r<5;r++) {
#pragma HLS UNROLL
                for(int c=0;c<4;c++) {
#pragma HLS UNROLL
                    win[r][c]=win[r][c+1];
                }
                win[r][4]=col[r];
            }
            if(y>=4 && x>=4) {
                int rco=0,rcg=0,cco=0,ccg=0;
                int lco=255,hco=0,lcg=255,hcg=0;
                for(int r=0;r<5;r++) {
#pragma HLS UNROLL
                    for(int c=0;c<5;c++) {
#pragma HLS UNROLL
                        ap_uint<24> a=win[r][c].range(23,0);
                        int aco=co(a),acg=cg(a);
                        lco=aco<lco?aco:lco;hco=aco>hco?aco:hco;
                        lcg=acg<lcg?acg:lcg;hcg=acg>hcg?acg:hcg;
                        if(r>=1 && r<=3 && c>=1 && c<=3) {
                            ap_uint<24> b=win[r][c].range(55,32);
                            rco+=aco;rcg+=acg;cco+=int(co(b));ccg+=int(cg(b));
                        }
                    }
                }
                ap_uint<24> a=win[2][2].range(23,0),b=win[2][2].range(55,32);
                int score=dist(yy(a),yy(b));
                score=maximum(score,dist((rco+4)/9,(cco+4)/9));
                score=maximum(score,dist((rcg+4)/9,(ccg+4)/9));
                score=maximum(score,dist(co(a),co(b))-(hco-lco));
                score=maximum(score,dist(cg(a),cg(b))-(hcg-lcg));
                unsigned edge=win[2][2].range(31,24);
                ap_uint<32> result=score;
                result[8]=score>high+edge;
                result[9]=score>low+(edge>>1);
                scores[(y-4)*500+x-4]=result;
            }
        }
    }
}
