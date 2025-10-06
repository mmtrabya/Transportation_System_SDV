/*
 * UART_interface.h
 * UART Driver Interface for ATmega32
 * Created: 4/13/2024 2:41:33 AM
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 * UPDATED: Added utility functions
 */ 

#ifndef UART_INTERFACE_H_
#define UART_INTERFACE_H_

#include "../../STD_TYPES.h"

/*
 * Function: UART_Init
 * Description: Initializes UART with default settings
 *              - Baud rate: 9600 (configurable in UART_config.h)
 *              - Data bits: 8
 *              - Parity: None
 *              - Stop bits: 1
 *              - Mode: Asynchronous
 * Parameters: None
 * Returns: None
 */
void UART_Init(void);

/*
 * Function: UART_TX_Char
 * Description: Transmits a single character via UART
 * Parameters: TX_DATA - Character to transmit
 * Returns: None
 */
void UART_TX_Char(u8 TX_DATA);

/*
 * Function: UART_RX_Char
 * Description: Receives a single character via UART (blocking)
 * Parameters: RX_DATA - Pointer to store received character
 * Returns: None
 */
void UART_RX_Char(u8* RX_DATA);

/*
 * Function: UART_TX_String
 * Description: Transmits a null-terminated string via UART
 * Parameters: TX_STRING - Pointer to string to transmit
 * Returns: None
 */
void UART_TX_String(u8* TX_STRING);

/*
 * Function: UART_RX_String
 * Description: Receives a string via UART until newline or max length
 *              - Stops at '\r' or '\n'
 *              - Automatically null-terminates
 *              - Has timeout protection
 * Parameters: RX_STRING - Pointer to buffer for received string
 * Returns: None
 */
void UART_RX_String(u8* RX_STRING);

/*
 * Function: UART_RX_Available
 * Description: Checks if data is available to read (non-blocking)
 * Parameters: None
 * Returns: 1 if data available, 0 otherwise
 */
u8 UART_RX_Available(void);

/*
 * Function: UART_TX_Number
 * Description: Transmits a signed integer as ASCII string
 * Parameters: number - Integer to transmit (-2147483648 to 2147483647)
 * Returns: None
 */
void UART_TX_Number(S32 number);

/*
 * Function: UART_TX_Float
 * Description: Transmits a float as ASCII string
 * Parameters: 
 *   - number: Float to transmit
 *   - decimal_places: Number of decimal places (0-6 recommended)
 * Returns: None
 */
void UART_TX_Float(f32 number, u8 decimal_places);

void UART_SendByte(u8 data);

u8 UART_Read(void);

void UART_SendString(const char* str);

#endif /* UART_INTERFACE_H_ */