// SPDX-License-Identifier: MIT
// Experimental grayscale-author-mode preprocessing; NOT the complete detector.
#include <stdint.h>
static unsigned level(unsigned numerator,unsigned denominator){
#pragma HLS INLINE off
    unsigned q=0,rem=numerator;
    for(int bit=7;bit>=0;bit--){
#pragma HLS PIPELINE II=1
        unsigned trial=denominator<<bit;
        if(rem>=trial){rem-=trial;q|=1u<<bit;}
    }
    unsigned twice=rem<<1;
    if(twice>denominator||(twice==denominator&&(q&1)))q++;
    return q;
}
unsigned preprocess_integer(const uint32_t *rgb,uint32_t *channels,
                            unsigned width,unsigned height){
#pragma HLS INTERFACE m_axi port=rgb offset=slave bundle=inputmem depth=360448 max_read_burst_length=64
#pragma HLS INTERFACE m_axi port=channels offset=slave bundle=outputmem depth=360448 max_write_burst_length=64
#pragma HLS INTERFACE s_axilite port=rgb bundle=control
#pragma HLS INTERFACE s_axilite port=channels bundle=control
#pragma HLS INTERFACE s_axilite port=width bundle=control
#pragma HLS INTERFACE s_axilite port=height bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    if(!width||width>1024||!height||height>2048)return 4;
    unsigned n=width*height;if(n>360448)return 4;
    uint32_t hist[256];uint8_t lut[256];
#pragma HLS BIND_STORAGE variable=hist type=ram_t2p impl=bram
    for(unsigned i=0;i<256;i++)hist[i]=0;
    for(unsigned i=0;i<n;i++){
#pragma HLS PIPELINE II=2
        uint32_t pixel=rgb[i];unsigned r=(pixel>>16)&255,g=(pixel>>8)&255,b=pixel&255;
        // This frozen author-data mode accepts grayscale originals only.
        // Never silently treat an unvalidated color conversion as qualified.
        if(r!=g||g!=b)return 5;
        hist[r]++;
    }
    unsigned first=0;bool found=false;
    for(unsigned i=0;i<256;i++)if(!found&&hist[i]){first=i;found=true;}
    unsigned denominator=n-hist[first],cumulative=0;
    for(unsigned i=0;i<256;i++){
        cumulative+=hist[i];unsigned value=0;
        if(!denominator)value=first;
        else if(i>=first){unsigned delta=cumulative-hist[first];value=level((delta<<8)-delta,denominator);}
        lut[i]=uint8_t(value);
    }
    for(unsigned i=0;i<n;i++){
#pragma HLS PIPELINE II=1
        unsigned gray=(rgb[i]>>16)&255,equalized=lut[gray],added=gray+equalized;
        if(added>255)added=255;
        // R=original, G=equalized, B=saturated sum, matching author channel order.
        channels[i]=(gray<<16)|(equalized<<8)|added;
    }
    return 0;
}
