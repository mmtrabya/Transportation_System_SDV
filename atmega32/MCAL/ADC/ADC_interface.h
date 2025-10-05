/*
 * ADC_interface.h
 *
 * Created: 2/11/2024 4:43:18 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef ADC_INTERFACE_H_
#define ADC_INTERFACE_H_

#include "../../STD_TYPES.h"


void ADC_Initi             (u8 MAX_VOLTAGE);
void ADC_GetDigitalValue   (u8 Channle ,u16* returnValue);

#endif /* ADC_INTERFACE_H_ */