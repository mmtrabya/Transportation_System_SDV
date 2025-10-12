/*
 * SPI.h - Enhanced SPI Driver for AVR ATmega32
 * 
 * Features:
 * - Master and Slave mode support
 * - Configurable clock speed (optimized for 16MHz F_CPU)
 * - Configurable SPI modes (0-3)
 * - Error detection and handling
 * - Multi-slave support with custom CS pins
 * - Buffer transfer with NULL pointer protection
 * 
 * F_CPU: 16MHz (16000000UL)
 * 
 * Clock Speed Table @ 16MHz:
 * - DIV2   -> 8 MHz   (1.0 μs/byte)  - Maximum speed
 * - DIV4   -> 4 MHz   (2.0 μs/byte)  - Recommended default
 * - DIV8   -> 2 MHz   (4.0 μs/byte)  - Safe for most devices
 * - DIV16  -> 1 MHz   (8.0 μs/byte)  - Conservative/Testing
 * - DIV32  -> 500 kHz (16.0 μs/byte) - Long cables
 * - DIV64  -> 250 kHz (32.0 μs/byte) - SD card init
 * - DIV128 -> 125 kHz (64.0 μs/byte) - Maximum compatibility
 * 
 * Created: 10/4/2025
 * Author: MAHMOUD MAHGOUB
 * Updated: Optimized for 16MHz operation with enhanced features
 */

#ifndef SPI_H_
#define SPI_H_

#include "../../REGS.h"
#include "../../STD_TYPES.h"

/*********************************************************************************************/
/*                                    PIN DEFINITIONS                                        */
/*********************************************************************************************/

#define SPI_SCK   7    // Port B, Pin 7 - Serial Clock
#define SPI_MISO  6    // Port B, Pin 6 - Master In Slave Out
#define SPI_MOSI  5    // Port B, Pin 5 - Master Out Slave In
#define SPI_SS    4    // Port B, Pin 4 - Slave Select

/*********************************************************************************************/
/*                                   CONFIGURATION MACROS                                    */
/*********************************************************************************************/

#define SPI_DUMMY_BYTE  0xFF    // Dummy byte for receive operations
#define DEFAULT_ACK     0xFF    // Default acknowledgment byte

/*********************************************************************************************/
/*                              SPI CLOCK RATE OPTIONS @ 16MHz                               */
/*********************************************************************************************/

typedef enum {
    SPI_CLOCK_DIV4    = 0,  // F_CPU/4   = 4 MHz   - Recommended default
    SPI_CLOCK_DIV16   = 1,  // F_CPU/16  = 1 MHz   - Safe/testing
    SPI_CLOCK_DIV64   = 2,  // F_CPU/64  = 250 kHz - SD card init
    SPI_CLOCK_DIV128  = 3,  // F_CPU/128 = 125 kHz - Max compatibility
    SPI_CLOCK_DIV2    = 4,  // F_CPU/2   = 8 MHz   - Maximum speed
    SPI_CLOCK_DIV8    = 5,  // F_CPU/8   = 2 MHz   - Most devices
    SPI_CLOCK_DIV32   = 6,  // F_CPU/32  = 500 kHz - Long cables
} SPI_ClockDiv_t;

/*********************************************************************************************/
/*                                  SPI MODE OPTIONS                                         */
/*********************************************************************************************/

typedef enum {
    SPI_MODE0 = 0,  // CPOL=0, CPHA=0 (Most common - idle low, sample rising)
    SPI_MODE1 = 1,  // CPOL=0, CPHA=1 (Idle low, sample falling)
    SPI_MODE2 = 2,  // CPOL=1, CPHA=0 (Idle high, sample falling)
    SPI_MODE3 = 3,  // CPOL=1, CPHA=1 (Idle high, sample rising)
} SPI_Mode_t;

/*********************************************************************************************/
/*                               DATA ORDER OPTIONS                                          */
/*********************************************************************************************/

typedef enum {
    SPI_MSB_FIRST = 0,  // Most Significant Bit first (default)
    SPI_LSB_FIRST = 1,  // Least Significant Bit first
} SPI_DataOrder_t;

