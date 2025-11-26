/*
 * STEPM_program.c
 *
 * Created: 4/20/2024 3:09:50 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 
#define  F_CPU  16000000UL 
#include <UTIL/delay.h>

#include "STD_TYPES.h"
#include "BIT_MATH.h"

#include "DIO_interface.h"
#include "DIO_private.h"
#include "DIO_config.h"

#include "STEPM_interface.h"
#include "STEPM_config.h"


void STEPM_INITI  (void)
{

  DIO_SetPinDirection(STEPM_PIN_OUTPUT,STEPM_PORTA,STEPM_PIN4);
  DIO_SetPinDirection(STEPM_PIN_OUTPUT,STEPM_PORTA,STEPM_PIN5);
  DIO_SetPinDirection(STEPM_PIN_OUTPUT,STEPM_PORTA,STEPM_PIN6);
  DIO_SetPinDirection(STEPM_PIN_OUTPUT,STEPM_PORTA,STEPM_PIN7);

}

void STEPM_Angule (u16 Angule)
{
   u16 COUNTER = 0;
   COUNTER = ((u32)Angule*1000)/(175*4);
   for ( u16 i = 0; i < COUNTER ; i++)
   {

    // First Step
     DIO_SetPinValue(STEPM_PIN_LOW,STEPM_PORTA,STEPM_PIN4);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN5);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN6);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN7);  
     _delay_ms(10); 

    // Second Step
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN4);
     DIO_SetPinValue(STEPM_PIN_LOW,STEPM_PORTA,STEPM_PIN5);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN6);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN7);  
     _delay_ms(10); 

    // Third Step
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN4);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN5);
     DIO_SetPinValue(STEPM_PIN_LOW,STEPM_PORTA,STEPM_PIN6);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN7);  
     _delay_ms(10); 

    // Fourth Step
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN4);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN5);
     DIO_SetPinValue(STEPM_PIN_HIGH,STEPM_PORTA,STEPM_PIN6);
     DIO_SetPinValue(STEPM_PIN_LOW,STEPM_PORTA,STEPM_PIN7);  
     _delay_ms(10); 

   }
    
}