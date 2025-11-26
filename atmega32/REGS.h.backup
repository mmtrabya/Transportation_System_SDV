/*
 * REGS.h
 * AVR ATmega32 Register Definitions
 * Created: 9/30/2025 12:36:47 PM
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 * CORRECTED: Fixed Timer1 register definitions
 */ 

#ifndef REGS_H_
#define REGS_H_

/*********************************************************************************************/

/* DIO_Registers */

// DDR_Adresss
#define  DDRA  (*(volatile u8*)0X3A)
#define  DDRB  (*(volatile u8*)0x37)
#define  DDRC  (*(volatile u8*)0x34)
#define  DDRD  (*(volatile u8*)0x31)

// PORT_Adresses
#define  PORTA (*(volatile u8*)0x3B)
#define  PORTB (*(volatile u8*)0x38)
#define  PORTC (*(volatile u8*)0x35)
#define  PORTD (*(volatile u8*)0x32)
   
// PIN_Adresses
#define  PINA  (*(volatile u8*)0x39)
#define  PINB  (*(volatile u8*)0x36)
#define  PINC  (*(volatile u8*)0x33)
#define  PIND  (*(volatile u8*)0x30)

/*********************************************************************************************/

/* ADC_Registers */

#define ADMUX          (*(volatile u8*)0x27)
#define REFS1     7
#define REFS0     6
#define ADLAR     5
#define MUX4      4
#define MUX3      3
#define MUX2      2
#define MUX1      1 
#define MUX0      0 

#define ADCSRA         (*(volatile u8*)0x26)
#define ADEN      7
#define ADSC      6 
#define ADATE     5
#define ADIF      4
#define ADIE      3
#define ADPS2     2 
#define ADPS1     1
#define ADPS0     0

#define ADCL_U16        (*(volatile u16*)0x24)

#define SFIOR           (*(volatile u8*)0x50)
#define ADTS2     7 
#define ADTS1     6
#define ADTS0     5

/*********************************************************************************************/

/* GIE_Registers */

#define  SREG     (*(volatile u8*)0x5F)
#define  I        7

/*********************************************************************************************/

/* EXIT_Registers */

#define MCUCR  (*(volatile u8*)0x55)
#define ISC11    3
#define ISC10    2
#define ISC01    1 
#define ISC00    0
  
#define MCUCSR (*(volatile u8*)0x54)
#define ISC2     6

#define GICR   (*(volatile u8*)0x5B)
#define INT2     5
#define INT0     6
#define INT1     7

/*********************************************************************************************/

/* Timer 0 */
#define TCNT0   (*(volatile unsigned char*)0x52)
#define TCCR0   (*(volatile unsigned char*)0x53)
/* TCCR0 */
#define FOC0    7
#define WGM00   6
#define COM01   5
#define COM00   4
#define WGM01   3
#define CS02    2
#define CS01    1
#define CS00    0

#define OCR0    (*(volatile unsigned char*)0x5C)

/*********************************************************************************************/

/* TIMER1_Registers - CORRECTED */

#define    TCCR1A   (*(volatile u8*)0X4F)
#define    COM1A1      7
#define    COM1A0      6
#define    COM1B1      5
#define    COM1B0      4
#define    FOC1A       3
#define    FOC1B       2 
#define    WGM11       1
#define    WGM10       0

#define    TCCR1B   (*(volatile u8*)0X4E) 
#define    ICNC1       7
#define    ICES1       6
#define    WGM13       4
#define    WGM12       3
#define    CS12        2
#define    CS11        1
#define    CS10        0

/* FIXED: Proper 16-bit register definitions for ultrasonic sensor */
#define    TCNT1    (*(volatile u16*)0X4C)   // 16-bit Timer Counter
#define    OCR1A    (*(volatile u16*)0X4A)   // 16-bit Output Compare A
#define    OCR1B    (*(volatile u16*)0X48)   // 16-bit Output Compare B
#define    ICR1     (*(volatile u16*)0X46)   // 16-bit Input Capture Register

