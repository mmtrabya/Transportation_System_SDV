/*
 * LCD_I2C_program.c
 *
 * I2C LCD Driver Implementation
 * Uses PCF8574 I2C I/O Expander
 * Compatible with 20x4 LCD displays
 */ 

#define F_CPU 16000000UL
#include <util/delay.h>
#include <avr/io.h>
/* UTILITIES */
#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"
#include "../../MCAL/String/String.h"

/* MCAL */
#include "../../MCAL/TWI/TWI_interface.h"

/* HAL */
#include "LCD_interface.h"
#include "../../CFG/LCD_config.h"
#include "LCD_private.h"

/* Backlight state variable */
static u8 backlightState = (1 << LCD_BL_BIT);

/*
 * Private Function: Write a byte to PCF8574
 */
static void LCD_writeByte(u8 data)
{
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(LCD_I2C_ADDRESS);
    TWI_sendMasterDataByte(data | backlightState);
    TWI_sendStopCondition();
    _delay_us(1);
}

/*
 * Private Function: Generate Enable Pulse
 */
static void LCD_pulseEnable(u8 data)
{
    // EN high
    LCD_writeByte(data | (1 << LCD_EN_BIT));
    _delay_us(1);
    
    // EN low
    LCD_writeByte(data & ~(1 << LCD_EN_BIT));
    _delay_us(50);
}

/*
 * Private Function: Send 4-bit nibble
 */
static void LCD_sendNibble(u8 nibble, u8 mode)
{
    u8 data = 0;
    
    // Set data bits D4-D7
    if (nibble & 0x01) data |= (1 << LCD_D4_BIT);
    if (nibble & 0x02) data |= (1 << LCD_D5_BIT);
    if (nibble & 0x04) data |= (1 << LCD_D6_BIT);
    if (nibble & 0x08) data |= (1 << LCD_D7_BIT);
    
    // Set RS bit (0 for command, 1 for data)
    if (mode == LCD_MODE_DATA)
    {
        data |= (1 << LCD_RS_BIT);
    }
    
    // RW is always 0 (write mode)
    data &= ~(1 << LCD_RW_BIT);
    
    // Send nibble with enable pulse
    LCD_pulseEnable(data);
}

/*
 * Private Function: Send full byte (two nibbles)
 */
static void LCD_sendByte(u8 dataByte, u8 mode)
{
    // Send high nibble
    LCD_sendNibble((dataByte >> 4) & 0x0F, mode);
    
    // Send low nibble
    LCD_sendNibble(dataByte & 0x0F, mode);
}

/*
 * Public Function: Initialize I2C LCD
 */
void LCD_init(void)
{
    // Initialize TWI/I2C Master
    TWI_initMaster();
    
    // Wait for LCD power-up
    _delay_ms(50);
    
    // LCD initialization sequence for 4-bit mode
    // Send 0x03 three times (8-bit mode initialization)
    LCD_sendNibble(0x03, LCD_MODE_COMMAND);
    _delay_ms(5);
    
    LCD_sendNibble(0x03, LCD_MODE_COMMAND);
    _delay_us(150);
    
    LCD_sendNibble(0x03, LCD_MODE_COMMAND);
    _delay_us(150);
    
    // Switch to 4-bit mode
    LCD_sendNibble(0x02, LCD_MODE_COMMAND);
    _delay_us(150);
    
    // Function Set: 4-bit mode, 2 lines, 5x8 font
    LCD_sendCommand(LCD_CMD_4BIT_MODE);
    _delay_us(50);
    
    // Display OFF
    LCD_sendCommand(LCD_CMD_DISPLAY_OFF);
    _delay_us(50);
    
    // Clear Display
    LCD_sendCommand(LCD_CMD_CLEAR);
    _delay_ms(2);
    
    // Entry Mode: Increment cursor, no display shift
    LCD_sendCommand(LCD_CMD_ENTRY_MODE);
    _delay_us(50);
    
    // Display ON, Cursor OFF, Blink OFF
    LCD_sendCommand(LCD_CMD_DISPLAY_ON);
    _delay_us(50);
    
    // Turn on backlight
    LCD_backlightOn();
}

/*
 * Public Function: Send Command to LCD
 */
void LCD_sendCommand(u8 command)
{
    LCD_sendByte(command, LCD_MODE_COMMAND);
    
    // Extra delay for clear and home commands
    if (command == LCD_CMD_CLEAR || command == LCD_CMD_HOME)
    {
        _delay_ms(2);
    }
    else
    {
        _delay_us(50);
    }
}

