/*
 * TIMR1_config.h
 *
 * Created: 3/1/2024 1:55:30 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef TIMR1_CONFIG_H_
#define TIMR1_CONFIG_H_

// Timer1 Mode Configuration for Channel A and B
#define  TIMR1_Mode_A     TIMR1_Fast_PWM_Mode
#define  TIMR1_Mode_B     TIMR1_Fast_PWM_Mode

// Timer1 Operating Modes
#define  TIMR1_Normal_Mode                0
#define  TIMR1_CTC_Mode                   1
#define  TIMR1_PWM_Phase_Correct_Mode     2 
#define  TIMR1_Fast_PWM_Mode              3   

// Tick Time Configuration (in microseconds)
// With F_CPU = 16MHz and prescaler = 1:
// Tick Time = 1 / 16MHz = 0.0625 us = 62.5 ns
// This config shows 4us, likely for a different prescaler setting
#define  TickTime      4

// Input Capture Edge Selection
#define     TIMR1_RISING_EDGE         0
#define     TIMR1_FALLING_EDGE        1

/*
 * Additional Mode Configurations (Currently Commented Out)
 * Uncomment and configure as needed for PWM applications
 */

/*
// Fast PWM Configuration for Channel A and B
#define TIMR1_A_Fast_PWM    FAST_PWM_Non_Inverting
#define TIMR1_B_Fast_PWM    FAST_PWM_Non_Inverting

// Fast PWM Modes
#define FAST_PWM_Non_Inverting    0
#define FAST_PWM_Inverting        1

// Timer1 Waveform Generation Mode Numbers
#define TIMR1_A_Mode_Number   TIMR1_Mode_14
#define TIMR1_B_Mode_Number   TIMR1_Mode_14

// All 16 Timer1 Modes (0-15)
#define TIMR1_Mode_0           0   // Normal
#define TIMR1_Mode_1           1   // PWM, Phase Correct, 8-bit
#define TIMR1_Mode_2           2   // PWM, Phase Correct, 9-bit
#define TIMR1_Mode_3           3   // PWM, Phase Correct, 10-bit
#define TIMR1_Mode_4           4   // CTC (OCR1A)
#define TIMR1_Mode_5           5   // Fast PWM, 8-bit
#define TIMR1_Mode_6           6   // Fast PWM, 9-bit
#define TIMR1_Mode_7           7   // Fast PWM, 10-bit
#define TIMR1_Mode_8           8   // PWM, Phase and Frequency Correct (ICR1)
#define TIMR1_Mode_9           9   // PWM, Phase and Frequency Correct (OCR1A)
#define TIMR1_Mode_10          10  // PWM, Phase Correct (ICR1)
#define TIMR1_Mode_11          11  // PWM, Phase Correct (OCR1A)
#define TIMR1_Mode_12          12  // CTC (ICR1)
#define TIMR1_Mode_13          13  // Reserved
#define TIMR1_Mode_14          14  // Fast PWM (ICR1)
#define TIMR1_Mode_15          15  // Fast PWM (OCR1A)
*/


#endif /* TIMR1_CONFIG_H_ */