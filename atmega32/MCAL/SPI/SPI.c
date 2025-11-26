/*
 * SPI.c - Enhanced SPI Driver Implementation for AVR ATmega32
 * 
 * Features:
 * - Master and Slave mode support
 * - Configurable clock speed and SPI modes
 * - Buffer transfer functions with error checking
 * - Slave Select control
 * - Optimized for F_CPU = 16MHz
 * 
 * Created: 10/4/2025
 * Author: MAHMOUD MAHGOUP
 * Updated: Optimized for 16MHz operation
 */

#include "SPI.h"
#include "../../REGS.h"

/*********************************************************************************************/
/*                          BASIC INITIALIZATION FUNCTIONS                                   */
/*********************************************************************************************/

void SPI_vInitMaster(void)
{
    // Set MOSI, SCK, and SS as outputs
    DDRB |= (1<<SPI_MOSI) | (1<<SPI_SCK) | (1<<SPI_SS);
    
    // Set MISO as input (explicitly for clarity)
    DDRB &= ~(1<<SPI_MISO);
    
    // Pull SS high initially (slave deselected)
    PORTB |= (1<<SPI_SS);
    
    // Enable SPI, Master mode, Clock = F_CPU/16 = 1MHz (safe default at 16MHz)
    // SPE: SPI Enable
    // MSTR: Master mode
    // SPR0: Clock divider bit 0 (F_CPU/16 when SPR0=1, SPR1=0, SPI2X=0)
    SPCR = (1<<SPE) | (1<<MSTR) | (1<<SPR0);
}

void SPI_vInitMasterEx(SPI_Mode_t mode, SPI_ClockDiv_t clockDiv)
{
    // Set MOSI, SCK, and SS as outputs
    DDRB |= (1<<SPI_MOSI) | (1<<SPI_SCK) | (1<<SPI_SS);
    
    // Set MISO as input
    DDRB &= ~(1<<SPI_MISO);
    
    // Pull SS high initially (slave deselected)
    PORTB |= (1<<SPI_SS);
    
    // Start with SPI enabled in Master mode
    SPCR = (1<<SPE) | (1<<MSTR);
    
    // Configure SPI mode (CPOL and CPHA)
    if (mode & 0x02) {
        SPCR |= (1<<CPOL);  // Clock polarity
    }
    if (mode & 0x01) {
        SPCR |= (1<<CPHA);  // Clock phase
    }
    
    // Configure clock divider
    SPSR &= ~(1<<SPI2X);  // Clear double speed bit initially
    
    switch (clockDiv) {
        case SPI_CLOCK_DIV2:   // F_CPU/2 = 8MHz @ 16MHz CPU (fastest)
            SPSR |= (1<<SPI2X);
            break;
            
        case SPI_CLOCK_DIV4:   // F_CPU/4 = 4MHz @ 16MHz CPU (recommended default)
            // SPR1=0, SPR0=0, SPI2X=0
            break;
            
        case SPI_CLOCK_DIV8:   // F_CPU/8 = 2MHz @ 16MHz CPU
            SPCR |= (1<<SPR0);
            SPSR |= (1<<SPI2X);
            break;
            
        case SPI_CLOCK_DIV16:  // F_CPU/16 = 1MHz @ 16MHz CPU (safe)
            SPCR |= (1<<SPR0);
            break;
            
        case SPI_CLOCK_DIV32:  // F_CPU/32 = 500kHz @ 16MHz CPU
            SPCR |= (1<<SPR1);
            SPSR |= (1<<SPI2X);
            break;
            
        case SPI_CLOCK_DIV64:  // F_CPU/64 = 250kHz @ 16MHz CPU (SD init)
            SPCR |= (1<<SPR1);
            break;
            
        case SPI_CLOCK_DIV128: // F_CPU/128 = 125kHz @ 16MHz CPU (max compatibility)
            SPCR |= (1<<SPR1) | (1<<SPR0);
            break;
            
        default:
            SPCR |= (1<<SPR0);  // Default to F_CPU/16 = 1MHz (safe)
            break;
    }
}

