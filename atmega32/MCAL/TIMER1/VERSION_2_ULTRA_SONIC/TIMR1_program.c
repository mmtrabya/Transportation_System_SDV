/*
 * TIMR1_program.c
 *
 * Created: 4/22/2024 4:12:42 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#include "../../../STD_TYPES.h"
#include "../../../BIT_MATH.h"

#include "TIMR1_interface.h"
#include "../../../REGS.h"
#include "../../../CFG/TIMR1_config.h"


void TIMR1_INITI (void)
{
   // Clear Compare Output Mode bits (Disable OC1A and OC1B pins)
   CLR_BIT(TCCR1A,COM1A0);
   CLR_BIT(TCCR1A,COM1A1);
   CLR_BIT(TCCR1A,COM1B0);
   CLR_BIT(TCCR1A,COM1B1);

   // Set Waveform Generation Mode to Normal (Mode 0)
   CLR_BIT(TCCR1A,WGM10);
   CLR_BIT(TCCR1A,WGM11);
   CLR_BIT(TCCR1B,WGM12);
   CLR_BIT(TCCR1B,WGM13);   
}

void TIMR1_Input_Capture (u8 Edge)
{
  // Enable Input Capture Noise Canceler
  SET_BIT(TCCR1B,ICNC1);
  
  switch (Edge)
  {
  case  TIMR1_RISING_EDGE  :
                            // Capture on rising edge
                            SET_BIT(TCCR1B,ICES1);
  break;
  
  case  TIMR1_FALLING_EDGE :
                            // Capture on falling edge
                            CLR_BIT(TCCR1B,ICES1);
  break;
  }  
}

void TIMR1_Start (void)
{
    // Set Clock Select bits to prescaler = 1 (no prescaling)
    // CS12:CS11:CS10 = 0:0:1
    CLR_BIT(TCCR1B,CS12);
    CLR_BIT(TCCR1B,CS11);
    SET_BIT(TCCR1B,CS10);        
}

void TIMR1_Stop  (void)
{
    // Clear all Clock Select bits (Stop timer)
    // CS12:CS11:CS10 = 0:0:0
    CLR_BIT(TCCR1B,CS12);
    CLR_BIT(TCCR1B,CS11);
    CLR_BIT(TCCR1B,CS10);        
}