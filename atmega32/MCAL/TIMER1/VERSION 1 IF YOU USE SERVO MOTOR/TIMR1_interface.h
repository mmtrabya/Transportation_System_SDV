/*
 * TIMR1_interface.h
 *
 * Created: 3/1/2024 1:54:58 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef TIMR1_INTERFACE_H_
#define TIMR1_INTERFACE_H_


void TIMR1_INITI (void);
void TIMR1_InputCapture (u8 Edge);
void TIMR1_Reading_Time (u16 Reading);
void TIMR1_A_INIT            (void);   
void TIMR1_A_SetCompareMatch (u16 CompareValue);
void TIMR1_A_SetFastPWM      (f32 Duty_Cycle , u16 Frequency);

void TIMR1_Start     (void); 
void TIMR1_Stop      (void); 

void TIMR1_B_INTI            (void);
void TIMR1_B_SetCompareMatch (u16 CompareValue);
void TIMR1_B_SetFastPWM      (f32 Duty_Cycle , u16 Frequency);

#endif /* TIMR1_INTERFACE_H_ */