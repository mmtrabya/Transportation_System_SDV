/*
 * ADC_program.c
 *
 * Created: 2/11/2024 4:46:05 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

//UTAL
#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"

//MCAL
#include "ADC_interface.h"
#include"../../REGS.h"
#include "../../CFG/ADC_config.h"


void ADC_Initi           (u8 MAX_VOLTAGE)
{
  switch (MAX_VOLTAGE)
  {

    case ADC_Reference_AVCC     :
                             CLR_BIT(ADMUX,REFS1);
                             SET_BIT(ADMUX,REFS0); 
    break;

    case ADC_Reference_AREF     :
                             CLR_BIT(ADMUX,REFS1);
                             CLR_BIT(ADMUX,REFS0); 
    break;

    case ADC_Reference_INTERNAL :
                             SET_BIT(ADMUX,REFS1);
                             SET_BIT(ADMUX,REFS0); 
    break;

  }

// RIGHT ADJUST
     CLR_BIT(ADMUX,ADLAR);

// Single Convertion mode
     CLR_BIT(ADCSRA,ADATE); 

// ADC INTERRUPT ENABLE
     CLR_BIT(ADCSRA,ADIE);

// ADC PRESCALER SELECT (125KHz) 
     SET_BIT(ADCSRA,ADPS0);
     SET_BIT(ADCSRA,ADPS1);
     SET_BIT(ADCSRA,ADPS2);

// ADC ENABLE
     SET_BIT(ADCSRA,ADEN);

}

void ADC_GetDigitalValue  (u8 Channle ,u16* returnValue)
{

if((Channle<=7)&&(returnValue != NULL)){

     switch (Channle) {
                         case ADC_Channle_0    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_0; // We Select Channle Number zero
                                                     break;
                         case ADC_Channle_1    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_1; // We Select Channle Number one
                                                     break;
                         case ADC_Channle_2    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_2; // We Select Channle Number two
                                                     break;
                         case ADC_Channle_3    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_3; // We Select Channle Number three
                                                     break;
                         case ADC_Channle_4    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_4; // We Select Channle Number four
                                                     break;
                         case ADC_Channle_5    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_5; // We Select Channle Number five
                                                     break;
                         case ADC_Channle_6    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_6; // We Select Channle Number six
                                                     break;
                         case ADC_Channle_7    :
                                                     ADMUX&=CLR_Channle_Num;          // Clear Channle Number We Sit it 
                                                     ADMUX|=ADC_Channle_7; // We Select Channle Number seven
                                                     break;
                                                                                                       
                       }
// Start Convertion
SET_BIT(ADCSRA, ADSC);

// Monitor ADC Flag of ADC
while (GET_BIT(ADCSRA,ADIF)==0);

// Clear Flag (Write one to Clear)
SET_BIT(ADCSRA,ADIF);

*returnValue = ADCL_U16;
                                        }
}