/*********************************************************************************************/
/*                            SPI CONFIGURATION STRUCTURE                                    */
/*********************************************************************************************/

typedef struct {
    SPI_Mode_t mode;              // SPI mode (0-3)
    SPI_ClockDiv_t clockDiv;      // Clock divider
    SPI_DataOrder_t dataOrder;    // Data order (MSB/LSB first)
} SPI_Config_t;

/*********************************************************************************************/
/*                           INITIALIZATION FUNCTION PROTOTYPES                              */
/*********************************************************************************************/

/*
 * Initialize SPI as Master with default settings
 * Default: Mode 0, Clock = F_CPU/16 (1MHz @ 16MHz), MSB First
 * 
 * This is a safe default suitable for most applications and testing.
 */
void SPI_vInitMaster(void);

/*
 * Initialize SPI as Master with custom configuration structure
 * 
 * Parameters:
 *   config: Pointer to SPI_Config_t structure containing:
 *           - mode: SPI mode (0-3)
 *           - clockDiv: Clock divider
 *           - dataOrder: MSB/LSB first
 * 
 * Example:
 *   SPI_Config_t cfg = {SPI_MODE0, SPI_CLOCK_DIV4, SPI_MSB_FIRST};
 *   SPI_vInitMasterConfig(&cfg);
 */
void SPI_vInitMasterConfig(const SPI_Config_t* config);

/*
 * Initialize SPI as Master with individual parameters
 * 
 * Parameters:
 *   mode: SPI mode (0-3)
 *   clockDiv: Clock divider (see SPI_ClockDiv_t for options)
 * 
 * Example:
 *   SPI_vInitMasterEx(SPI_MODE0, SPI_CLOCK_DIV4);  // 4MHz, Mode 0
 */
void SPI_vInitMasterEx(SPI_Mode_t mode, SPI_ClockDiv_t clockDiv);

/*
 * Initialize SPI as Slave with default settings
 * Default: Mode 0, MSB First
 */
void SPI_vInitSlave(void);

/*
 * Initialize SPI as Slave with custom mode
 * 
 * Parameters:
 *   mode: SPI mode (0-3)
 */
void SPI_vInitSlaveEx(SPI_Mode_t mode);

/*********************************************************************************************/
/*                           DATA TRANSFER FUNCTION PROTOTYPES                               */
/*********************************************************************************************/

/*
 * Transmit and receive a byte via SPI (blocking)
 * 
 * Parameters:
 *   data: Byte to transmit
 * 
 * Returns:
 *   Received byte from slave device
 * 
 * Note: This function blocks until transfer is complete
 *       Transfer time @ 16MHz: 1μs (DIV2) to 64μs (DIV128) per byte
 */
u8 SPI_ui8TransmitRecive(u8 data);

/*
 * Transmit multiple bytes via SPI (blocking)
 * 
 * Parameters:
 *   pData: Pointer to data buffer to transmit
 *   length: Number of bytes to transmit
 * 
 * Note: Received data is discarded. NULL pointer safe.
 * 
 * Example:
 *   u8 cmd[] = {0x03, 0x00, 0x10};
 *   SPI_vTransmitBuffer(cmd, 3);
 */
void SPI_vTransmitBuffer(const u8* pData, u16 length);

/*
 * Receive multiple bytes via SPI (blocking)
 * 
 * Parameters:
 *   pData: Pointer to buffer where received data will be stored
 *   length: Number of bytes to receive
 * 
 * Note: Sends dummy bytes (0xFF) to clock in data. NULL pointer safe.
 * 
 * Example:
 *   u8 rxData[10];
 *   SPI_vReceiveBuffer(rxData, 10);
 */
void SPI_vReceiveBuffer(u8* pData, u16 length);

