/*
 * TIMR1_interface.h
 *
 * Created: 4/22/2024 4:12:58 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef TIMR1_INTERFACE_H_
#define TIMR1_INTERFACE_H_

#include "../../../STD_TYPES.h"

/*
 * Function: TIMR1_INITI
 * Description: Initializes Timer1 in Normal mode
 *              - Clears all compare output modes
 *              - Sets waveform generation mode to Normal (Mode 0)
 * Parameters: None
 * Returns: None
 */
void TIMR1_INITI (void);

/*
 * Function: TIMR1_Input_Capture
 * Description: Configures Timer1 Input Capture mode
 *              - Enables noise canceler
 *              - Sets edge detection (rising or falling)
 * Parameters: Edge - TIMR1_RISING_EDGE or TIMR1_FALLING_EDGE
 * Returns: None
 */
void TIMR1_Input_Capture (u8 Edge);

/*
 * Function: TIMR1_Start
 * Description: Starts Timer1 with prescaler = 1 (no division)
 *              - Sets CS10 = 1, CS11 = 0, CS12 = 0
 *              - Timer ticks at CPU frequency (16MHz)
 * Parameters: None
 * Returns: None
 */
void TIMR1_Start (void);

/*
 * Function: TIMR1_Stop
 * Description: Stops Timer1 by clearing all clock select bits
 * Parameters: None
 * Returns: None
 */
void TIMR1_Stop  (void);


#endif /* TIMR1_INTERFA*/