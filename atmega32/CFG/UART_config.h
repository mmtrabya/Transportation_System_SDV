/*
 * UART_config.h
 * UART Configuration for ATmega32
 * Created: 4/13/2024 5:03:01 AM
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 * CORRECTED: Added baud rate and buffer size configuration
 */ 

#ifndef UART_CONFIG_H_
#define UART_CONFIG_H_

/* System Configuration */
#define F_CPU_UART          16000000UL

/* Baud Rate Configuration */
// UBRR = (F_CPU / (16 * BAUD_RATE)) - 1
// For 16MHz and 9600 baud: UBRR = 103

#define UART_BAUD_9600      103
#define UART_BAUD_19200     51
#define UART_BAUD_38400     25
#define UART_BAUD_57600     16
#define UART_BAUD_115200    8

// Select desired baud rate (default: 115200)
#define UART_BAUD_RATE      UART_BAUD_115200

/* Buffer and Timeout Configuration */
#define UART_MAX_STRING_LENGTH    100    // Maximum string length for RX_String
#define UART_RX_TIMEOUT           100000UL  // Timeout counter for RX operations

/* Hardware Pin Definitions (Fixed in ATmega32) */
// Note: These are hardware-defined and cannot be changed
#define UART_TX_PIN     DIO_PIN1         // PD1 (TXD)
#define UART_RX_PIN     DIO_PIN0         // PD0 (RXD)
#define UART_PORT       DIO_PORTD

/* Communication Settings (Fixed in UART_INTI) */
// These are configured in code:
// - 8 data bits
// - No parity
// - 1 stop bit
// - Asynchronous mode

#endif /* UART_CONFIG_H_ */