/*
 * Public Function: Send Character to LCD
 */
void LCD_sendChar(u8 data)
{
    LCD_sendByte(data, LCD_MODE_DATA);
    _delay_us(50);
}

/*
 * Public Function: Write String to LCD
 */
void LCD_writeString(u8* string)
{
    u8 counter = 0;
    
    if (string == NULL)
    {
        return;
    }
    
    while (string[counter] != '\0')
    {
        LCD_sendChar(string[counter]);
        counter++;
    }
}

/*
 * Public Function: Clear Display
 */
void LCD_clear(void)
{
    LCD_sendCommand(LCD_CMD_CLEAR);
    _delay_ms(2);
}

/*
 * Public Function: Write Number to LCD (using String.c)
 */
void LCD_writeNumber(S32 number)
{
    s8 str[12];  // Buffer for number string (max 11 digits + null)
    
    // Convert number to string using String.c function
    NUM_tostring(str, number);
    
    // Display the string
    LCD_writeString((u8*)str);
}

/*
 * Public Function: Write Signed Number to LCD
 */
void LCD_writeSignedNumber(S32 number)
{
    LCD_writeNumber(number);
}

/*
 * Public Function: Set Cursor Position
 * For 20x4 LCD DDRAM addresses:
 * Line 0: 0x00 - 0x13 (0 to 19)
 * Line 1: 0x40 - 0x53 (64 to 83)
 * Line 2: 0x14 - 0x27 (20 to 39)
 * Line 3: 0x54 - 0x67 (84 to 103)
 */
void LCD_goTo(u8 lineNumber, u8 position)
{
    u8 address;
    
    switch (lineNumber)
    {
        case LCD_LINE_0:
            address = position;
            break;
            
        case LCD_LINE_1:
            address = position + 0x40;
            break;
            
        case LCD_LINE_2:
            address = position + 0x14;
            break;
            
        case LCD_LINE_3:
            address = position + 0x54;
            break;
            
        default:
            address = 0;
            break;
    }
    
    // Set DDRAM address command (bit 7 = 1)
    LCD_sendCommand(0x80 | address);
}

/*
 * Public Function: Clear Specific Position
 */
void LCD_clearPosition(u8 lineNumber, u8 position)
{
    LCD_goTo(lineNumber, position);
    LCD_sendChar(' ');
    LCD_goTo(lineNumber, position);
}

/*
 * Public Function: Clear Line
 */
void LCD_clearLine(u8 lineNumber)
{
    u8 i;
    LCD_goTo(lineNumber, 0);
    for (i = 0; i < 20; i++)
    {
        LCD_sendChar(' ');
    }
    LCD_goTo(lineNumber, 0);
}

/*
 * Public Function: Turn Backlight ON
 */
void LCD_backlightOn(void)
{
    backlightState = (1 << LCD_BL_BIT);
    LCD_writeByte(0x00);
}

/*
 * Public Function: Turn Backlight OFF
 */
void LCD_backlightOff(void)
{
    backlightState = 0;
    LCD_writeByte(0x00);
}

/*
 * Public Function: Write Float Number (simple implementation)
 */
void LCD_writeFloat(float number, u8 decimalPlaces)
{
    S32 intPart = (S32)number;
    float fractPart = number - intPart;
    
    // Write integer part
    LCD_writeNumber(intPart);
    
    // Write decimal point
    LCD_sendChar('.');
    
    // Write decimal places
    if (decimalPlaces > 0)
    {
        u8 i;
        for (i = 0; i < decimalPlaces; i++)
        {
            fractPart *= 10;
            u8 digit = (u8)fractPart;
            LCD_sendChar(digit + '0');
            fractPart -= digit;
        }
    }
}

/* ============================================================================
 * TEST FUNCTIONS
 * ============================================================================ */

/*
 * Test Function: Basic LCD Test
 */
void LCD_testBasic(void)
{
    LCD_init();
    LCD_clear();
    
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"LCD I2C Test");
    
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"Hello World!");
    
    _delay_ms(2000);
}

/*
 * Test Function: Number Display Test
 */
void LCD_testNumbers(void)
{
    LCD_clear();
    
    // Test positive number
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"Pos: ");
    LCD_writeNumber(12345);
    
    // Test negative number
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"Neg: ");
    LCD_writeNumber(-9876);
    
    // Test zero
    LCD_goTo(LCD_LINE_2, 0);
    LCD_writeString((u8*)"Zero: ");
    LCD_writeNumber(0);
    
    _delay_ms(3000);
}

