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
// 0x10 : Data signal of paired
//        bit 31~0 - paired[31:0] (Read/Write)
// 0x14 : Data signal of paired
//        bit 31~0 - paired[63:32] (Read/Write)
// 0x18 : reserved
// 0x1c : Data signal of scores
//        bit 31~0 - scores[31:0] (Read/Write)
// 0x20 : Data signal of scores
//        bit 31~0 - scores[63:32] (Read/Write)
// 0x24 : reserved
// 0x28 : Data signal of gain_r
//        bit 31~0 - gain_r[31:0] (Read/Write)
// 0x2c : reserved
// 0x30 : Data signal of gain_g
//        bit 31~0 - gain_g[31:0] (Read/Write)
// 0x34 : reserved
// 0x38 : Data signal of gain_b
//        bit 31~0 - gain_b[31:0] (Read/Write)
// 0x3c : reserved
// 0x40 : Data signal of offset_r
//        bit 31~0 - offset_r[31:0] (Read/Write)
// 0x44 : reserved
// 0x48 : Data signal of offset_g
//        bit 31~0 - offset_g[31:0] (Read/Write)
// 0x4c : reserved
// 0x50 : Data signal of offset_b
//        bit 31~0 - offset_b[31:0] (Read/Write)
// 0x54 : reserved
// 0x58 : Data signal of high_r
//        bit 31~0 - high_r[31:0] (Read/Write)
// 0x5c : reserved
// 0x60 : Data signal of low_r
//        bit 31~0 - low_r[31:0] (Read/Write)
// 0x64 : reserved
// (SC = Self Clear, COR = Clear on Read, TOW = Toggle on Write, COH = Clear on Handshake)

#define XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL       0x00
#define XREFERENCE_FRAME_CONTROL_ADDR_GIE           0x04
#define XREFERENCE_FRAME_CONTROL_ADDR_IER           0x08
#define XREFERENCE_FRAME_CONTROL_ADDR_ISR           0x0c
#define XREFERENCE_FRAME_CONTROL_ADDR_PAIRED_DATA   0x10
#define XREFERENCE_FRAME_CONTROL_BITS_PAIRED_DATA   64
#define XREFERENCE_FRAME_CONTROL_ADDR_SCORES_DATA   0x1c
#define XREFERENCE_FRAME_CONTROL_BITS_SCORES_DATA   64
#define XREFERENCE_FRAME_CONTROL_ADDR_GAIN_R_DATA   0x28
#define XREFERENCE_FRAME_CONTROL_BITS_GAIN_R_DATA   32
#define XREFERENCE_FRAME_CONTROL_ADDR_GAIN_G_DATA   0x30
#define XREFERENCE_FRAME_CONTROL_BITS_GAIN_G_DATA   32
#define XREFERENCE_FRAME_CONTROL_ADDR_GAIN_B_DATA   0x38
#define XREFERENCE_FRAME_CONTROL_BITS_GAIN_B_DATA   32
#define XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_R_DATA 0x40
#define XREFERENCE_FRAME_CONTROL_BITS_OFFSET_R_DATA 32
#define XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_G_DATA 0x48
#define XREFERENCE_FRAME_CONTROL_BITS_OFFSET_G_DATA 32
#define XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_B_DATA 0x50
#define XREFERENCE_FRAME_CONTROL_BITS_OFFSET_B_DATA 32
#define XREFERENCE_FRAME_CONTROL_ADDR_HIGH_R_DATA   0x58
#define XREFERENCE_FRAME_CONTROL_BITS_HIGH_R_DATA   32
#define XREFERENCE_FRAME_CONTROL_ADDR_LOW_R_DATA    0x60
#define XREFERENCE_FRAME_CONTROL_BITS_LOW_R_DATA    32

