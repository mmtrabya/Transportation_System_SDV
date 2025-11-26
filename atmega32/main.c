/*
 * main.c
 * Main application for SDV ATmega32 Controller
 * 
 * Location: atmega32/main.c
 * 
 * Features:
 * - GPS Module (NEO-6M)
 * - IMU 9DOF (MPU9250 + QMC5883L)
 * - Motor Control (L298N - 4 motors)
 * - Ultrasonic Sensors (4x HC-SR04)
 * - Raspberry Pi Communication (UART)
 */

#include "Application.h"
#include "APP/raspberry_pi_protocol.h"

/* ==================== GLOBAL FLAGS ==================== */

volatile u8 uart_data_received = 0;
volatile u8 uart_byte = 0;

/* ==================== UART RX INTERRUPT ==================== */

ISR(UART_RX_vect) {
    // Read received byte
    uart_byte = UDR;
    uart_data_received = 1;
}

/* ==================== SYSTEM INITIALIZATION ==================== */

void System_Init(void) {
    // Disable interrupts during initialization
    cli();
    
    // Initialize all modules via protocol
    Protocol_Init();
    
    // Enable UART RX interrupt
    SET_BIT(UCSRB, RXCIE);
    
    // Enable global interrupts
    sei();
    
    // Startup indication
    BUZZER_ON();
    LED_ON(GREEN_LED_PIN);
    _delay_ms(200);
    BUZZER_OFF();
    LED_OFF(GREEN_LED_PIN);
}

/* ==================== PERIODIC TASKS ==================== */

void Update_Sensors_Periodic(void) {
    static u32 last_sensor_update = 0;
    static u32 tick_counter = 0;
    
    tick_counter++;
    
    // Update sensors every ~1 second (approximate)
    if (tick_counter - last_sensor_update > 10000) {
        last_sensor_update = tick_counter;
        
        // Update system uptime
        Protocol_UpdateUptime();
        
        // Optional: Blink status LED
        LED_ON(GREEN_LED_PIN);
        _delay_ms(50);
        LED_OFF(GREEN_LED_PIN);
    }
}

/* ==================== MAIN FUNCTION ==================== */

int main(void) {
    // Initialize system
    System_Init();
    
    // Main loop
    while (1) {
        // Process incoming UART data
        if (uart_data_received) {
            uart_data_received = 0;
            Protocol_ProcessByte(uart_byte);
        }
        
        // Periodic sensor updates
        Update_Sensors_Periodic();
        
        // Small delay to prevent busy-waiting
        _delay_ms(1);
    }
    
    return 0;
}

/* ==================== ALTERNATIVE: POLLING MODE ==================== */

#ifdef USE_POLLING_MODE

int main_polling(void) {
    // Initialize system (without UART interrupt)
    cli();
    Protocol_Init();
    sei();
    
    // Startup indication
    BUZZER_ON();
    LED_ON(GREEN_LED_PIN);
    _delay_ms(200);
    BUZZER_OFF();
    LED_OFF(GREEN_LED_PIN);
    
    while (1) {
        // Poll UART for incoming data
        if (GET_BIT(UCSRA, RXC)) {
            u8 received_byte = UDR;
            Protocol_ProcessByte(received_byte);
        }
        
        // Periodic tasks
        Update_Sensors_Periodic();
        
        _delay_ms(1);
    }
    
    return 0;
}

#endif