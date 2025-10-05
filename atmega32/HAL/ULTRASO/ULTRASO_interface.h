/*
 * ULTRASO_interface.h
 *
 * Created: 4/22/2024 4:33:03 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef ULTRASO_INTERFACE_H_
#define ULTRASO_INTERFACE_H_

#include "../../STD_TYPES.h"

/*
 * Function: ULTRAS_INITI
 * Description: Initializes ultrasonic sensor pins
 *              - Sets trigger pins (PB0-PB3) as outputs
 *              - Sets echo pin (PD6) as input
 * Parameters: None
 * Returns: None
 */
void  ULTRAS_INITI (void);

/*
 * Function: ULTRAS_TRIG
 * Description: Sends 10us trigger pulse to selected ultrasonic sensor
 * Parameters: TRIG_PIN - Pin number (ULTRASONIC1_TRIG_PIN to ULTRASONIC4_TRIG_PIN)
 * Returns: None
 */
void  ULTRAS_TRIG  (u8 TRIG_PIN);

/*
 * Function: ULTRAS_Read
 * Description: Reads distance from ultrasonic sensor
 *              - Sends trigger pulse
 *              - Measures echo pulse duration using Timer1 Input Capture
 *              - Calculates distance in centimeters
 *              - Returns -1.0 on error (timeout or out of range)
 * Parameters: 
 *   - Read: Pointer to float variable to store distance (in cm)
 *   - TRIG_PIN: Pin number (ULTRASONIC1_TRIG_PIN to ULTRASONIC4_TRIG_PIN)
 * Returns: Distance via pointer (2-400cm valid range, -1.0 for error)
 */
void  ULTRAS_Read  (f32* Read, u8 TRIG_PIN);


#endif /* ULTRASO_INTERFACE_H_ */