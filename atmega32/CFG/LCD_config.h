/*
 * LCD_I2C_config.h
 *
 * Configuration file for I2C 20x4 LCD
 * PCF8574 I2C I/O Expander Configuration
 */ 

#ifndef LCD_I2C_CONFIG_H_
#define LCD_I2C_CONFIG_H_

/* I2C LCD Address Configuration */
/* Common I2C addresses: 0x27, 0x3F, 0x20, 0x38 */
/* Check your module's address with I2C scanner if unsure */
#define LCD_I2C_ADDRESS    0x27

/* PCF8574 Pin Mapping to LCD pins */
/* Standard PCF8574 to LCD pin mapping:
 * P0 -> RS
 * P1 -> RW
 * P2 -> EN
 * P3 -> Backlight
 * P4 -> D4
 * P5 -> D5
 * P6 -> D6
 * P7 -> D7
 */

#define LCD_RS_BIT    0
#define LCD_RW_BIT    1
#define LCD_EN_BIT    2
#define LCD_BL_BIT    3  // Backlight
#define LCD_D4_BIT    4
#define LCD_D5_BIT    5
#define LCD_D6_BIT    6
#define LCD_D7_BIT    7

/* Line Definitions for 20x4 LCD */
#define LCD_LINE_0     0
#define LCD_LINE_1     1
#define LCD_LINE_2     2
#define LCD_LINE_3     3

/* LCD Commands */
#define LCD_CMD_CLEAR          0x01
#define LCD_CMD_HOME           0x02
#define LCD_CMD_ENTRY_MODE     0x06
#define LCD_CMD_DISPLAY_ON     0x0C
#define LCD_CMD_DISPLAY_OFF    0x08
#define LCD_CMD_CURSOR_ON      0x0E
#define LCD_CMD_CURSOR_BLINK   0x0F
#define LCD_CMD_4BIT_MODE      0x28  // 4-bit, 2 lines, 5x8 font
#define LCD_CMD_8BIT_MODE      0x38  // 8-bit, 2 lines, 5x8 font

#endif /* LCD_I2C_CONFIG_H_ */