/*
 * Transfer multiple bytes (transmit and receive simultaneously)
 * 
 * Parameters:
 *   pTxData: Pointer to transmit buffer
 *   pRxData: Pointer to receive buffer
 *   length: Number of bytes to transfer
 * 
 * Note: Both buffers must be at least 'length' bytes. NULL pointer safe.
 * 
 * Example:
 *   u8 txBuf[4] = {0x01, 0x02, 0x03, 0x04};
 *   u8 rxBuf[4];
 *   SPI_vTransferBuffer(txBuf, rxBuf, 4);
 */
void SPI_vTransferBuffer(const u8* pTxData, u8* pRxData, u16 length);

/*********************************************************************************************/
/*                        SLAVE SELECT CONTROL FUNCTION PROTOTYPES                           */
/*********************************************************************************************/

/*
 * Select slave device on default SS pin (PB4)
 * Pulls SS pin LOW to activate slave
 * 
 * Call this before starting SPI transaction
 */
void SPI_vSlaveSelect(void);

/*
 * Deselect slave device on default SS pin (PB4)
 * Pulls SS pin HIGH to deactivate slave
 * 
 * Call this after completing SPI transaction
 */
void SPI_vSlaveDeselect(void);

/*
 * Select custom slave device on any pin
 * Useful for multi-slave systems
 * 
 * Parameters:
 *   port: Pointer to PORT register (e.g., &PORTC)
 *   pin: Pin number (0-7)
 * 
 * Example:
 *   DDRC |= (1<<2);  // Set PC2 as output
 *   SPI_vCustomSlaveSelect(&PORTC, 2);  // Select device on PC2
 */
void SPI_vCustomSlaveSelect(volatile u8* port, u8 pin);

/*
 * Deselect custom slave device on any pin
 * 
 * Parameters:
 *   port: Pointer to PORT register (e.g., &PORTC)
 *   pin: Pin number (0-7)
 * 
 * Example:
 *   SPI_vCustomSlaveDeselect(&PORTC, 2);  // Deselect device on PC2
 */
void SPI_vCustomSlaveDeselect(volatile u8* port, u8 pin);

/*********************************************************************************************/
/*                        STATUS AND CONTROL FUNCTION PROTOTYPES                             */
/*********************************************************************************************/

/*
 * Check if SPI is busy transmitting
 * 
 * Returns:
 *   1 if transmission in progress
 *   0 if ready for next transfer
 */
u8 SPI_u8IsBusy(void);

/*
 * Check for SPI error (write collision)
 * 
 * Returns:
 *   1 if write collision detected
 *   0 if no error
 * 
 * Note: Write collision occurs when SPDR is written before previous transfer completes
 */
u8 SPI_u8GetError(void);

/*
 * Clear SPI error flags
 * Clears write collision flag (WCOL)
 */
void SPI_vClearError(void);

/*
 * Set SPI clock speed dynamically
 * 
 * Parameters:
 *   clockDiv: Clock divider (see SPI_ClockDiv_t)
 * 
 * Note: Can be called at runtime to change speed for different devices
 * 
 * Example:
 *   SPI_vSetClockSpeed(SPI_CLOCK_DIV2);  // Switch to 8MHz
 */
void SPI_vSetClockSpeed(SPI_ClockDiv_t clockDiv);

/*
 * Set SPI mode dynamically
 * 
 * Parameters:
 *   mode: SPI mode (0-3)
 * 
 * Example:
 *   SPI_vSetMode(SPI_MODE3);  // Switch to Mode 3
 */
void SPI_vSetMode(SPI_Mode_t mode);

/*
 * Set data order (MSB/LSB first)
 * 
 * Parameters:
 *   order: Data order (see SPI_DataOrder_t)
 * 
 * Example:
 *   SPI_vSetDataOrder(SPI_LSB_FIRST);
 */
void SPI_vSetDataOrder(SPI_DataOrder_t order);

/*
 * Enable SPI peripheral
 */
void SPI_vEnable(void);

/*
 * Disable SPI peripheral
 */
void SPI_vDisable(void);

/*
 * Get current clock speed setting
 * 
 * Returns:
 *   Current clock divider value (SPI_ClockDiv_t)
 */
