/*
 * LCD_I2C_private.h
 *
 * Private definitions for I2C LCD driver
 */ 

#ifndef LCD_I2C_PRIVATE_H_
#define LCD_I2C_PRIVATE_H_

#include "../../STD_TYPES.h"
#include "../../CFG/LCD_config.h"
#include "LCD_interface.h"

/* Private Functions */
// static void LCD_I2C_SendByte     (u8 data, u8 mode);
// static void LCD_I2C_SendNibble   (u8 nibble, u8 mode);
// static void LCD_I2C_PulseEnable  (u8 data);
// static void LCD_I2C_WriteByte    (u8 data);

/* Mode definitions */
#define LCD_MODE_COMMAND    0
#define LCD_MODE_DATA       1



#endif /* LCD_I2C_PRIVATE_H_ */