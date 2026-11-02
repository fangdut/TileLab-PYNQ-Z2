// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2025.2 (64-bit)
// Tool Version Limit: 2025.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
#ifndef __linux__

#include "xstatus.h"
#ifdef SDT
#include "xparameters.h"
#endif
#include "xtexture_integer.h"

extern XTexture_integer_Config XTexture_integer_ConfigTable[];

#ifdef SDT
XTexture_integer_Config *XTexture_integer_LookupConfig(UINTPTR BaseAddress) {
	XTexture_integer_Config *ConfigPtr = NULL;

	int Index;

	for (Index = (u32)0x0; XTexture_integer_ConfigTable[Index].Name != NULL; Index++) {
		if (!BaseAddress || XTexture_integer_ConfigTable[Index].Control_BaseAddress == BaseAddress) {
			ConfigPtr = &XTexture_integer_ConfigTable[Index];
			break;
		}
	}

	return ConfigPtr;
}

int XTexture_integer_Initialize(XTexture_integer *InstancePtr, UINTPTR BaseAddress) {
	XTexture_integer_Config *ConfigPtr;

	Xil_AssertNonvoid(InstancePtr != NULL);

	ConfigPtr = XTexture_integer_LookupConfig(BaseAddress);
	if (ConfigPtr == NULL) {
		InstancePtr->IsReady = 0;
		return (XST_DEVICE_NOT_FOUND);
	}

	return XTexture_integer_CfgInitialize(InstancePtr, ConfigPtr);
}
#else
XTexture_integer_Config *XTexture_integer_LookupConfig(u16 DeviceId) {
	XTexture_integer_Config *ConfigPtr = NULL;

	int Index;

	for (Index = 0; Index < XPAR_XTEXTURE_INTEGER_NUM_INSTANCES; Index++) {
		if (XTexture_integer_ConfigTable[Index].DeviceId == DeviceId) {
			ConfigPtr = &XTexture_integer_ConfigTable[Index];
			break;
		}
	}

	return ConfigPtr;
}

int XTexture_integer_Initialize(XTexture_integer *InstancePtr, u16 DeviceId) {
	XTexture_integer_Config *ConfigPtr;

	Xil_AssertNonvoid(InstancePtr != NULL);

	ConfigPtr = XTexture_integer_LookupConfig(DeviceId);
	if (ConfigPtr == NULL) {
		InstancePtr->IsReady = 0;
		return (XST_DEVICE_NOT_FOUND);
	}

	return XTexture_integer_CfgInitialize(InstancePtr, ConfigPtr);
}
#endif

#endif