void SPI_vInitMasterConfig(const SPI_Config_t* config)
{
    // Input validation
    if (config == NULL) {
        return;
    }
    
    // Set MOSI, SCK, and SS as outputs
    DDRB |= (1<<SPI_MOSI) | (1<<SPI_SCK) | (1<<SPI_SS);
    
    // Set MISO as input
    DDRB &= ~(1<<SPI_MISO);
    
    // Pull SS high initially (slave deselected)
    PORTB |= (1<<SPI_SS);
    
    // Start with SPI enabled in Master mode
    SPCR = (1<<SPE) | (1<<MSTR);
    
    // Configure data order
    if (config->dataOrder == SPI_LSB_FIRST) {
        SPCR |= (1<<DORD);
    }
    
    // Configure SPI mode
    if (config->mode & 0x02) {
        SPCR |= (1<<CPOL);
    }
    if (config->mode & 0x01) {
        SPCR |= (1<<CPHA);
    }
    
    // Configure clock divider
    SPSR &= ~(1<<SPI2X);
    
    switch (config->clockDiv) {
        case SPI_CLOCK_DIV2:   // 8MHz @ 16MHz
            SPSR |= (1<<SPI2X);
            break;
        case SPI_CLOCK_DIV4:   // 4MHz @ 16MHz (recommended)
            break;
        case SPI_CLOCK_DIV8:   // 2MHz @ 16MHz
            SPCR |= (1<<SPR0);
            SPSR |= (1<<SPI2X);
            break;
        case SPI_CLOCK_DIV16:  // 1MHz @ 16MHz
            SPCR |= (1<<SPR0);
            break;
        case SPI_CLOCK_DIV32:  // 500kHz @ 16MHz
            SPCR |= (1<<SPR1);
            SPSR |= (1<<SPI2X);
            break;
        case SPI_CLOCK_DIV64:  // 250kHz @ 16MHz
            SPCR |= (1<<SPR1);
            break;
        case SPI_CLOCK_DIV128: // 125kHz @ 16MHz
            SPCR |= (1<<SPR1) | (1<<SPR0);
            break;
        default:
            SPCR |= (1<<SPR0);  // Default to 1MHz
            break;
    }
}

void SPI_vInitSlave(void)
{
    // Set MISO as output
    DDRB |= (1<<SPI_MISO);
    
    // Set MOSI, SCK, and SS as inputs (explicit for clarity)
    DDRB &= ~((1<<SPI_MOSI) | (1<<SPI_SCK) | (1<<SPI_SS));
    
    // Enable SPI in slave mode (MSTR bit = 0)
    SPCR = (1<<SPE);
}

void SPI_vInitSlaveEx(SPI_Mode_t mode)
{
    // Set MISO as output
    DDRB |= (1<<SPI_MISO);
    
    // Set MOSI, SCK, and SS as inputs
    DDRB &= ~((1<<SPI_MOSI) | (1<<SPI_SCK) | (1<<SPI_SS));
    
    // Enable SPI in slave mode
    SPCR = (1<<SPE);
    
    // Configure SPI mode
    if (mode & 0x02) {
        SPCR |= (1<<CPOL);
    }
    if (mode & 0x01) {
        SPCR |= (1<<CPHA);
    }
}

/*********************************************************************************************/
/*                          DATA TRANSFER FUNCTIONS                                          */
/*********************************************************************************************/

u8 SPI_ui8TransmitRecive(u8 data)
{
    // Clear any pending collision flag by reading SPSR and SPDR
    volatile u8 dummy;
    if (SPSR & (1<<WCOL)) {
        dummy = SPSR;
        dummy = SPDR;
        (void)dummy; // Suppress unused warning
    }
    
    // Load data into the data register
    SPDR = data;
    
    // Wait for transmission to complete
    // SPIF flag is set when transfer is complete
    while (!(SPSR & (1<<SPIF))) {
        // Blocking wait - consider adding timeout for production code
    }
    
    // Return received data
    return SPDR;
}

void SPI_vTransmitBuffer(const u8* pData, u16 length)
{
    u16 i;
    
    // Input validation
    if (pData == NULL || length == 0) {
        return;
    }
    
    for (i = 0; i < length; i++) {
        SPI_ui8TransmitRecive(pData[i]);
    }
}

void SPI_vReceiveBuffer(u8* pData, u16 length)
{
    u16 i;
    
    // Input validation
    if (pData == NULL || length == 0) {
        return;
    }
    
    for (i = 0; i < length; i++) {
        pData[i] = SPI_ui8TransmitRecive(SPI_DUMMY_BYTE);  // Send dummy byte to clock in data
    }
}

void SPI_vTransferBuffer(const u8* pTxData, u8* pRxData, u16 length)
{
    u16 i;
    
    // Input validation
    if (pTxData == NULL || pRxData == NULL || length == 0) {
        return;
    }
    
    for (i = 0; i < length; i++) {
        pRxData[i] = SPI_ui8TransmitRecive(pTxData[i]);
    }
}

/*********************************************************************************************/
/*                          SLAVE SELECT CONTROL FUNCTIONS                                   */
/*********************************************************************************************/

void SPI_vSlaveSelect(void)
{
    PORTB &= ~(1<<SPI_SS);  // Pull SS low (active)
}

void SPI_vSlaveDeselect(void)
{
    PORTB |= (1<<SPI_SS);   // Pull SS high (inactive)
}