u8 SPI_u8GetClockSpeed(void);

/*
 * Get current SPI mode setting
 * 
 * Returns:
 *   Current SPI mode (0-3)
 */
u8 SPI_u8GetMode(void);

/*********************************************************************************************/
/*                                   HELPER MACROS                                           */
/*********************************************************************************************/

/* Quick slave select macros (for time-critical applications) */
#define SPI_SS_LOW()   (PORTB &= ~(1<<SPI_SS))
#define SPI_SS_HIGH()  (PORTB |= (1<<SPI_SS))

/* Custom CS control macros */
#define SPI_CS_LOW(port, pin)   ((port) &= ~(1<<(pin)))
#define SPI_CS_HIGH(port, pin)  ((port) |= (1<<(pin)))

/* Check if transmission is complete */
#define SPI_IS_TRANSFER_COMPLETE()  (SPSR & (1<<SPIF))

/* Check for write collision error */
#define SPI_HAS_ERROR()  (SPSR & (1<<WCOL))

/*********************************************************************************************/
/*                      RECOMMENDED DEVICE CONFIGURATIONS @ 16MHz                            */
/*********************************************************************************************/

/*
 * QUICK REFERENCE FOR COMMON DEVICES:
 * 
 * Device              | Clock Divider | Mode   | Actual Speed | Notes
 * --------------------|---------------|--------|--------------|-------------------------
 * SD Card (init)      | DIV64         | MODE0  | 250 kHz      | Required for init
 * SD Card (data)      | DIV4          | MODE0  | 4 MHz        | After initialization
 * ESP32 SPI Slave     | DIV4          | MODE0  | 4 MHz        | Reliable speed
 * NRF24L01+           | DIV4          | MODE0  | 4 MHz        | Wireless module
 * W5500 Ethernet      | DIV2          | MODE0  | 8 MHz        | Maximum ATmega speed
 * MAX7219 LED         | DIV2          | MODE0  | 8 MHz        | Fast display updates
 * 74HC595 Shift Reg   | DIV2          | MODE0  | 8 MHz        | Shift register
 * MCP3008 ADC         | DIV8          | MODE0  | 2 MHz        | Safety margin @ 5V
 * 25LC256 EEPROM      | DIV4          | MODE0  | 4 MHz        | 32KB EEPROM
 * MCP2515 CAN         | DIV4          | MODE0  | 4 MHz        | CAN controller
 * PN532 NFC           | DIV4          | MODE0  | 4 MHz        | NFC reader
 * MPU9250 (SPI)       | DIV16         | MODE0  | 1 MHz        | IMU sensor
 * BME280              | DIV4          | MODE0  | 4 MHz        | Environmental sensor
 * Nokia 5110 LCD      | DIV4          | MODE0  | 4 MHz        | PCD8544 controller
 * 
 * DEFAULT RECOMMENDATION: DIV4 (4MHz), MODE0 - works with 90% of devices
 */

/*********************************************************************************************/
/*                                  USAGE EXAMPLES                                           */
/*********************************************************************************************/

