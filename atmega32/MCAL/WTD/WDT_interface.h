/*
 * WDT_interface.h
 *
 * Created: 4/8/2024 5:52:45 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef WDT_INTERFACE_H_
#define WDT_INTERFACE_H_

/**
 * @brief Start the Watchdog Timer with specified timeout period
 * @param Time_Ms: Timeout period (use WDT_xxx_Ms or WDT_xxx_us constants)
 */
void WDT_Start(u8 Time_Ms);

/**
 * @brief Stop/Disable the Watchdog Timer
 */
void WDT_Stop(void);

/**
 * @brief Reset the Watchdog Timer (feed the watchdog)
 */
void WDT_Reset(void);

void WDT_Enable(u8 timeout);

void WDT_Disable(void);


#endif /* WDT_INTERFACE_H_ */