void SPI_vCustomSlaveSelect(volatile u8* port, u8 pin)
{
    if (port != NULL) {
        *port &= ~(1<<pin);  // Pull CS pin low (active)
    }
}

void SPI_vCustomSlaveDeselect(volatile u8* port, u8 pin)
{
    if (port != NULL) {
        *port |= (1<<pin);   // Pull CS pin high (inactive)
    }
}

/*********************************************************************************************/
/*                          STATUS AND CONTROL FUNCTIONS                                     */
/*********************************************************************************************/

u8 SPI_u8IsBusy(void)
{
    // Return 1 if transmission is in progress, 0 if complete
    return !(SPSR & (1<<SPIF));
}

u8 SPI_u8GetError(void)
{
    // Check for write collision error
    return (SPSR & (1<<WCOL)) ? 1 : 0;
}

void SPI_vClearError(void)
{
    // Clear write collision flag by reading SPSR then SPDR
    volatile u8 dummy = SPSR;
    dummy = SPDR;
    (void)dummy; // Suppress unused variable warning
}

void SPI_vSetClockSpeed(SPI_ClockDiv_t clockDiv)
{
    u8 spcr_temp = SPCR;
    u8 spsr_temp = SPSR;
    
    // Clear clock bits
    spcr_temp &= ~((1<<SPR1) | (1<<SPR0));
    spsr_temp &= ~(1<<SPI2X);
    
    switch (clockDiv) {
        case SPI_CLOCK_DIV2:   // 8MHz @ 16MHz
            spsr_temp |= (1<<SPI2X);
            break;
        case SPI_CLOCK_DIV4:   // 4MHz @ 16MHz
            break;
        case SPI_CLOCK_DIV8:   // 2MHz @ 16MHz
            spcr_temp |= (1<<SPR0);
            spsr_temp |= (1<<SPI2X);
            break;
        case SPI_CLOCK_DIV16:  // 1MHz @ 16MHz
            spcr_temp |= (1<<SPR0);
            break;
        case SPI_CLOCK_DIV32:  // 500kHz @ 16MHz
            spcr_temp |= (1<<SPR1);
            spsr_temp |= (1<<SPI2X);
            break;
        case SPI_CLOCK_DIV64:  // 250kHz @ 16MHz
            spcr_temp |= (1<<SPR1);
            break;
        case SPI_CLOCK_DIV128: // 125kHz @ 16MHz
            spcr_temp |= (1<<SPR1) | (1<<SPR0);
            break;
        default:
            spcr_temp |= (1<<SPR0);  // Default to 1MHz
            break;
    }
    
    SPCR = spcr_temp;
    SPSR = spsr_temp;
}

void SPI_vSetMode(SPI_Mode_t mode)
{
    u8 spcr_temp = SPCR;
    
    // Clear mode bits
    spcr_temp &= ~((1<<CPOL) | (1<<CPHA));
    
    // Set new mode
    if (mode & 0x02) {
        spcr_temp |= (1<<CPOL);
    }
    if (mode & 0x01) {
        spcr_temp |= (1<<CPHA);
    }
    
    SPCR = spcr_temp;
}

void SPI_vSetDataOrder(SPI_DataOrder_t order)
{
    if (order == SPI_LSB_FIRST) {
        SPCR |= (1<<DORD);
    } else {
        SPCR &= ~(1<<DORD);
    }
}

void SPI_vEnable(void)
{
    SPCR |= (1<<SPE);
}

void SPI_vDisable(void)
{
    SPCR &= ~(1<<SPE);
}

u8 SPI_u8GetClockSpeed(void)
{
    // Return current clock divider setting
    u8 spr_bits = (SPCR & ((1<<SPR1) | (1<<SPR0))) >> SPR0;
    u8 spi2x_bit = (SPSR & (1<<SPI2X)) ? 1 : 0;
    
    // Decode the speed setting
    if (spi2x_bit) {
        switch (spr_bits) {
            case 0: return SPI_CLOCK_DIV2;   // 8MHz
            case 1: return SPI_CLOCK_DIV8;   // 2MHz
            case 2: return SPI_CLOCK_DIV32;  // 500kHz
            default: return SPI_CLOCK_DIV2;
        }
    } else {
        switch (spr_bits) {
            case 0: return SPI_CLOCK_DIV4;   // 4MHz
            case 1: return SPI_CLOCK_DIV16;  // 1MHz
            case 2: return SPI_CLOCK_DIV64;  // 250kHz
            case 3: return SPI_CLOCK_DIV128; // 125kHz
            default: return SPI_CLOCK_DIV4;
        }
    }
}

u8 SPI_u8GetMode(void)
{
    // Extract and return current SPI mode
    u8 mode = 0;
    if (SPCR & (1<<CPOL)) mode |= 0x02;
    if (SPCR & (1<<CPHA)) mode |= 0x01;
    return mode;
}