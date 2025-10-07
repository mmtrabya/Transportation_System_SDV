#include <avr/io.h>
#include <util/delay.h>

int main(void) {
    DDRB |= (1 << PB0);  // LED on PB0
    
    while(1) {
        PORTB ^= (1 << PB0);  // Toggle LED
        _delay_ms(500);        // 500ms = visible blink
    }
}