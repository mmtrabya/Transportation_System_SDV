#ifndef MPU_INT_H
#define MPU_INT_H

#include "../../MCAL/I2C/I2C_Int.h"
#include "../../STD_TYPES.h"

#define MPU6050_ADDRESS  0x68
#define PWR_1            0x6B
#define ACC_CONFIG       0x1C
#define GYRO_CONFIG      0x1B
#define WHO_AM_I         0x75
#define MPU60X0_W        0xD0    // 0X68  = 0XD0   
#define MPU60X0_R        0xD1    // 0X68  = 0XD1    
#define MPU6050_ACCX     0x3B
#define INT_PIN_CFG      0x37
#define USER_CTRL        0x6A

extern u8 arr[14];
extern s16 ACCX, ACCY, ACCZ, T, GYX, GYY, GYZ;
extern f32 AX, AY, AZ, TEM, GY, GX, GZ;

void MPU_Init(void);
void MPU_Write(u8 dev_addr, u8 reg, u8 instr);
u8 MPU6050_TestConnection(void);
void MPU_Readall();
void MPU_Conv();
void MPU6050_EnableBypassMode();

#endif /* MPU_INT_H */