/* 8-bit byte access (optional - for low-level control) */
#define    TCNT1L   (*(volatile u8*)0X4C)    // Low byte only
#define    TCNT1H   (*(volatile u8*)0X4D)    // High byte only
#define    OCR1AL   (*(volatile u8*)0X4A)    // Low byte only
#define    OCR1AH   (*(volatile u8*)0X4B)    // High byte only
#define    OCR1BL   (*(volatile u8*)0X48)    // Low byte only
#define    OCR1BH   (*(volatile u8*)0X49)    // High byte only
#define    ICR1L    (*(volatile u8*)0X46)    // Low byte only
#define    ICR1H    (*(volatile u8*)0X47)    // High byte only

/*********************************************************************************************/

/* Shared Timer Registers (TIMSK and TIFR) */

#define TIMSK   (*(volatile u8*)0X59)
/* TIMSK Bits */
#define OCIE2   7
#define TOIE2   6
#define TICIE1  5
#define OCIE1A  4
#define OCIE1B  3
#define TOIE1   2
#define OCIE0   1
#define TOIE0   0

#define TIFR    (*(volatile u8*)0X58)
/* TIFR Bits */
#define OCF2    7
#define TOV2    6
#define ICF1    5
#define OCF1A   4
#define OCF1B   3
#define TOV1    2
#define OCF0    1
#define TOV0    0

/*********************************************************************************************/

/* Other Shared Registers */

#define TWCR    (*(volatile unsigned char*)0x56)
#define SPMCR   (*(volatile unsigned char*)0x57)

/*********************************************************************************************/

/* WDT_Registers */

#define   WDTCR  (*(volatile u8*)0X41)
#define   WDTOE    4
#define   WDE      3
#define   WDP2     2
#define   WDP1     1
#define   WDP0     0

/*********************************************************************************************/

/* UART_Registers */

#define   UDR    (*(volatile u8*)0X2C)    

#define   UCSRA  (*(volatile u8*)0X2B) 
#define   RXC      7                        
#define   TXC      6                   
#define   UDRE     5                   
#define   FE       4                 
#define   DOR      3                  
#define   PE       2                 
#define   U2X      1                  
#define   MPCM     0                  

#define   UCSRB  (*(volatile u8*)0X2A) 
#define   RXCIE    7                     
#define   TXCIE    6                    
#define   UDRIE    5                    
#define   RXEN     4                   
#define   TXEN     3                   
#define   UCSZ2    2                    
#define   RXB8     1                   
#define   TXB8     0 

#define   UCSRC  (*(volatile u8*)0X40) 
#define   URSEL    7                    
#define   UMSEL    6                    
#define   UMP1     5                   
#define   UMP0     4                   
#define   USBS     3                   
#define   UCSZ1    2                    
#define   UCSZ0    1                    
#define   UCPOL    0   

#define   UBRRL  (*(volatile u8*)0X29)                           
#define   UBRR     103        

/******************************************************************************/

/* SPI */

/* SPI Control Register */
#define SPCR       (*(volatile unsigned char*)0x2D)
/* SPI Status Register */
#define SPSR       (*(volatile unsigned char*)0x2E)
/* SPI I/O Data Register */
#define SPDR       (*(volatile unsigned char*)0x2F)

/* SPI Status Register - SPSR */
#define    SPIF         7
#define    WCOL         6
#define    SPI2X        0

/* SPI Control Register - SPCR */
#define    SPIE         7
#define    SPE          6
#define    DORD         5
#define    MSTR         4
#define    CPOL         3
#define    CPHA         2
#define    SPR1         1
#define    SPR0         0

/****************************** EEPROM Control Register ****************************/

/* EEPROM Control Register */
#define EECR	(*(volatile unsigned char*)0x3C)

#define    EERIE        3
#define    EEMWE        2
#define    EEWE         1
#define    EERE         0

