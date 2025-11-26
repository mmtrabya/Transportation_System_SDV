/*
 * TIMR0_interface.h
 *
 * Created: 2/16/2024 3:03:18 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef TIMR0_INTERFACE_H_
#define TIMR0_INTERFACE_H_

#include"../../STD_TYPES.h"

void TIMR0_INTI  (void);
void TIMR0_Start (void);
void TIMR0_Stop  (void);
void TIMR0_SetCompareMatch (u8 CompareValue);
void TIMR0_MS_Delay (u16 Ms_Delay);
void TIMR0_CallBackOVF(void(*PtrToFun)(void));
void TIMR0_CallBackCTC(void(*PtrToFun)(void));
void TIMR0_DutyCycle (u8 Duty_Cycle);


#endif /* TIMR0_INTERFACE_H_ */