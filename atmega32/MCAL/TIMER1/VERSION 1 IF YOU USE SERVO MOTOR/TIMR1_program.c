/*
 * TIMR1_program.c
 *
 * Created: 3/1/2024 1:54:43 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#include "../../../STD_TYPES.h"
#include "../../../BIT_MATH.h"

#include "TIMR1_interface.h"
#include "../../../CFG/TIMR1_config.h"
#include "../../../REGS.h"

void TIMR1_INITI (void)
{
   CLR_BIT(TCCR1A,COM1A0);
   CLR_BIT(TCCR1A,COM1A1);
   CLR_BIT(TCCR1A,WGM10);
   CLR_BIT(TCCR1A,WGM11);

   CLR_BIT(TCCR1B,WGM12);
   CLR_BIT(TCCR1B,WGM13);

}

void TIMR1_InputCapture (u8 Edge)
{
  switch (Edge)
  {
  case TIMR1_RISING_EDGE :
                          SET_BIT(TCCR1B,ICES1);
    break;
  
  case TIMR1_FALLING_EDGE :
                          CLR_BIT(TCCR1B,ICES1);
    break;
  }

}

void TIMR1_Reading_Time (u16 Reading)
{
  Reading = ICR1L;
}

void TIMR1_A_INIT    (void)
{
  #if     TIMR1_Mode_A == TIMR1_Normal_Mode  

  #elif   TIMR1_Mode_A == TIMR1_CTC_Mode 

  #elif   TIMR1_Mode_A == TIMR1_PWM_Phase_Correct_Mode
  
  #elif   TIMR1_Mode_A == TIMR1_Fast_PWM_Mode
  
  CLR_BIT(TCCR1A,COM1A0);
  SET_BIT(TCCR1A,COM1A1);  

  CLR_BIT(TCCR1A,WGM10);
  SET_BIT(TCCR1A,WGM11);   
  SET_BIT(TCCR1B,WGM12);
  SET_BIT(TCCR1B,WGM13);

  #endif    
} 

void TIMR1_A_SetFastPWM  (f32 Duty_Cycle , u16 Frequency)
{

    if (Duty_Cycle<=100)
    { 
    ICR1L  = ((1000000UL/(Frequency*TickTime))-1);
    OCR1AL = ((((ICR1L+1)*Duty_Cycle)/100.0)-1); 
    }
    
}

void TIMR1_A_SetCompareMatch (u16 CompareValue)
{
 OCR1AL = CompareValue;  
}

void TIMR1_Start     (void)
{

CLR_BIT(TCCR1B,CS12); 
SET_BIT(TCCR1B,CS11);
SET_BIT(TCCR1B,CS10);   

} 

void TIMR1_Stop      (void)
{

CLR_BIT(TCCR1B,CS12); 
CLR_BIT(TCCR1B,CS11);
CLR_BIT(TCCR1B,CS10); 

}