/* EEPROM Data Register */
#define EEDR	(*(volatile unsigned char*)0x3D)

/* EEPROM Address Register */
#define EEAR	(*(volatile unsigned short*)0x3E)
#define EEARL	(*(volatile unsigned char*)0x3E)
#define EEARH	(*(volatile unsigned char*)0x3F)

/****************************** TWI (I2C) Registers ****************************/

/* TWI stands for "Two Wire Interface" or "TWI Was I2C(tm)" */
#define TWBR    (*(volatile unsigned char*)0x20)
#define TWSR    (*(volatile unsigned char*)0x21)
#define TWAR    (*(volatile unsigned char*)0x22)
#define TWDR    (*(volatile unsigned char*)0x23)

/* SPMCR */
#define SPMIE   7
#define RWWSB   6
/* bit 5 reserved */
#define RWWSRE  4
#define BLBSET  3
#define PGWRT   2
#define PGERS   1
#define SPMEN   0

/* TWCR */
#define TWINT   7
#define TWEA    6
#define TWSTA   5
#define TWSTO   4
#define TWWC    3
#define TWEN    2
/* bit 1 reserved */
#define TWIE    0

/* TWAR */
#define TWA6    7
#define TWA5    6
#define TWA4    5
#define TWA3    4
#define TWA2    3
#define TWA1    2
#define TWA0    1
#define TWGCE   0

/* TWSR */
#define TWS7    7
#define TWS6    6
#define TWS5    5
#define TWS4    4
#define TWS3    3
/* bit 2 reserved */
#define TWPS1   1
#define TWPS0   0

/*********************************************************************************/

/* Interrupt vectors */
/* External Interrupt Request 0 */
#define INT0_vect			    __vector_1
/* External Interrupt Request 1 */
#define INT1_vect			    __vector_2
/* External Interrupt Request 2 */
#define INT2_vect			    __vector_3
/* Timer/Counter2 Compare Match */
#define TIMER2_COMP_vect		__vector_4
/* Timer/Counter2 Overflow */
#define TIMER2_OVF_vect			__vector_5
/* Timer/Counter1 Capture Event */
#define TIMER1_ICU_vect		    __vector_6
/* Timer/Counter1 Compare Match A */
#define TIMER1_OCA_vect		    __vector_7
/* Timer/Counter1 Compare Match B */
#define TIMER1_OCB_vect		    __vector_8
/* Timer/Counter1 Overflow */
#define TIMER1_OVF_vect			__vector_9
/* Timer/Counter0 Compare Match */
#define TIMER0_OC_vect	    	__vector_10
/* Timer/Counter0 Overflow */
#define TIMER0_OV_vect			__vector_11
/* Serial Transfer Complete */
#define SPI_STC_vect			__vector_12
/* USART, Rx Complete */
#define UART_RX_vect			__vector_13
/* USART Data Register Empty */
#define UART_UDRE_vect			__vector_14
/* USART, Tx Complete */
#define UART_TX_vect			__vector_15
/* ADC Conversion Complete */
#define ADC_vect			    __vector_16
/* EEPROM Ready */
#define EE_RDY_vect			    __vector_17
/* Analog Comparator */
#define ANA_COMP_vect			__vector_18
/* 2-wire Serial Interface */
#define TWI_vect			    __vector_19
/* Store Program Memory Ready */
#define SPM_RDY_vect			__vector_20

#define BAD_vect        __vector_default

/*interrupt functions*/

# define sei()   __asm__ __volatile__ ("sei" ::)
# define cli()   __asm__ __volatile__ ("cli" ::)
# define reti()  __asm__ __volatile__ ("reti" ::)
# define ret()   __asm__ __volatile__ ("ret" ::)

#  define ISR_NOBLOCK    __attribute__((interrupt))
#  define ISR_NAKED      __attribute__((naked))


#  define ISR(vector,...)            \
void vector (void) __attribute__ ((signal))__VA_ARGS__ ; \
void vector (void)

#endif /* REGS_H_ */