/*
 * Test Function: Float Display Test
 */
void LCD_testFloat(void)
{
    LCD_clear();
    
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"Float: ");
    LCD_writeFloat(3.14159, 2);
    
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"Temp: ");
    LCD_writeFloat(25.5, 1);
    LCD_sendChar(0xDF);  // Degree symbol
    LCD_sendChar('C');
    
    _delay_ms(3000);
}

/*
 * Test Function: All Lines Test
 */
void LCD_testAllLines(void)
{
    LCD_clear();
    
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"Line 0: 20x4 LCD");
    
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"Line 1: I2C Mode");
    
    LCD_goTo(LCD_LINE_2, 0);
    LCD_writeString((u8*)"Line 2: PCF8574");
    
    LCD_goTo(LCD_LINE_3, 0);
    LCD_writeString((u8*)"Line 3: Working!");
    
    _delay_ms(3000);
}

/*
 * Test Function: Backlight Test
 */
void LCD_testBacklight(void)
{
    LCD_clear();
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"Backlight Test");
    
    _delay_ms(1000);
    
    LCD_backlightOff();
    _delay_ms(1000);
    
    LCD_backlightOn();
    _delay_ms(1000);
    
    LCD_backlightOff();
    _delay_ms(1000);
    
    LCD_backlightOn();
}

/*
 * Test Function: String Compare Test
 */
void LCD_testStringCompare(void)
{
    u8 str1[] = "HELLO";
    u8 str2[] = "HELLO";
    u8 str3[] = "WORLD";
    
    LCD_clear();
    
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"Str Compare Test:");
    
    LCD_goTo(LCD_LINE_1, 0);
    if (string_compare(str1, str2))
    {
        LCD_writeString((u8*)"str1==str2: TRUE");
    }
    else
    {
        LCD_writeString((u8*)"str1==str2: FALSE");
    }
    
    LCD_goTo(LCD_LINE_2, 0);
    if (string_compare(str1, str3))
    {
        LCD_writeString((u8*)"str1==str3: TRUE");
    }
    else
    {
        LCD_writeString((u8*)"str1==str3: FALSE");
    }
    
    _delay_ms(3000);
}

/*
 * Test Function: String Length Test
 */
void LCD_testStringLength(void)
{
    u8 testStr[] = "AVR ATmega32";
    
    LCD_clear();
    
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"String: ");
    LCD_writeString(testStr);
    
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"Length: ");
    LCD_writeNumber(string_length((s8*)testStr));
    
    _delay_ms(3000);
}

/*
 * Test Function: Clear Position Test
 */
void LCD_testClearPosition(void)
{
    LCD_clear();
    
    LCD_goTo(LCD_LINE_0, 0);
    LCD_writeString((u8*)"Clear Position Test");
    
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"1234567890");
    
    _delay_ms(2000);
    
    // Clear positions 2-7
    LCD_clearPosition(LCD_LINE_1, 2);
    LCD_clearPosition(LCD_LINE_1, 3);
    LCD_clearPosition(LCD_LINE_1, 4);
    LCD_clearPosition(LCD_LINE_1, 5);
    LCD_clearPosition(LCD_LINE_1, 6);
    LCD_clearPosition(LCD_LINE_1, 7);
    
    _delay_ms(2000);
}

/*
 * Main Test Function: Run All Tests
 */
void LCD_runAllTests(void)
{
    LCD_init();
    
    // Test 1: Basic Test
    LCD_testBasic();
    _delay_ms(1000);
    
    // Test 2: Numbers
    LCD_testNumbers();
    _delay_ms(1000);
    
    // Test 3: Float
    LCD_testFloat();
    _delay_ms(1000);
    
    // Test 4: All Lines
    LCD_testAllLines();
    _delay_ms(1000);
    
    // Test 5: Backlight
    LCD_testBacklight();
    _delay_ms(1000);
    
    // Test 6: String Compare
    LCD_testStringCompare();
    _delay_ms(1000);
    
    // Test 7: String Length
    LCD_testStringLength();
    _delay_ms(1000);
    
    // Test 8: Clear Position
    LCD_testClearPosition();
    _delay_ms(1000);
    
    // Final Message
    LCD_clear();
    LCD_goTo(LCD_LINE_1, 0);
    LCD_writeString((u8*)"All Tests Complete!");
    LCD_goTo(LCD_LINE_2, 0);
    LCD_writeString((u8*)"System Ready!");
}