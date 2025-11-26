/*
 * SRVM_program.c
 *
 * Created: 3/4/2024 7:04:55 AM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#include "STD_TYPES.h"
#include "BIT_MATH.h"

#include "DIO_interface.h"
#include "DIO_private.h"
#include "DIO_config.h"

#include "TIMR1_interface.h"
#include "TIMR1_private.h"
#include "TIMR1_config.h"

#include "SRVM_interface.h"
#include "SRVM_private.h"




void SRVM_INIT  (void)
{

 DIO_SetPinDirection(SRVM_PIN_OUTPUT,SRVM_PORTD,SRVM_PIN5);  
 TIMR1_A_INIT();

}

void SRVM_Angle (u8 Angle)
{
  if (Angle == 180 || Angle == 90 || Angle == 0 )
  {
    switch (Angle)
    {
    case 0   :
              TIMR1_A_SetFastPWM(7.5,50);
              break;

    case 90  :
              TIMR1_A_SetFastPWM(10,50);
              break;

    case 180 :
              TIMR1_A_SetFastPWM(5,50);
              break;
    }
TIMR1_Start();    
  }
    
}

void SRVM_Stop  (void)
{

 TIMR1_Stop();

}