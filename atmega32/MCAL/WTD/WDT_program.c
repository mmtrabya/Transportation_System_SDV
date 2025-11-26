/*
 * WDT_program.c
 *
 * Created: 4/8/2024 5:52:29 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"

#include "WDT_interface.h"
#include "../../CFG/WDT_config.h"
#include "../../REGS.h"


void WDT_Start(u8 Time_Ms)
{
    if (Time_Ms <= WDT_TimeConstant)
    {
        /* Configure prescaler bits based on timeout period */
        switch (Time_Ms)
        {
            case WDT_16300_us:
                CLR_BIT(WDTCR, WDP2);
                CLR_BIT(WDTCR, WDP1);
                CLR_BIT(WDTCR, WDP0);
                break;

            case WDT_32500_us:
                CLR_BIT(WDTCR, WDP2);
                CLR_BIT(WDTCR, WDP1);
                SET_BIT(WDTCR, WDP0);
                break;   

            case WDT_65_Ms:
                CLR_BIT(WDTCR, WDP2);
                SET_BIT(WDTCR, WDP1);
                CLR_BIT(WDTCR, WDP0);
                break;

            case WDT_130_Ms:
                CLR_BIT(WDTCR, WDP2);
                SET_BIT(WDTCR, WDP1);
                SET_BIT(WDTCR, WDP0);
                break;

            case WDT_260_Ms:
                SET_BIT(WDTCR, WDP2);
                CLR_BIT(WDTCR, WDP1);
                CLR_BIT(WDTCR, WDP0);
                break;

            case WDT_520_Ms:
                SET_BIT(WDTCR, WDP2);
                CLR_BIT(WDTCR, WDP1);
                SET_BIT(WDTCR, WDP0);
                break;

            case WDT_1000_Ms:
                SET_BIT(WDTCR, WDP2);
                SET_BIT(WDTCR, WDP1);
                CLR_BIT(WDTCR, WDP0);
                break;

            case WDT_2100_Ms:
                SET_BIT(WDTCR, WDP2);
                SET_BIT(WDTCR, WDP1);
                SET_BIT(WDTCR, WDP0);
                break;
        }
        
        /* Enable the Watchdog Timer */
        SET_BIT(WDTCR, WDE);
    }
}

void WDT_Stop(void)
{
    /* Write logical one to WDTOE and WDE */
    /* Keep old prescaler setting to prevent unintentional time-out */
    WDTCR = (1 << WDTOE) | (1 << WDE);
    
    /* Turn off WDT within 4 clock cycles */
    WDTCR = WDT_STOP;
}

void WDT_Reset(void)
{
    /* Reset the Watchdog Timer */
    __asm__ __volatile__ ("wdr");
}
// Wrapper functions for compatibility
void WDT_Enable(u8 timeout) {
    WDT_Start(timeout);
}

void WDT_Disable(void) {
    WDT_Stop();
}
