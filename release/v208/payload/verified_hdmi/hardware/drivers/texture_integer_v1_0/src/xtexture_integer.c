// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2025.2 (64-bit)
// Tool Version Limit: 2025.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
/***************************** Include Files *********************************/
#include "xtexture_integer.h"

/************************** Function Implementation *************************/
#ifndef __linux__
int XTexture_integer_CfgInitialize(XTexture_integer *InstancePtr, XTexture_integer_Config *ConfigPtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(ConfigPtr != NULL);

    InstancePtr->Control_BaseAddress = ConfigPtr->Control_BaseAddress;
    InstancePtr->IsReady = XIL_COMPONENT_IS_READY;

    return XST_SUCCESS;
}
#endif

void XTexture_integer_Start(XTexture_integer *InstancePtr) {
    u32 Data;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL) & 0x80;
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL, Data | 0x01);
}

u32 XTexture_integer_IsDone(XTexture_integer *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL);
    return (Data >> 1) & 0x1;
}

u32 XTexture_integer_IsIdle(XTexture_integer *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL);
    return (Data >> 2) & 0x1;
}

u32 XTexture_integer_IsReady(XTexture_integer *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL);
    // check ap_start to see if the pcore is ready for next input
    return !(Data & 0x1);
}

void XTexture_integer_EnableAutoRestart(XTexture_integer *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL, 0x80);
}

void XTexture_integer_DisableAutoRestart(XTexture_integer *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_AP_CTRL, 0);
}

void XTexture_integer_Set_model(XTexture_integer *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_MODEL_DATA, (u32)(Data));
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_MODEL_DATA + 4, (u32)(Data >> 32));
}

u64 XTexture_integer_Get_model(XTexture_integer *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_MODEL_DATA);
    Data += (u64)XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_MODEL_DATA + 4) << 32;
    return Data;
}

void XTexture_integer_Set_work(XTexture_integer *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_WORK_DATA, (u32)(Data));
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_WORK_DATA + 4, (u32)(Data >> 32));
}

u64 XTexture_integer_Get_work(XTexture_integer *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_WORK_DATA);
    Data += (u64)XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_WORK_DATA + 4) << 32;
    return Data;
}

void XTexture_integer_Set_rgb(XTexture_integer *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RGB_DATA, (u32)(Data));
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RGB_DATA + 4, (u32)(Data >> 32));
}

u64 XTexture_integer_Get_rgb(XTexture_integer *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RGB_DATA);
    Data += (u64)XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RGB_DATA + 4) << 32;
    return Data;
}

void XTexture_integer_Set_result(XTexture_integer *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RESULT_DATA, (u32)(Data));
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RESULT_DATA + 4, (u32)(Data >> 32));
}

u64 XTexture_integer_Get_result(XTexture_integer *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RESULT_DATA);
    Data += (u64)XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_RESULT_DATA + 4) << 32;
    return Data;
}

void XTexture_integer_Set_width(XTexture_integer *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_WIDTH_DATA, Data);
}

u32 XTexture_integer_Get_width(XTexture_integer *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_WIDTH_DATA);
    return Data;
}

void XTexture_integer_Set_height(XTexture_integer *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_HEIGHT_DATA, Data);
}

u32 XTexture_integer_Get_height(XTexture_integer *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_HEIGHT_DATA);
    return Data;
}

void XTexture_integer_InterruptGlobalEnable(XTexture_integer *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_GIE, 1);
}

void XTexture_integer_InterruptGlobalDisable(XTexture_integer *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_GIE, 0);
}

void XTexture_integer_InterruptEnable(XTexture_integer *InstancePtr, u32 Mask) {
    u32 Register;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Register =  XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_IER);
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_IER, Register | Mask);
}

void XTexture_integer_InterruptDisable(XTexture_integer *InstancePtr, u32 Mask) {
    u32 Register;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Register =  XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_IER);
    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_IER, Register & (~Mask));
}

void XTexture_integer_InterruptClear(XTexture_integer *InstancePtr, u32 Mask) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XTexture_integer_WriteReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_ISR, Mask);
}

u32 XTexture_integer_InterruptGetEnabled(XTexture_integer *InstancePtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    return XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_IER);
}

u32 XTexture_integer_InterruptGetStatus(XTexture_integer *InstancePtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    return XTexture_integer_ReadReg(InstancePtr->Control_BaseAddress, XTEXTURE_INTEGER_CONTROL_ADDR_ISR);
}

