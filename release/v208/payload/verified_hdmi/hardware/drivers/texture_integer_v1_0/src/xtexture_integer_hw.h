// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2025.2 (64-bit)
// Tool Version Limit: 2025.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
// control
// 0x00 : Control signals
//        bit 0  - ap_start (Read/Write/COH)
//        bit 1  - ap_done (Read/COR)
//        bit 2  - ap_idle (Read)
//        bit 3  - ap_ready (Read/COR)
//        bit 7  - auto_restart (Read/Write)
//        bit 9  - interrupt (Read)
//        others - reserved
// 0x04 : Global Interrupt Enable Register
//        bit 0  - Global Interrupt Enable (Read/Write)
//        others - reserved
// 0x08 : IP Interrupt Enable Register (Read/Write)
//        bit 0 - enable ap_done interrupt (Read/Write)
//        bit 1 - enable ap_ready interrupt (Read/Write)
//        others - reserved
// 0x0c : IP Interrupt Status Register (Read/TOW)
//        bit 0 - ap_done (Read/TOW)
//        bit 1 - ap_ready (Read/TOW)
//        others - reserved
// 0x10 : Data signal of model
//        bit 31~0 - model[31:0] (Read/Write)
// 0x14 : Data signal of model
//        bit 31~0 - model[63:32] (Read/Write)
// 0x18 : reserved
// 0x1c : Data signal of work
//        bit 31~0 - work[31:0] (Read/Write)
// 0x20 : Data signal of work
//        bit 31~0 - work[63:32] (Read/Write)
// 0x24 : reserved
// 0x28 : Data signal of rgb
//        bit 31~0 - rgb[31:0] (Read/Write)
// 0x2c : Data signal of rgb
//        bit 31~0 - rgb[63:32] (Read/Write)
// 0x30 : reserved
// 0x34 : Data signal of result
//        bit 31~0 - result[31:0] (Read/Write)
// 0x38 : Data signal of result
//        bit 31~0 - result[63:32] (Read/Write)
// 0x3c : reserved
// 0x40 : Data signal of width
//        bit 31~0 - width[31:0] (Read/Write)
// 0x44 : reserved
// 0x48 : Data signal of height
//        bit 31~0 - height[31:0] (Read/Write)
// 0x4c : reserved
// (SC = Self Clear, COR = Clear on Read, TOW = Toggle on Write, COH = Clear on Handshake)

#define XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL     0x00
#define XTEXTURE_INTEGER_CONTROL_ADDR_GIE         0x04
#define XTEXTURE_INTEGER_CONTROL_ADDR_IER         0x08
#define XTEXTURE_INTEGER_CONTROL_ADDR_ISR         0x0c
#define XTEXTURE_INTEGER_CONTROL_ADDR_MODEL_DATA  0x10
#define XTEXTURE_INTEGER_CONTROL_BITS_MODEL_DATA  64
#define XTEXTURE_INTEGER_CONTROL_ADDR_WORK_DATA   0x1c
#define XTEXTURE_INTEGER_CONTROL_BITS_WORK_DATA   64
#define XTEXTURE_INTEGER_CONTROL_ADDR_RGB_DATA    0x28
#define XTEXTURE_INTEGER_CONTROL_BITS_RGB_DATA    64
#define XTEXTURE_INTEGER_CONTROL_ADDR_RESULT_DATA 0x34
#define XTEXTURE_INTEGER_CONTROL_BITS_RESULT_DATA 64
#define XTEXTURE_INTEGER_CONTROL_ADDR_WIDTH_DATA  0x40
#define XTEXTURE_INTEGER_CONTROL_BITS_WIDTH_DATA  32
#define XTEXTURE_INTEGER_CONTROL_ADDR_HEIGHT_DATA 0x48
#define XTEXTURE_INTEGER_CONTROL_BITS_HEIGHT_DATA 32

