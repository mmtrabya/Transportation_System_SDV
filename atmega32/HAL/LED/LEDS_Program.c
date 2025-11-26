
#include "../../MCAL/DIO/DIO_interface.h"
#include"../../STD_TYPES.h"
#include "LEDS_INTERFACE.h"

void LED_Init(void)
{
 DIO_setPinDirection(DIO_PIN_OUTPUT,LED_PORT,RED_LED_PIN);     //output
 DIO_setPinDirection(DIO_PIN_OUTPUT,LED_PORT,GREEN_LED_PIN);   //output
 DIO_setPinDirection(DIO_PIN_OUTPUT,LED_PORT,BLUE_LED_PIN);    //output			
}

void LED_ON(u8 pin)
{
 switch (pin)
 {
  case RED_LED_PIN:
	               DIO_setPinValue(DIO_PIN_HIGH,LED_PORT,RED_LED_PIN);
	   break;
  case GREEN_LED_PIN:
	               DIO_setPinValue(DIO_PIN_HIGH,LED_PORT,GREEN_LED_PIN);
	   break;
  case BLUE_LED_PIN:
	               DIO_setPinValue(DIO_PIN_HIGH,LED_PORT,BLUE_LED_PIN);	   
       break;
 }
}
void LED_OFF(u8 pin)
{
switch (pin)
 {
  case RED_LED_PIN:
	               DIO_setPinValue(DIO_PIN_LOW,LED_PORT,RED_LED_PIN);
	   break;
  case GREEN_LED_PIN:
	               DIO_setPinValue(DIO_PIN_LOW,LED_PORT,GREEN_LED_PIN);
	   break;
  case BLUE_LED_PIN:
	               DIO_setPinValue(DIO_PIN_LOW,LED_PORT,BLUE_LED_PIN);	   
	   break;
 }	
}