/*
 * EXAMPLE 1: Basic single byte transfer
 * 
 *   SPI_vInitMaster();
 *   SPI_vSlaveSelect();
 *   u8 response = SPI_ui8TransmitRecive(0xAA);
 *   SPI_vSlaveDeselect();
 * 
 * 
 * EXAMPLE 2: Multi-byte transfer with custom speed
 * 
 *   u8 txData[4] = {0x01, 0x02, 0x03, 0x04};
 *   u8 rxData[4];
 *   
 *   SPI_vInitMasterEx(SPI_MODE0, SPI_CLOCK_DIV4);  // 4MHz
 *   SPI_vSlaveSelect();
 *   SPI_vTransferBuffer(txData, rxData, 4);
 *   SPI_vSlaveDeselect();
 * 
 * 
 * EXAMPLE 3: Multiple devices with different settings
 * 
 *   // Initialize
 *   SPI_vInitMaster();
 *   DDRC |= (1<<0) | (1<<1);  // CS pins
 *   PORTC |= (1<<0) | (1<<1); // Deselect all
 *   
 *   // Fast device (8MHz)
 *   SPI_vSetClockSpeed(SPI_CLOCK_DIV2);
 *   SPI_vCustomSlaveSelect(&PORTC, 0);
 *   SPI_ui8TransmitRecive(0xFF);
 *   SPI_vCustomSlaveDeselect(&PORTC, 0);
 *   
 *   // Slower device (2MHz)
 *   SPI_vSetClockSpeed(SPI_CLOCK_DIV8);
 *   SPI_vCustomSlaveSelect(&PORTC, 1);
 *   SPI_ui8TransmitRecive(0xAA);
 *   SPI_vCustomSlaveDeselect(&PORTC, 1);
 * 
 * 
 * EXAMPLE 4: SD Card initialization sequence
 * 
 *   // Slow speed for init
 *   SPI_vInitMasterEx(SPI_MODE0, SPI_CLOCK_DIV64);  // 250kHz
 *   
 *   // Send 80 clock pulses with CS high
 *   SPI_vSlaveDeselect();
 *   for(u8 i=0; i<10; i++) {
 *       SPI_ui8TransmitRecive(0xFF);
 *   }
 *   
 *   // Initialize card...
 *   
 *   // Switch to fast mode for data transfer
 *   SPI_vSetClockSpeed(SPI_CLOCK_DIV4);  // 4MHz
 * 
 * 
 * EXAMPLE 5: Error handling
 * 
 *   SPI_vInitMaster();
 *   SPI_vSlaveSelect();
 *   
 *   SPI_ui8TransmitRecive(0xAA);
 *   
 *   if(SPI_u8GetError()) {
 *       // Handle write collision
 *       SPI_vClearError();
 *   }
 *   
 *   SPI_vSlaveDeselect();
 * 
 * 
 * EXAMPLE 6: Using configuration structure
 * 
 *   SPI_Config_t config = {
 *       .mode = SPI_MODE0,
 *       .clockDiv = SPI_CLOCK_DIV4,
 *       .dataOrder = SPI_MSB_FIRST
 *   };
 *   
 *   SPI_vInitMasterConfig(&config);
 */

/*********************************************************************************************/
/*                              PERFORMANCE METRICS @ 16MHz                                  */
/*********************************************************************************************/

/*
 * SINGLE BYTE TRANSFER TIMES:
 * 
 * DIV2   (8 MHz):   1.0 μs per byte
 * DIV4   (4 MHz):   2.0 μs per byte
 * DIV8   (2 MHz):   4.0 μs per byte
 * DIV16  (1 MHz):   8.0 μs per byte
 * DIV32  (500 kHz): 16.0 μs per byte
 * DIV64  (250 kHz): 32.0 μs per byte
 * DIV128 (125 kHz): 64.0 μs per byte
 * 
 * 
 * BULK TRANSFER EXAMPLES:
 * 
 * 512 bytes (SD card sector):
 * - DIV2:  0.512 ms (1000 KB/s)
 * - DIV4:  1.024 ms (500 KB/s)
 * - DIV8:  2.048 ms (250 KB/s)
 * - DIV16: 4.096 ms (125 KB/s)
 * 
 * 1024 bytes (display buffer):
 * - DIV2:  1.024 ms (1000 KB/s)
 * - DIV4:  2.048 ms (500 KB/s)
 * - DIV8:  4.096 ms (250 KB/s)
 * - DIV16: 8.192 ms (125 KB/s)
 */

/*********************************************************************************************/
/*                                   TIMING NOTES                                            */
/*********************************************************************************************/

