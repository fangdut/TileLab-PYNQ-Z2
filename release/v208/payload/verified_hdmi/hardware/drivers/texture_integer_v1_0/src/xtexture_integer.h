// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2025.2 (64-bit)
// Tool Version Limit: 2025.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
#ifndef XTEXTURE_INTEGER_H
#define XTEXTURE_INTEGER_H

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
#include "xtexture_integer_hw.h"

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
} XTexture_integer_Config;
#endif

typedef struct {
    u64 Control_BaseAddress;
    u32 IsReady;
} XTexture_integer;

typedef u32 word_type;

/***************** Macros (Inline Functions) Definitions *********************/
#ifndef __linux__
#define XTexture_integer_WriteReg(BaseAddress, RegOffset, Data) \
    Xil_Out32((BaseAddress) + (RegOffset), (u32)(Data))
#define XTexture_integer_ReadReg(BaseAddress, RegOffset) \
    Xil_In32((BaseAddress) + (RegOffset))
#else
#define XTexture_integer_WriteReg(BaseAddress, RegOffset, Data) \
    *(volatile u32*)((BaseAddress) + (RegOffset)) = (u32)(Data)
#define XTexture_integer_ReadReg(BaseAddress, RegOffset) \
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
int XTexture_integer_Initialize(XTexture_integer *InstancePtr, UINTPTR BaseAddress);
XTexture_integer_Config* XTexture_integer_LookupConfig(UINTPTR BaseAddress);
#else
int XTexture_integer_Initialize(XTexture_integer *InstancePtr, u16 DeviceId);
XTexture_integer_Config* XTexture_integer_LookupConfig(u16 DeviceId);
#endif
int XTexture_integer_CfgInitialize(XTexture_integer *InstancePtr, XTexture_integer_Config *ConfigPtr);
#else
int XTexture_integer_Initialize(XTexture_integer *InstancePtr, const char* InstanceName);
int XTexture_integer_Release(XTexture_integer *InstancePtr);
#endif

void XTexture_integer_Start(XTexture_integer *InstancePtr);
u32 XTexture_integer_IsDone(XTexture_integer *InstancePtr);
u32 XTexture_integer_IsIdle(XTexture_integer *InstancePtr);
u32 XTexture_integer_IsReady(XTexture_integer *InstancePtr);
void XTexture_integer_EnableAutoRestart(XTexture_integer *InstancePtr);
void XTexture_integer_DisableAutoRestart(XTexture_integer *InstancePtr);

void XTexture_integer_Set_model(XTexture_integer *InstancePtr, u64 Data);
u64 XTexture_integer_Get_model(XTexture_integer *InstancePtr);
void XTexture_integer_Set_work(XTexture_integer *InstancePtr, u64 Data);
u64 XTexture_integer_Get_work(XTexture_integer *InstancePtr);
void XTexture_integer_Set_rgb(XTexture_integer *InstancePtr, u64 Data);
u64 XTexture_integer_Get_rgb(XTexture_integer *InstancePtr);
void XTexture_integer_Set_result(XTexture_integer *InstancePtr, u64 Data);
u64 XTexture_integer_Get_result(XTexture_integer *InstancePtr);
void XTexture_integer_Set_width(XTexture_integer *InstancePtr, u32 Data);
u32 XTexture_integer_Get_width(XTexture_integer *InstancePtr);
void XTexture_integer_Set_height(XTexture_integer *InstancePtr, u32 Data);
u32 XTexture_integer_Get_height(XTexture_integer *InstancePtr);

void XTexture_integer_InterruptGlobalEnable(XTexture_integer *InstancePtr);
void XTexture_integer_InterruptGlobalDisable(XTexture_integer *InstancePtr);
void XTexture_integer_InterruptEnable(XTexture_integer *InstancePtr, u32 Mask);
void XTexture_integer_InterruptDisable(XTexture_integer *InstancePtr, u32 Mask);
void XTexture_integer_InterruptClear(XTexture_integer *InstancePtr, u32 Mask);
u32 XTexture_integer_InterruptGetEnabled(XTexture_integer *InstancePtr);
u32 XTexture_integer_InterruptGetStatus(XTexture_integer *InstancePtr);

#ifdef __cplusplus
}
#endif

#endif
