/*
 * UART_program.c
 * UART Driver for ATmega32 - USB-to-TTL Compatible
 * Created: 4/13/2024 2:41:18 AM
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 * CORRECTED: Fixed RX_String bug and added timeout protection
 */ 

#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"
#include "../../REGS.h"
#include "../../CFG/UART_config.h"
#include "UART_interface.h"

void UART_INTI(void)
{
    // Disable Double Speed Mode
    CLR_BIT(UCSRA, U2X);
    
    // Set Baud Rate (9600 at 16MHz by default)
    UBRRL = UART_BAUD_RATE;
    
    // Configure UCSRC Register
    // URSEL=1 to select UCSRC (shared address with UBRRH)
    // UMSEL=0 for Asynchronous mode
    // UPM1:0=00 for No Parity
    // USBS=0 for 1 stop bit
    // UCSZ1:0=11 for 8-bit data (with UCSZ2=0)
    // UCPOL=0 (don't care in async mode)
    
    u8 ucsrc_value = 0x00;
    SET_BIT(ucsrc_value, URSEL);     // Select UCSRC register
    CLR_BIT(ucsrc_value, UMSEL);     // Asynchronous mode
    CLR_BIT(ucsrc_value, UMP1);      // No parity
    CLR_BIT(ucsrc_value, UMP0);      // No parity
    CLR_BIT(ucsrc_value, USBS);      // 1 stop bit
    SET_BIT(ucsrc_value, UCSZ1);     // 8-bit data size
    SET_BIT(ucsrc_value, UCSZ0);     // 8-bit data size
    CLR_BIT(ucsrc_value, UCPOL);     // Clock polarity (async: don't care)
    
    // Write to UCSRC
    UCSRC = ucsrc_value;
    
    // Configure UCSRB Register
    CLR_BIT(UCSRB, UCSZ2);           // 8-bit data size (with UCSZ1:0=11)
    SET_BIT(UCSRB, TXEN);            // Enable transmitter
    SET_BIT(UCSRB, RXEN);            // Enable receiver
    
    // Optional: Enable RX/TX interrupts
    // SET_BIT(UCSRB, RXCIE);        // RX Complete Interrupt Enable
    // SET_BIT(UCSRB, TXCIE);        // TX Complete Interrupt Enable
}

void UART_TX_Char(u8 TX_DATA)
{
    // Wait until transmit buffer is empty (UDRE flag set)
    while (GET_BIT(UCSRA, UDRE) == 0);
    
    // Put data into buffer, sends the data
    UDR = TX_DATA;
}

void UART_RX_Char(u8* RX_DATA)
{
    // Validate pointer
    if (RX_DATA != NULL)
    {
        // Wait for data to be received (RXC flag set)
        while (GET_BIT(UCSRA, RXC) == 0);
        
        // Get and return received data from buffer
        *RX_DATA = UDR;
    }
}

void UART_TX_String(u8* TX_STRING)
{
    // Validate pointer
    if (TX_STRING != NULL)
    {
        u8 counter = 0;
        
        // Send characters until null terminator
        while (TX_STRING[counter] != '\0')
        {
            UART_TX_Char(TX_STRING[counter]);
            counter++;
        }
    }
}

void UART_RX_String(u8* RX_STRING)
{
    // FIXED: Complete rewrite with proper logic
    if (RX_STRING != NULL)
    {
        u8 counter = 0;
        u8 received_char;
        
        // Receive characters until newline or max length
        while (1)
        {
            // Wait for character with timeout protection
            u32 timeout = 0;
            while (GET_BIT(UCSRA, RXC) == 0)
            {
                timeout++;
                if (timeout > UART_RX_TIMEOUT)
                {
                    // Timeout: terminate string and return
                    RX_STRING[counter] = '\0';
                    return;
                }
            }
            
            // Read character
            received_char = UDR;
            
            // Check for end conditions
            if (received_char == '\r' || received_char == '\n')
            {
                // Newline detected: terminate string
                RX_STRING[counter] = '\0';
                return;
            }
            
            // Check buffer overflow protection
            if (counter >= (UART_MAX_STRING_LENGTH - 1))
            {
                // Buffer full: terminate string
                RX_STRING[counter] = '\0';
                return;
            }
            
            // Store character and increment counter
            RX_STRING[counter] = received_char;
            counter++;
        }
    }
}

// Optional: Non-blocking receive function
u8 UART_RX_Available(void)
{
    // Returns 1 if data is available, 0 otherwise
    return GET_BIT(UCSRA, RXC);
}

// Optional: Transmit integer as string
void UART_TX_Number(S32 number)
{
    u8 buffer[12];  // Enough for 32-bit int + sign + null
    u8 i = 0;
    u8 is_negative = 0;
    
    // Handle negative numbers
    if (number < 0)
    {
        is_negative = 1;
        number = -number;
    }
    
    // Handle zero case
    if (number == 0)
    {
        UART_TX_Char('0');
        return;
    }
    
    // Convert to string (reversed)
    while (number > 0)
    {
        buffer[i++] = (number % 10) + '0';
        number /= 10;
    }
    
    // Add negative sign if needed
    if (is_negative)
    {
        buffer[i++] = '-';
    }
    
    // Send in correct order (reverse)
    while (i > 0)
    {
        UART_TX_Char(buffer[--i]);
    }
}

// Optional: Transmit float as string
void UART_TX_Float(f32 number, u8 decimal_places)
{
    S32 int_part = (S32)number;
    f32 frac_part = number - (f32)int_part;
    
    // Handle negative
    if (number < 0)
    {
        UART_TX_Char('-');
        int_part = -int_part;
        frac_part = -frac_part;
    }
    
    // Send integer part
    UART_TX_Number(int_part);
    
    // Send decimal point
    UART_TX_Char('.');
    
    // Send fractional part
    for (u8 i = 0; i < decimal_places; i++)
    {
        frac_part *= 10;
        u8 digit = (u8)frac_part;
        UART_TX_Char(digit + '0');
        frac_part -= digit;
    }
}
// Wrapper functions for compatibility
void UART_Init(void) {
    UART_INTI();
}

void UART_SendByte(u8 data) {
    UART_TX_Char(data);
}

u8 UART_Read(void) {
    u8 data;
    UART_RX_Char(&data);
    return data;
}

void UART_SendString(const char* str) {
    while (*str) {
        UART_SendByte(*str++);
    }
}