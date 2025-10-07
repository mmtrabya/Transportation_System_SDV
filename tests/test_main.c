/*
 * simple_uart_test.c
 * ABSOLUTE SIMPLEST UART TEST - Just sends "Hello" forever
 * Use this to verify UART works at all
 * 
 * ALSO BLINKS LED on PORTB.0 to confirm code is running
 */

#include <avr/io.h>
#include <util/delay.h>

// CRITICAL: Set your actual clock frequency
#define F_CPU 8000000UL
#define BAUD 9600
// For 115200 on 8MHz using U2X, choose UBRR = 8
#define MYUBRR 51

void UART_Init(void) {
    UBRRH = (unsigned char)(MYUBRR >> 8);
    UBRRL = (unsigned char)MYUBRR;
    UCSRB = (1 << TXEN) | (1 << RXEN);   // Enable TX and RX
    UCSRC = (1 << URSEL) | (1 << UCSZ1) | (1 << UCSZ0);  // 8-bit data
}

void UART_Transmit(unsigned char data) {
    // Wait for empty transmit buffer
    while (!(UCSRA & (1 << UDRE)));
    
    // Put data into buffer, sends the data
    UDR = data;
}

void UART_SendString(const char* str) {
    while (*str) {
        UART_Transmit(*str++);
    }
}

int main(void) {
    // Setup LED on PB0 for visual confirmation
    DDRB |= (1 << PB0);  // Set PB0 as output
    
    // Initialize UART
    UART_Init();
    
    // Small delay for stability
    _delay_ms(500);
    
    // Send startup message
    UART_SendString("\r\n\r\n");
    UART_SendString("========================================\r\n");
    UART_SendString("ATmega32 Simple UART Test\r\n");
    UART_SendString("F_CPU: ");
    
    // Send F_CPU value
    if (F_CPU == 16000000UL) {
        UART_SendString("16MHz");
    } else if (F_CPU == 8000000UL) {
        UART_SendString("8MHz");
    } else {
        UART_SendString("Other");
    }
    UART_SendString("\r\n");
    
    UART_SendString("UBRR: ");
    // Simple UBRR display (just show if it's 8 or 16)
    if (MYUBRR == 8) {
        UART_SendString("8");
    } else if (MYUBRR == 16) {
        UART_SendString("16");
    } else {
        UART_SendString("??");
    }
    UART_SendString("\r\n");
    
    UART_SendString("========================================\r\n");
    UART_SendString("\r\n");
    
    unsigned int counter = 0;
    
    while (1) {
        // Blink LED (confirms code is running)
        PORTB ^= (1 << PB0);
        
        // Send message
        UART_SendString("Hello from ATmega32! Count: ");
        
        // Send counter value (simple method)
        UART_Transmit('0' + (counter / 100) % 10);
        UART_Transmit('0' + (counter / 10) % 10);
        UART_Transmit('0' + (counter % 10));
        
        UART_SendString("\r\n");
        
        counter++;
        if (counter > 999) counter = 0;
        
        // Wait 1 second
        _delay_ms(1000);
    }
    
    return 0;
}