/*
 * LCD_I2C_interface.h
 *
 * Created: Modified for I2C 20x4 LCD support
 * Author: Modified for I2C communication via PCF8574
 * Description: LCD driver using I2C (TWI) interface
 */ 

#ifndef LCD_I2C_INTERFACE_H_
#define LCD_I2C_INTERFACE_H_

#include "../../STD_TYPES.h"

/* ============================================================================
 * PUBLIC FUNCTIONS
 * ============================================================================ */

/* Basic LCD Functions */
void LCD_init         (void);
void LCD_sendCommand  (u8 command);
void LCD_sendChar     (u8 data);
void LCD_writeString  (u8* string);
void LCD_clear        (void);

/* Number Display Functions */
void LCD_writeNumber      (S32 number);
void LCD_writeSignedNumber(S32 number);
void LCD_writeFloat       (float number, u8 decimalPlaces);

/* Cursor Control Functions */
void LCD_goTo         (u8 lineNumber, u8 position);
void LCD_clearPosition(u8 lineNumber, u8 position);
void LCD_clearLine    (u8 lineNumber);

/* Backlight Control */
void LCD_backlightOn  (void);
void LCD_backlightOff (void);

/* ============================================================================
 * TEST FUNCTIONS
 * ============================================================================ */

void LCD_testBasic        (void);
void LCD_testNumbers      (void);
void LCD_testFloat        (void);
void LCD_testAllLines     (void);
void LCD_testBacklight    (void);
void LCD_testStringCompare(void);
void LCD_testStringLength (void);
void LCD_testClearPosition(void);
void LCD_runAllTests      (void);

#endif /* LCD_INTERFACE_H_ */