"""Create an isolated ROI-before-CNN candidate from accepted HLS62.

No live design or accepted snapshot is overwritten. Profile words20:26 store
a fixed, calibrated pixel rectangle and required source dimensions; word26
is the opt-in magic. All-zero reserved words retain full-frame behavior.
"""
from pathlib import Path
import argparse,hashlib,json

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    base=root/'experimental/texture_v170/hls/frozen/v170_hls62.cpp'
    text=base.read_text(encoding='utf8')
    def replace(before,after):
        nonlocal text
        assert text.count(before)==1,before
        text=text.replace(before,after)
    replace('    int den=int(side)*2;ap_int<37> im[3];', '''    // Optional per-fixture input ROI. Crop happens here in PL, before CNN.
    // Reject incompatible geometry instead of silently clamping/inspecting
    // another part of the source. No image arithmetic is delegated to ARM.
    bool roi=h[26]==0x19600001u;
    bool reserved=h[20]||h[21]||h[22]||h[23]||h[24]||h[25]||h[26];
    if((reserved&&!roi)||(roi&&(!h[22]||!h[23]||h[24]!=width||h[25]!=height||h[20]>=width||h[21]>=height||h[22]>width-h[20]||h[23]>height-h[21]))){result[1]=4;return;}
    unsigned view_x=roi?h[20]:0,view_y=roi?h[21]:0;
    unsigned view_w=roi?h[22]:width,view_h=roi?h[23]:height;
    int den=int(side)*2;ap_int<37> im[3];''')
    replace('int xx=clampi((2*x+1)*int(width)-side,0,(int(width)-1)*den),x0=xx/den;',
            'int xx=clampi((2*x+1)*int(view_w)-side,0,(int(view_w)-1)*den),x0=xx/den;')
    replace('int x1=x0+1<int(width)?x0+1:x0,fx=xx-x0*den;',
            'int x1=x0+1<int(view_w)?x0+1:x0,fx=xx-x0*den;')
    replace('int yy=clampi((2*y+1)*int(height)-side,0,(int(height)-1)*den),y0=yy/den,y1=y0+1<int(height)?y0+1:y0,fy=yy-y0*den;',
            'int yy=clampi((2*y+1)*int(view_h)-side,0,(int(view_h)-1)*den),y0=yy/den,y1=y0+1<int(view_h)?y0+1:y0,fy=yy-y0*den;')
    replace('for(unsigned x=0;x<width;x++){\n#pragma HLS PIPELINE II=1\n            row0[x]=rgb[y0*width+x];',
            'for(unsigned x=0;x<view_w;x++){\n#pragma HLS PIPELINE II=1\n            row0[x]=rgb[(view_y+y0)*width+view_x+x];')
    replace('for(unsigned x=0;x<width;x++){\n#pragma HLS PIPELINE II=1\n            row1[x]=rgb[y1*width+x];',
            'for(unsigned x=0;x<view_w;x++){\n#pragma HLS PIPELINE II=1\n            row1[x]=rgb[(view_y+y1)*width+view_x+x];')
    replace('ap_uint<11> ww=width,hh=height;ap_uint<12> xd=ww*2,yd=hh*2;',
            'ap_uint<11> ww=width,hh=height,iw=view_w,ih=view_h;ap_uint<12> xd=iw*2,yd=ih*2;')
    replace('ap_uint<16> xx=clampi((2*x+1)*int(grid)-int(ww),0,(int(grid)-1)*2*int(ww));',
            'ap_uint<16> xx=clampi((2*(x-int(view_x))+1)*int(grid)-int(iw),0,(int(grid)-1)*2*int(iw));')
    replace('ap_uint<16> yy=clampi((2*y+1)*int(grid)-int(hh),0,(int(grid)-1)*2*int(hh));',
            'ap_uint<16> yy=clampi((2*(y-int(view_y))+1)*int(grid)-int(ih),0,(int(grid)-1)*2*int(ih));')
    replace('bool alarm=h[15]<(1u<<20)&&value>limit;',
            'bool inside=unsigned(x)>=view_x&&unsigned(x)-view_x<view_w&&unsigned(y)>=view_y&&unsigned(y)-view_y<view_h;\n            bool alarm=inside&&h[15]<(1u<<20)&&value>limit;')
    replace('    result[9]=++completed_frames;',
            '    if(roi){result[10]=view_x;result[11]=view_y;result[12]=view_w;result[13]=view_h;result[14]=width;result[15]=height;}\n    result[9]=++completed_frames;')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'texture_integer.cpp').write_text(text,encoding='utf8')
    proof=dict(base_source_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),candidate_source_sha256=hashlib.sha256((a.out/'texture_integer.cpp').read_bytes()).hexdigest(),
        scope='ISOLATED_INPUT_ROI_CANDIDATE_NOT_ACCEPTED',parameters='words20:x,21:y,22:w,23:h,24:source_w,25:source_h,26:0x19600001',
        full_frame_compatibility_requires_zero_reserved_words=True,roi_is_fixed_operator_calibration_not_automatic_localization=True)
    (a.out/'source_proof.json').write_text(json.dumps(proof,indent=2),encoding='utf8');print(json.dumps(proof))

if __name__=='__main__':main()
