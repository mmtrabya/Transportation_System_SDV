/*
 * DCM_config.h
 * H-Bridge Configuration for 4 Motors with 2 Enable Pins
 * Group 1: Motor A & C share Enable Pin 1
 * Group 2: Motor B & D share Enable Pin 2
 * Created: 2/24/2024 1:10:24 PM
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#ifndef DCM_CONFIG_H_
#define DCM_CONFIG_H_

// H-Bridge Mode Only
#define DCM_H_Bridge      2

// Select Mode For All Motors
#define DCM_Modes_Motor_A    DCM_H_Bridge
#define DCM_Modes_Motor_B    DCM_H_Bridge
#define DCM_Modes_Motor_C    DCM_H_Bridge
#define DCM_Modes_Motor_D    DCM_H_Bridge

// Number of Motors
#define DCM_Motor_A       0
#define DCM_Motor_B       1
#define DCM_Motor_C       2
#define DCM_Motor_D       3

// Direction of Motors
#define DCM_CCW   0
#define DCM_CW    1

// DCM Port Connections
#define DCM_PORTA      DIO_PORTA
#define DCM_PORTB      DIO_PORTB
#define DCM_PORTC      DIO_PORTC
#define DCM_PORTD      DIO_PORTD

// H-Bridge Motor A Connections (First L298N - Motor 1)
#define DCM_MA_IN1           DIO_PIN2
#define DCM_MA_IN2           DIO_PIN3
#define DCM_MA_ENABLE        DIO_PIN4    // Shared Enable 1 (Group 1: A & C)
#define DCM_MA_IN_PORT       DIO_PORTD
#define DCM_MA_ENABLE_PORT   DIO_PORTD

// H-Bridge Motor C Connections (Second L298N - Motor 1)
// Motor C shares the same ENABLE as Motor A
#define DCM_MC_IN1           DIO_PIN2
#define DCM_MC_IN2           DIO_PIN3
#define DCM_MC_ENABLE        DIO_PIN4    // Shared Enable 1 (Group 1: A & C)
#define DCM_MC_IN_PORT       DIO_PORTD
#define DCM_MC_ENABLE_PORT   DIO_PORTD

// H-Bridge Motor B Connections (First L298N - Motor 2)
#define DCM_MB_IN3           DIO_PIN2
#define DCM_MB_IN4           DIO_PIN3
#define DCM_MB_ENABLE        DIO_PIN5    // Shared Enable 2 (Group 2: B & D)
#define DCM_MB_IN_PORT       DIO_PORTC
#define DCM_MB_ENABLE_PORT   DIO_PORTD

// H-Bridge Motor D Connections (Second L298N - Motor 2)
// Motor D shares the same ENABLE as Motor B
#define DCM_MD_IN3           DIO_PIN2
#define DCM_MD_IN4           DIO_PIN3
#define DCM_MD_ENABLE        DIO_PIN5    // Shared Enable 2 (Group 2: B & D)
#define DCM_MD_IN_PORT       DIO_PORTC
#define DCM_MD_ENABLE_PORT   DIO_PORTD

// Timer 0 PWM Pin (PB3/OC0)
// NOTE: Connect PB3 to BOTH enable pins (PD4 and PD5) through hardware
// Or use PB3 to only one enable pin if you want to control groups independently
#define DCM_PWM_PIN          DIO_PIN3
#define DCM_PWM_PORT         DIO_PORTB

// Pin States
#define DCM_PIN_HIGH       DIO_PIN_HIGH
#define DCM_PIN_LOW        DIO_PIN_LOW
#define DCM_PIN_OUTPUT     DIO_PIN_OUTPUT
#define DCM_PIN_INPUT      DIO_PIN_INPUT

/* HARDWARE WIRING NOTES:
 * =====================
 * You have 2 enable pins on your module:
 * - Enable 1 (PD4): Controls Motor A & Motor C together
 * - Enable 2 (PD5): Controls Motor B & Motor D together
 * 
 * PWM CONNECTION OPTIONS:
 * Option 1: Connect PB3 (Timer0 PWM) to BOTH PD4 and PD5
 *           Result: All 4 motors share same speed, different directions
 * 
 * Option 2: Connect PB3 to only PD4 OR PD5
 *           Result: Only Group 1 OR Group 2 has PWM speed control
 *           The other group runs at full speed when enabled
 */

#endif /* DCM_CONFIG_H_ */