/*
 * ULTRASO_program.c
 *
 * Created: 4/22/2024 4:32:47 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 *  CORRECTED VERSION - Fixed all critical bugs
 */ 

#define   F_CPU 16000000UL
#include <util/delay.h>
#include <avr/io.h>

#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"
#include "../../CFG/ULTRASO_config.h"
#include "../../MCAL/DIO/DIO_interface.h"


#include "../../MCAL/TIMER1/VERSION_2_ULTRA_SONIC/TIMR1_interface.h"
#include "../../CFG/TIMR1_config.h"

#include "ULTRASO_interface.h"

void  ULTRAS_INITI (void)
{
    DIO_setPinDirection(DIO_PIN_OUTPUT,DIO_PORTA,DIO_PIN0); //TRIG ULTRASONIC1
    DIO_setPinDirection(DIO_PIN_OUTPUT,DIO_PORTA,DIO_PIN1); //TRIG ULTRASONIC2
    DIO_setPinDirection(DIO_PIN_OUTPUT,DIO_PORTA,DIO_PIN2); //TRIG ULTRASONIC3
    DIO_setPinDirection(DIO_PIN_OUTPUT,DIO_PORTA,DIO_PIN3); //TRIG ULTRASONIC4
    DIO_setPinDirection(DIO_PIN_INPUT,DIO_PORTD,DIO_PIN6);  //ECHO PIN
}

void  ULTRAS_TRIG  (u8 TRIG_PIN)
{  
  switch (TRIG_PIN)
  {
  case ULTRASONIC1_TRIG_PIN:
    DIO_setPinValue(DIO_PIN_HIGH,DIO_PORTA,DIO_PIN0);
    _delay_us(10);
    DIO_setPinValue(DIO_PIN_LOW,DIO_PORTA,DIO_PIN0);
    break;
  
  case ULTRASONIC2_TRIG_PIN:
    DIO_setPinValue(DIO_PIN_HIGH,DIO_PORTA,DIO_PIN1);
    _delay_us(10);
    DIO_setPinValue(DIO_PIN_LOW,DIO_PORTA,DIO_PIN1);
    break;

  case ULTRASONIC3_TRIG_PIN:
    DIO_setPinValue(DIO_PIN_HIGH,DIO_PORTA,DIO_PIN2);
    _delay_us(10);
    DIO_setPinValue(DIO_PIN_LOW,DIO_PORTA,DIO_PIN2);
    break;

  case ULTRASONIC4_TRIG_PIN:
    DIO_setPinValue(DIO_PIN_HIGH,DIO_PORTA,DIO_PIN3);
    _delay_us(10);
    DIO_setPinValue(DIO_PIN_LOW,DIO_PORTA,DIO_PIN3);
    break;   

  }
}

void  ULTRAS_Read  (f32* Read , u8 TRIG_PIN)
{
  u16 Read1, Read2, Period;
  u32 timeout;
  
  // Initialize Timer1
  TIMR1_INITI();
  TIMR1_Start();
  
  // Clear Timer Counter - FIXED: was TCNT1L, now full 16-bit
  TCNT1 = 0;
  
  // Reset Input Capture Flag
  SET_BIT(TIFR, ICF1);
  
  // Send trigger pulse
  ULTRAS_TRIG(TRIG_PIN);
  
  // Wait for rising edge (start of echo pulse) with timeout
  TIMR1_Input_Capture(TIMR1_RISING_EDGE);
  timeout = 0;
  while ((GET_BIT(TIFR, ICF1)) == 0)
  {
    timeout++;
    if (timeout > 50000UL)  // Timeout protection (~3ms)
    {
      *Read = -1.0;  // Error: No echo received
      TIMR1_Stop();
      TCNT1 = 0;
      return;
    }
  }
  
  // FIXED: Read full 16-bit ICR1 register (was ICR1L - only 8 bits)
  Read1 = ICR1;
  
  // Reset flag for falling edge detection
  SET_BIT(TIFR, ICF1);
  
  // Wait for falling edge (end of echo pulse) with timeout
  TIMR1_Input_Capture(TIMR1_FALLING_EDGE);
  timeout = 0;
  while ((GET_BIT(TIFR, ICF1)) == 0)
  {
    timeout++;
    if (timeout > 50000UL)  // Timeout protection
    {
      *Read = -1.0;  // Error: Echo didn't complete
      TIMR1_Stop();
      TCNT1 = 0;
      return;
    }
  }
  
  // FIXED: Read full 16-bit ICR1 register (was ICR1L - only 8 bits)
  Read2 = ICR1;
  
  // Reset flag
  SET_BIT(TIFR, ICF1);
  
  // Stop timer and reset
  TIMR1_Stop();
  TCNT1 = 0;
  
  // Calculate echo pulse duration in timer ticks
  Period = Read2 - Read1;
  
  // Calculate distance in centimeters
  // Formula: Distance = (Period * SpeedOfSound) / (2 * F_CPU)
  // Speed of sound = 34600 cm/s
  // Factor of 2 because sound travels to object and back
  // FIXED: Added proper type casting to prevent overflow
  *Read = ((u32)Period * 34600UL) / ((u32)F_CPU * 2UL);
  
  // Optional: Validate range (HC-SR04 valid range: 2cm to 400cm)
  if (*Read < 2.0 || *Read > 400.0)
  {
    *Read = -1.0;  // Out of range
  }
}