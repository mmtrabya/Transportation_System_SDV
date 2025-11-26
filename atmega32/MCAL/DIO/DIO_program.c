/*
 * DIO_program.c
 *
 * Created: 9/2/2023 12:29:04 PM
 *  Author: mahmoud
 */ 

#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"
#include"../../REGS.h"
#include "DIO_interface.h"


void DIO_setPinDirection      ( u8 PinDirection , u8 PortId , u8 PinId )
{

if((PinId<=7)&&(PortId<=3)&&((PinDirection==DIO_PIN_OUTPUT)|(PinDirection==DIO_PIN_INPUT))){    
            
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  switch (PinDirection) {
                                      case DIO_PIN_OUTPUT:  SET_BIT(DDRA, PinId);
                                             break;
                                      case DIO_PIN_INPUT:   CLR_BIT(DDRA, PinId);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTB :
                                  switch (PinDirection) {
                                      case DIO_PIN_OUTPUT:  SET_BIT(DDRB, PinId);
                                             break;
                                      case DIO_PIN_INPUT:   CLR_BIT(DDRB, PinId);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTC :
                                  switch (PinDirection) {
                                      case DIO_PIN_OUTPUT:  SET_BIT(DDRC, PinId);
                                             break;
                                      case DIO_PIN_INPUT:   CLR_BIT(DDRC, PinId);
                                             break;       
                                                        }
                                break; 

                case DIO_PORTD :
                                  switch (PinDirection) {
                                      case DIO_PIN_OUTPUT:  SET_BIT(DDRD, PinId);
                                             break;
                                      case DIO_PIN_INPUT:   CLR_BIT(DDRD, PinId);
                                             break;       
                                                        }
                                break;                                                                                                 

                           }

                                                                   }
else
                                                                   {
    
                                                                   }                                                                   

}

void DIO_setPinValue          (u8 PinValue     ,  u8 PortId,  u8 PinId )
{
if((PinId<=7)&&(PortId<=3)&&((PinValue==DIO_PIN_HIGH)|(PinValue==DIO_PIN_LOW))){    
            
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  switch (PinValue) {
                                      case DIO_PIN_HIGH:  SET_BIT(PORTA, PinId);
                                             break;
                                      case DIO_PIN_LOW :  CLR_BIT(PORTA, PinId);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTB :
                                  switch (PinValue) {
                                      case DIO_PIN_HIGH:  SET_BIT(PORTB, PinId);
                                             break;
                                      case DIO_PIN_LOW :  CLR_BIT(PORTB, PinId);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTC :
                                  switch (PinValue) {
                                      case DIO_PIN_HIGH:  SET_BIT(PORTC, PinId);
                                             break;
                                      case DIO_PIN_LOW :  CLR_BIT(PORTC, PinId);
                                             break;       
                                                        }
                                break; 

                case DIO_PORTD :
                                  switch (PinValue) {
                                      case DIO_PIN_HIGH:  SET_BIT(PORTD, PinId);
                                             break;
                                      case DIO_PIN_LOW :  CLR_BIT(PORTD, PinId);
                                             break;       
                                                        }
                                break;                                                                                                 

                           }

                                                                               }
else
                                                                               {
    
                                                                               }                                                                   

}

void DIO_togglePinValue       (u8 PortId                    , u8 PinId )
{

if((PinId<=7)&&(PortId<=3)){    
           
            switch (PortId)  
                           {
                case DIO_PORTA :
                                    TOG_BIT(PORTA, PinId); 
                                break; 
                case DIO_PORTB :
                                    TOG_BIT(PORTB, PinId);
                                break; 
                case DIO_PORTC :
                                    TOG_BIT(PORTC, PinId);
                                break; 

                case DIO_PORTD :
                                    TOG_BIT(PORTD, PinId);
                                break;                                                                                                 

                           }

                           }
else
                           {
    
                           }                                                                   

}    

void DIO_getPinValue          (u8*PinValue     , u8 PortId  , u8 PinId )
{

if((PinId<=7)&&(PortId<=3)&&(PinValue != NULL)){    
           
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  *PinValue=GET_BIT(PINA, PinId);
                                break; 
                case DIO_PORTB :
                                  *PinValue=GET_BIT(PINB, PinId);
                                break; 
                case DIO_PORTC :
                                  *PinValue=GET_BIT(PINC, PinId);
                                break; 
                case DIO_PORTD :
                                  *PinValue=GET_BIT(PIND, PinId);
                                break;                                                                                                 
                           }

                                                 }
else
                                                 {
    
                                                 }       
}

void DIO_activePullUp         (u8 PortId                    , u8 PinId )
{

if((PinId<=7)&&(PortId<=3)){    
           
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  SET_BIT(PORTA, PinId);
                                break; 
                case DIO_PORTB :
                                  SET_BIT(PORTB, PinId);
                                break; 
                case DIO_PORTC :
                                  SET_BIT(PORTC, PinId);
                                break; 
                case DIO_PORTD :
                                  SET_BIT(PORTD, PinId);
                                break;                                                                                                 
                           }

                                                 }
else
                                                 {
    
                                                 }

}

