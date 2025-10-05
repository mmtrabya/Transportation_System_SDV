
#include "../../MCAL/DIO/DIO_interface.h"
#include"../../STD_TYPES.h"
#include "BUZZER_INTERFACE.h"

void BUZZER_Init(void)
{
	DIO_setPinDirection(DIO_PIN_OUTPUT,BUZZER_PORT,BUZZER_PIN); //OUTPUT
}

void BUZZER_ON(void)
{
	DIO_setPinValue(DIO_PIN_HIGH,BUZZER_PORT,BUZZER_PIN); //HIGH
}

void BUZZER_OFF(void)
{
	DIO_setPinValue(DIO_PIN_LOW,BUZZER_PORT,BUZZER_PIN); //LOW
}