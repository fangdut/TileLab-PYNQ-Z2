// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2025.2 (64-bit)
// Tool Version Limit: 2025.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
#ifndef XREFERENCE_FRAME_H
#define XREFERENCE_FRAME_H

#ifdef __cplusplus
extern "C" {
#endif

/***************************** Include Files *********************************/
#ifndef __linux__
#include "xil_types.h"
#include "xil_assert.h"
#include "xstatus.h"
#include "xil_io.h"
#else
#include <stdint.h>
#include <assert.h>
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stddef.h>
#endif
#include "xreference_frame_hw.h"

/**************************** Type Definitions ******************************/
#ifdef __linux__
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
#else
typedef struct {
#ifdef SDT
    char *Name;
#else
    u16 DeviceId;
#endif
    u64 Control_BaseAddress;
} XReference_frame_Config;
#endif

typedef struct {
    u64 Control_BaseAddress;
    u32 IsReady;
} XReference_frame;

typedef u32 word_type;

/***************** Macros (Inline Functions) Definitions *********************/
#ifndef __linux__
#define XReference_frame_WriteReg(BaseAddress, RegOffset, Data) \
    Xil_Out32((BaseAddress) + (RegOffset), (u32)(Data))
#define XReference_frame_ReadReg(BaseAddress, RegOffset) \
    Xil_In32((BaseAddress) + (RegOffset))
#else
#define XReference_frame_WriteReg(BaseAddress, RegOffset, Data) \
    *(volatile u32*)((BaseAddress) + (RegOffset)) = (u32)(Data)
#define XReference_frame_ReadReg(BaseAddress, RegOffset) \
    *(volatile u32*)((BaseAddress) + (RegOffset))

#define Xil_AssertVoid(expr)    assert(expr)
#define Xil_AssertNonvoid(expr) assert(expr)

#define XST_SUCCESS             0
#define XST_DEVICE_NOT_FOUND    2
#define XST_OPEN_DEVICE_FAILED  3
#define XIL_COMPONENT_IS_READY  1
#endif

/************************** Function Prototypes *****************************/
#ifndef __linux__
#ifdef SDT
int XReference_frame_Initialize(XReference_frame *InstancePtr, UINTPTR BaseAddress);
XReference_frame_Config* XReference_frame_LookupConfig(UINTPTR BaseAddress);
#else
int XReference_frame_Initialize(XReference_frame *InstancePtr, u16 DeviceId);
XReference_frame_Config* XReference_frame_LookupConfig(u16 DeviceId);
#endif
int XReference_frame_CfgInitialize(XReference_frame *InstancePtr, XReference_frame_Config *ConfigPtr);
#else
int XReference_frame_Initialize(XReference_frame *InstancePtr, const char* InstanceName);
int XReference_frame_Release(XReference_frame *InstancePtr);
#endif

void XReference_frame_Start(XReference_frame *InstancePtr);
u32 XReference_frame_IsDone(XReference_frame *InstancePtr);
u32 XReference_frame_IsIdle(XReference_frame *InstancePtr);
u32 XReference_frame_IsReady(XReference_frame *InstancePtr);
void XReference_frame_EnableAutoRestart(XReference_frame *InstancePtr);
void XReference_frame_DisableAutoRestart(XReference_frame *InstancePtr);

void XReference_frame_Set_paired(XReference_frame *InstancePtr, u64 Data);
u64 XReference_frame_Get_paired(XReference_frame *InstancePtr);
void XReference_frame_Set_scores(XReference_frame *InstancePtr, u64 Data);
u64 XReference_frame_Get_scores(XReference_frame *InstancePtr);
void XReference_frame_Set_gain_r(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_gain_r(XReference_frame *InstancePtr);
void XReference_frame_Set_gain_g(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_gain_g(XReference_frame *InstancePtr);
void XReference_frame_Set_gain_b(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_gain_b(XReference_frame *InstancePtr);
void XReference_frame_Set_offset_r(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_offset_r(XReference_frame *InstancePtr);
void XReference_frame_Set_offset_g(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_offset_g(XReference_frame *InstancePtr);
void XReference_frame_Set_offset_b(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_offset_b(XReference_frame *InstancePtr);
void XReference_frame_Set_high_r(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_high_r(XReference_frame *InstancePtr);
void XReference_frame_Set_low_r(XReference_frame *InstancePtr, u32 Data);
u32 XReference_frame_Get_low_r(XReference_frame *InstancePtr);

void XReference_frame_InterruptGlobalEnable(XReference_frame *InstancePtr);
void XReference_frame_InterruptGlobalDisable(XReference_frame *InstancePtr);
void XReference_frame_InterruptEnable(XReference_frame *InstancePtr, u32 Mask);
void XReference_frame_InterruptDisable(XReference_frame *InstancePtr, u32 Mask);
void XReference_frame_InterruptClear(XReference_frame *InstancePtr, u32 Mask);
u32 XReference_frame_InterruptGetEnabled(XReference_frame *InstancePtr);
u32 XReference_frame_InterruptGetStatus(XReference_frame *InstancePtr);

#ifdef __cplusplus
}
#endif

#endif