void DIO_setPortDirection    (u8 PortDirection , u8 PortId)
{

if((PortId<=3)&&((PortDirection==DIO_PORT_OUTPUT)|(PortDirection==DIO_PORT_INPUT))){    
            
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  switch (PortDirection) {
                                      case DIO_PORT_OUTPUT:  SET_PORT(DDRA);
                                             break;
                                      case DIO_PORT_INPUT:  CLR_PORT(DDRA);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTB :
                                  switch (PortDirection) {
                                      case DIO_PORT_OUTPUT:  SET_PORT(DDRB);
                                             break;
                                      case DIO_PORT_INPUT:  CLR_PORT(DDRB);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTC :
                                  switch (PortDirection) {
                                      case DIO_PORT_OUTPUT:  SET_PORT(DDRC);
                                             break;
                                      case DIO_PORT_INPUT:  CLR_PORT(DDRC);
                                             break;       
                                                        }
                                break; 

                case DIO_PORTD :
                                  switch (PortDirection) {
                                      case DIO_PORT_OUTPUT:  SET_PORT(DDRD);
                                             break;
                                      case DIO_PORT_INPUT:  CLR_PORT(DDRD);
                                             break;       
                                                        }
                                break;                                                                                                 

                           }

                                                                   }
else
                                                                   {
    
                                                                   }        
}

void DIO_setPortValue        (u8 PortValue     , u8 PortId)
{

if((PortId<=3)&&((PortValue==DIO_PORT_HIGH)|(PortValue==DIO_PORT_LOW))){    
            
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  switch (PortValue)    {
                                      case DIO_PORT_HIGH:  SET_PORT(PORTA);
                                             break;
                                      case DIO_PORT_LOW :  CLR_PORT(PORTA);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTB :
                                  switch (PortValue)    {
                                      case DIO_PORT_HIGH:  SET_PORT(PORTB);
                                             break;
                                      case DIO_PORT_LOW :  CLR_PORT(PORTB);
                                             break;       
                                                        }
                                break; 
                case DIO_PORTC :
                                  switch (PortValue)    {
                                      case DIO_PORT_HIGH:  SET_PORT(PORTC);
                                             break;
                                      case DIO_PORT_LOW :  CLR_PORT(PORTC);
                                             break;       
                                                        }
                                break; 

                case DIO_PORTD :
                                  switch (PortValue)    {
                                      case DIO_PORT_HIGH:  SET_PORT(PORTD);
                                             break;
                                      case DIO_PORT_LOW :  CLR_PORT(PORTD);
                                             break;       
                                                        }
                                break;                                                                                                 

                           }

                                                                   }
else
                                                                   {
    
                                                                   }        
}

void DIO_togglePortValue     (u8 PortId                   )
{

if((PortId<=3))            {  
            switch (PortId)  
                           {
                case DIO_PORTA :
                                    TOG_PORT(PORTA); 
                                break; 
                case DIO_PORTB :
                                    TOG_PORT(PORTB);
                                break; 
                case DIO_PORTC :
                                    TOG_PORT(PORTC);
                                break; 

                case DIO_PORTD :
                                    TOG_PORT(PORTD);
                                break;                                                                                                 

                           }

                           }
                           
else
                           {
    
                           }   
}

void DIO_getPortValue        (u8*PortValue[DIO_MSB]     , u8 PortId)
{
if((PortId<=3)&&(PortValue != NULL)){    
           
            switch (PortId)  
                           {
                case DIO_PORTA :
                              for(int BIT=DIO_LSB;BIT<=DIO_MSB;BIT++){
                                  *PortValue[BIT]=GET_BIT(PINA, BIT);}
                                break; 
                case DIO_PORTB :
                              for(int BIT=DIO_LSB;BIT<=DIO_MSB;BIT++){
                                  *PortValue[BIT]=GET_BIT(PINB, BIT);}
                                break; 
                case DIO_PORTC :
                              for(int BIT=DIO_LSB;BIT<=DIO_MSB;BIT++){
                                  *PortValue[BIT]=GET_BIT(PINC, BIT);}
                                break; 
                case DIO_PORTD :
                              for(int BIT=DIO_LSB;BIT<=DIO_MSB;BIT++){
                                  *PortValue[BIT]=GET_BIT(PIND, BIT);}
                                break;                                                                                                 
                           }

                                                 }
else
                                                 {
    
                                                 }
}
void DIO_activePortPullUp    (u8 PortId                   )
{

if((PortId<=3)){    
           
            switch (PortId)  
                           {
                case DIO_PORTA :
                                  SET_PORT(PORTA);
                                break; 
                case DIO_PORTB :
                                  SET_PORT(PORTB);
                                break; 
                case DIO_PORTC :
                                  SET_PORT(PORTC);
                                break; 
                case DIO_PORTD :
                                  SET_PORT(PORTD);
                                break;                                                                                                 
                           }

                                                 }
else
                                                 {
    
                                                 }
}                                                 