/*
 * TIMR0_config.h
 *
 * Created: 2/16/2024 3:03:34 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef TIMR0_CONFIG_H_
#define TIMR0_CONFIG_H_

#define TIMR0_Preload_Value        113
#define TIMR0_OVER_FLOW_COUNTER    977
#define TIMR0_Ticks                256

#define TIMR0_Mode     Fast_PWM

#define Normal_Mode   1 
#define CTC_Mode      2
#define Fast_PWM      3

#define TIMR0_FastPWM_Mode   FAST_PWM_Non_Inverting

#define FAST_PWM_Inverting         0
#define FAST_PWM_Non_Inverting     1





#endif /* TIMR0_CONFIG_H_ */