/*
 * IMPORTANT TIMING CONSIDERATIONS:
 * 
 * 1. CS Setup Time:
 *    Some devices require delay between CS assert and first clock
 *    Solution: Add _delay_us(1-10) after SPI_vSlaveSelect()
 * 
 * 2. CS Hold Time:
 *    Some devices need CS held after last clock
 *    Solution: Add _delay_us(1-10) before SPI_vSlaveDeselect()
 * 
 * 3. Inter-byte Delay:
 *    Some slow devices need time between bytes
 *    Solution: Add delays in buffer transfer loops
 * 
 * 4. Cable Length Impact:
 *    - < 10cm:    All speeds work
 *    - 10-30cm:   DIV4 (4MHz) or slower recommended
 *    - 30-100cm:  DIV8 (2MHz) or slower recommended
 *    - > 100cm:   DIV16 (1MHz) or slower + proper termination
 * 
 * 5. Noise Considerations:
 *    - Use shorter cables when possible
 *    - Add 100nF capacitor near each SPI device
 *    - Keep SPI traces short and together
 *    - Use ground plane on PCB
 *    - Consider shielded cables for long runs
 */

/*********************************************************************************************/
/*                                 TROUBLESHOOTING GUIDE                                     */
/*********************************************************************************************/

/*
 * PROBLEM: Device not responding
 * SOLUTIONS:
 *   1. Reduce clock speed -> Try SPI_vSetClockSpeed(SPI_CLOCK_DIV16)
 *   2. Verify SPI mode -> Try MODE0 and MODE3
 *   3. Check CS timing -> Add _delay_us(10) after select
 *   4. Verify MOSI/MISO not swapped
 *   5. Check power supply voltage (3.3V vs 5V)
 * 
 * 
 * PROBLEM: Corrupted data
 * SOLUTIONS:
 *   1. Reduce clock speed
 *   2. Shorten cable length
 *   3. Add 100nF bypass capacitor near device
 *   4. Improve grounding
 *   5. Check for EMI sources nearby
 * 
 * 
 * PROBLEM: Intermittent communication
 * SOLUTIONS:
 *   1. Check power supply stability
 *   2. Add delays between transactions
 *   3. Reduce clock speed
 *   4. Check for loose connections
 *   5. Verify CS pin control
 * 
 * 
 * PROBLEM: Write collision error (WCOL)
 * SOLUTIONS:
 *   1. Ensure previous transfer complete before next write
 *   2. Use SPI_u8IsBusy() to check status
 *   3. Clear error with SPI_vClearError()
 *   4. Avoid back-to-back transfers without checking SPIF
 */

/*********************************************************************************************/
/*                              SPEED SELECTION GUIDE                                        */
/*********************************************************************************************/

/*
 * WHEN TO USE EACH SPEED @ 16MHz:
 * 
 * DIV2 (8 MHz) - USE FOR:
 *   ✓ On-board communication (short traces)
 *   ✓ High-speed devices (W5500, 74HC595, MAX7219)
 *   ✓ Low-noise environments
 *   ✓ Production-tested systems
 *   ✗ Long cables (>10cm)
 *   ✗ Noisy environments
 *   ✗ Breadboard prototypes
 * 
 * DIV4 (4 MHz) - USE FOR: [RECOMMENDED DEFAULT]
 *   ✓ Most general-purpose devices
 *   ✓ SD cards (after initialization)
 *   ✓ Wireless modules (NRF24L01+, ESP32)
 *   ✓ Development and testing
 *   ✓ Cable lengths up to 30cm
 *   ✓ Good balance of speed and reliability
 * 
 * DIV8 (2 MHz) - USE FOR:
 *   ✓ Sensitive analog devices (ADCs)
 *   ✓ Long cables (30-100cm)
 *   ✓ High-EMI environments
 *   ✓ Battery-powered devices (lower EMI)
 * 
 * DIV16 (1 MHz) - USE FOR:
 *   ✓ Unknown devices (testing)
 *   ✓ Very long cables (>100cm)
 *   ✓ Extreme noise environments
 *   ✓ Debugging with oscilloscope
 *   ✓ Multi-drop SPI buses
 * 
 * DIV64/128 (250/125 kHz) - USE FOR:
 *   ✓ SD card initialization ONLY
 *   ✓ Device discovery/enumeration
 *   ✓ Maximum compatibility testing
 */
#endif /* SPI_H_ */