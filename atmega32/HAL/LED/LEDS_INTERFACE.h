#ifndef LEDS_INTERFACE_H_
#define LEDS_INTERFACE_H_

#include "../../MCAL/DIO/DIO_interface.h"
#include"../../STD_TYPES.h"



#define LED_PORT        DIO_PORTC
#define RED_LED_PIN     DIO_PIN5
#define GREEN_LED_PIN   DIO_PIN6
#define BLUE_LED_PIN    DIO_PIN7



void LED_Init(void);
void LED_ON(u8 pin);
void LED_OFF(u8 pin);




#endif /* LEDS_INTERFACE_H_ */