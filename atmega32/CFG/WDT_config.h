/*
 * WDT_config.h
 *
 * Created: 3/1/2024 1:55:30 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef WDT_CONFIG_H_
#define WDT_CONFIG_H_

/* Watchdog Timer Stop/Disable value */
#define   WDT_STOP             0x00 

/* Maximum timeout constant index */
#define   WDT_TimeConstant     7  

/* Watchdog Timer Timeout Periods */
#define   WDT_16300_us         0    /* 16.3 milliseconds */
#define   WDT_32500_us         1    /* 32.5 milliseconds */
#define   WDT_65_Ms            2    /* 65 milliseconds */
#define   WDT_130_Ms           3    /* 130 milliseconds */
#define   WDT_260_Ms           4    /* 260 milliseconds */
#define   WDT_520_Ms           5    /* 520 milliseconds */
#define   WDT_1000_Ms          6    /* 1.0 second */
#define   WDT_2100_Ms          7    /* 2.1 seconds */


#endif /* WDT_CONFIG_H_ */