/*
 * Application.h
 *
 * Created: 9/30/2025 12:45:40 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef APPLICATION_H_
#define APPLICATION_H_

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <util/delay.h>

#include "STD_TYPES.h"
#include "BIT_MATH.h"

#include "MCAL/DIO/DIO_interface.h"

#include "MCAL/ADC/ADC_interface.h"
#include "CFG/ADC_config.h"

#include "MCAL/EEPROM/EEPROM_Int.h"

#include "MCAL/GIE/GI_interface.h"
#include "MCAL/EXIT/EXIT_interface.h"
#include "CFG/EXIT_config.h"

#include "MCAL/SPI/SPI.h"
#include "MCAL/String/String.h"

#include "MCAL/TIMER0/TIMR0_interface.h"
#include "CFG/TIMR0_config.h"

#include "MCAL/TIMER1/VERSION_2_ULTRA_SONIC/TIMR1_interface.h"
#include "CFG/TIMR1_config.h"

#include "MCAL/TWI/TWI_interface.h"
#include "MCAL/TWI/TWI_private.h"

#include "MCAL/UART/UART_interface.h"
#include "CFG/UART_config.h"

#include "MCAL/WTD/WDT_interface.h"
#include "CFG/WDT_config.h"

#include "HAL/Buzzer/BUZZER_INTERFACE.h"

#include "HAL/DCM/DCM_interface.h"
#include "CFG/DCM_config.h"



#include "HAL/LCD/LCD_interface.h"
#include "HAL/LCD/LCD_private.h"
#include "CFG/LCD_config.h"

#include "HAL/LED/LEDS_INTERFACE.h"

#include "HAL/MPU9250/MPU9250_interface.h"
#include "CFG/MPU9250_config.h"
#include "HAL/ULTRASO/ULTRASO_interface.h"
#include "CFG/ULTRASO_config.h"


#include "APP/raspberry_pi_protocol.h"




#endif /* APPLICATION_H_ */