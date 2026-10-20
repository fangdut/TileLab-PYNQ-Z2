// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2025.2 (64-bit)
// Tool Version Limit: 2025.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
/***************************** Include Files *********************************/
#include "xreference_frame.h"

/************************** Function Implementation *************************/
#ifndef __linux__
int XReference_frame_CfgInitialize(XReference_frame *InstancePtr, XReference_frame_Config *ConfigPtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(ConfigPtr != NULL);

    InstancePtr->Control_BaseAddress = ConfigPtr->Control_BaseAddress;
    InstancePtr->IsReady = XIL_COMPONENT_IS_READY;

    return XST_SUCCESS;
}
#endif

void XReference_frame_Start(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL) & 0x80;
    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL, Data | 0x01);
}

u32 XReference_frame_IsDone(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL);
    return (Data >> 1) & 0x1;
}

u32 XReference_frame_IsIdle(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL);
    return (Data >> 2) & 0x1;
}

u32 XReference_frame_IsReady(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL);
    // check ap_start to see if the pcore is ready for next input
    return !(Data & 0x1);
}

void XReference_frame_EnableAutoRestart(XReference_frame *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL, 0x80);
}

void XReference_frame_DisableAutoRestart(XReference_frame *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_AP_CTRL, 0);
}

void XReference_frame_Set_paired(XReference_frame *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_PAIRED_DATA, (u32)(Data));
    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_PAIRED_DATA + 4, (u32)(Data >> 32));
}

u64 XReference_frame_Get_paired(XReference_frame *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_PAIRED_DATA);
    Data += (u64)XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_PAIRED_DATA + 4) << 32;
    return Data;
}

void XReference_frame_Set_scores(XReference_frame *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_SCORES_DATA, (u32)(Data));
    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_SCORES_DATA + 4, (u32)(Data >> 32));
}

u64 XReference_frame_Get_scores(XReference_frame *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_SCORES_DATA);
    Data += (u64)XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_SCORES_DATA + 4) << 32;
    return Data;
}

void XReference_frame_Set_gain_r(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GAIN_R_DATA, Data);
}

u32 XReference_frame_Get_gain_r(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GAIN_R_DATA);
    return Data;
}

void XReference_frame_Set_gain_g(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GAIN_G_DATA, Data);
}

u32 XReference_frame_Get_gain_g(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GAIN_G_DATA);
    return Data;
}

void XReference_frame_Set_gain_b(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GAIN_B_DATA, Data);
}

u32 XReference_frame_Get_gain_b(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GAIN_B_DATA);
    return Data;
}

void XReference_frame_Set_offset_r(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_R_DATA, Data);
}

u32 XReference_frame_Get_offset_r(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_R_DATA);
    return Data;
}

void XReference_frame_Set_offset_g(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_G_DATA, Data);
}

u32 XReference_frame_Get_offset_g(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_G_DATA);
    return Data;
}

void XReference_frame_Set_offset_b(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_B_DATA, Data);
}

u32 XReference_frame_Get_offset_b(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_OFFSET_B_DATA);
    return Data;
}

void XReference_frame_Set_high_r(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_HIGH_R_DATA, Data);
}

u32 XReference_frame_Get_high_r(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_HIGH_R_DATA);
    return Data;
}

void XReference_frame_Set_low_r(XReference_frame *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_LOW_R_DATA, Data);
}

u32 XReference_frame_Get_low_r(XReference_frame *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_LOW_R_DATA);
    return Data;
}

void XReference_frame_InterruptGlobalEnable(XReference_frame *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GIE, 1);
}

void XReference_frame_InterruptGlobalDisable(XReference_frame *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_GIE, 0);
}

void XReference_frame_InterruptEnable(XReference_frame *InstancePtr, u32 Mask) {
    u32 Register;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Register =  XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_IER);
    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_IER, Register | Mask);
}

void XReference_frame_InterruptDisable(XReference_frame *InstancePtr, u32 Mask) {
    u32 Register;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Register =  XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_IER);
    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_IER, Register & (~Mask));
}

void XReference_frame_InterruptClear(XReference_frame *InstancePtr, u32 Mask) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XReference_frame_WriteReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_ISR, Mask);
}

u32 XReference_frame_InterruptGetEnabled(XReference_frame *InstancePtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    return XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_IER);
}

u32 XReference_frame_InterruptGetStatus(XReference_frame *InstancePtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    return XReference_frame_ReadReg(InstancePtr->Control_BaseAddress, XREFERENCE_FRAME_CONTROL_ADDR_ISR);
}

