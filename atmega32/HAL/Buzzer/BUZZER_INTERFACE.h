#ifndef BUZZER_INTERFACE_H_
#define BUZZER_INTERFACE_H_

#include "../../MCAL/DIO/DIO_interface.h"
#include"../../STD_TYPES.h"



#define BUZZER_PORT        DIO_PORTC
#define BUZZER_PIN         DIO_PIN4




void BUZZER_Init(void);
void BUZZER_ON(void);
void BUZZER_OFF(void);




#endif /* LEDS_INTERFACE_H_ */