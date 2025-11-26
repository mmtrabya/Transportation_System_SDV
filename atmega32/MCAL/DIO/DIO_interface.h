/*
 * DIO_interface.h
 *
 * Created: 9/2/2023 12:28:28 PM
 *  Author: mahmoud
 */ 

#include "../../STD_TYPES.h"

#ifndef DIO_INTERFACE_H_
#define DIO_INTERFACE_H_

// PIN_Direction
#define  DIO_PIN_OUTPUT   1
#define  DIO_PIN_INPUT   0

// PIN_Value
#define  DIO_PIN_HIGH     1
#define  DIO_PIN_LOW      0

// PORT_Direction
#define  DIO_PORT_OUTPUT   1
#define  DIO_PORT_INPUT   0

// PORT_Value
#define  DIO_PORT_HIGH     1
#define  DIO_PORT_LOW      0

// PIN_Defnition  
#define DIO_PIN0          0
#define DIO_PIN1          1 
#define DIO_PIN2          2
#define DIO_PIN3          3
#define DIO_PIN4          4
#define DIO_PIN5          5
#define DIO_PIN6          6
#define DIO_PIN7          7

// PORT_Defnition
#define DIO_PORTA          0
#define DIO_PORTB          1 
#define DIO_PORTC          2
#define DIO_PORTD          3

#define DIO_LSB            0 
#define DIO_MSB            7 

// PIN
void DIO_setPinDirection    (u8 PinDirection , u8 PortId, u8 PinId );
void DIO_setPinValue        (u8 PinValue     , u8 PortId, u8 PinId );
void DIO_togglePinValue     (u8 PortId                  , u8 PinId );
void DIO_getPinValue        (u8*PinValue     , u8 PortId, u8 PinId );
void DIO_activePullUp       (u8 PortId                  , u8 PinId );

// PORT
void DIO_setPortDirection    (u8 PortDirection        , u8 PortId);
void DIO_setPortValue        (u8 PortValue            , u8 PortId);
void DIO_togglePortValue     (u8 PortId                          );
void DIO_getPortValue        (u8*PortValue[DIO_MSB]   , u8 PortId);
void DIO_activePortPullUp    (u8 PortId                          );



#endif /* LED_INTERFACE_H_ */