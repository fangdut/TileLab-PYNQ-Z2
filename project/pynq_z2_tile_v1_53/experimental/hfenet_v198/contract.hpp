// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
static const unsigned HFE_MAGIC=0x19800001u;
static const unsigned HEADER_WORDS=64,TENSOR_WORDS=16,OP_WORDS=32;
static const unsigned MAX_MODEL_BYTES=2097152,MAX_WORK_BYTES=134217728;
enum {CONV=2,NORM=3,RELU=4,POOL=5,UP=6,ADD=7,CAT=8,MASK=9,PREWITT=10};
// Tensor fields: offset(int16 elements),C,H,W,exp kind,scalar exp,
// optional exp table,element count,last-use; remaining fields reserved0.
// Op fields: kind,src0,src1,dst,params(word32),weights(int16),KH,KW,DY,DX,
// PY,PX,Cin,Cout,groups,terms,OCweight stride16,input exp,output exp,
// shift0,shift1,shift2,paramwordcount. Remaining fields reserved0.
