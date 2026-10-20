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
#include "xreference_frame.h"

extern XReference_frame_Config XReference_frame_ConfigTable[];

#ifdef SDT
XReference_frame_Config *XReference_frame_LookupConfig(UINTPTR BaseAddress) {
	XReference_frame_Config *ConfigPtr = NULL;

	int Index;

	for (Index = (u32)0x0; XReference_frame_ConfigTable[Index].Name != NULL; Index++) {
		if (!BaseAddress || XReference_frame_ConfigTable[Index].Control_BaseAddress == BaseAddress) {
			ConfigPtr = &XReference_frame_ConfigTable[Index];
			break;
		}
	}

	return ConfigPtr;
}

int XReference_frame_Initialize(XReference_frame *InstancePtr, UINTPTR BaseAddress) {
	XReference_frame_Config *ConfigPtr;

	Xil_AssertNonvoid(InstancePtr != NULL);

	ConfigPtr = XReference_frame_LookupConfig(BaseAddress);
	if (ConfigPtr == NULL) {
		InstancePtr->IsReady = 0;
		return (XST_DEVICE_NOT_FOUND);
	}

	return XReference_frame_CfgInitialize(InstancePtr, ConfigPtr);
}
#else
XReference_frame_Config *XReference_frame_LookupConfig(u16 DeviceId) {
	XReference_frame_Config *ConfigPtr = NULL;

	int Index;

	for (Index = 0; Index < XPAR_XREFERENCE_FRAME_NUM_INSTANCES; Index++) {
		if (XReference_frame_ConfigTable[Index].DeviceId == DeviceId) {
			ConfigPtr = &XReference_frame_ConfigTable[Index];
			break;
		}
	}

	return ConfigPtr;
}

int XReference_frame_Initialize(XReference_frame *InstancePtr, u16 DeviceId) {
	XReference_frame_Config *ConfigPtr;

	Xil_AssertNonvoid(InstancePtr != NULL);

	ConfigPtr = XReference_frame_LookupConfig(DeviceId);
	if (ConfigPtr == NULL) {
		InstancePtr->IsReady = 0;
		return (XST_DEVICE_NOT_FOUND);
	}

	return XReference_frame_CfgInitialize(InstancePtr, ConfigPtr);
}
#endif

#endif

