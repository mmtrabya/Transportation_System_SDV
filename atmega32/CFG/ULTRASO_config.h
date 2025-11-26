/*
 * ULTRASO_config.h
 *
 * Created: 2/11/2024 4:43:46 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef ULTRASO_CONFIG_H_
#define ULTRASO_CONFIG_H_

#include "../MCAL/DIO/DIO_interface.h"

// System Clock Frequency
//#define  F_CPU 16000000UL

// Port Definitions
#define ULTRASONIC_TRIG_PORT     DIO_PORTA
#define ULTRASONIC_ECHO_PORT     DIO_PORTD

// Trigger Pin Definitions (One for each sensor)
#define  ULTRASONIC1_TRIG_PIN    DIO_PIN0
#define  ULTRASONIC2_TRIG_PIN    DIO_PIN1
#define  ULTRASONIC3_TRIG_PIN    DIO_PIN2
#define  ULTRASONIC4_TRIG_PIN    DIO_PIN3

// Echo Pin Definition (Shared by all sensors - connected to ICP1/PD6)
#define  ULTRASONIC_ECHO_PIN     DIO_PIN6

#endif /* ULTRASO_CONFIG_H_ */