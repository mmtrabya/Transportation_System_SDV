#ifndef QMC_INT_H
#define QMC_INT_H
//#define F_CPU  8000000UL
#include "../../STD_TYPES.h"
#include "../../MCAL/I2C/I2C_Int.h"
#include <util/delay.h>
#include <math.h>

// QMC5883L I2C Address
#define QMC5883L_ADDR      0x0D

// Register Map
#define QMC_CONFIG_1       0x09
#define QMC_CONFIG_2       0x0A
#define QMC_SET_RESET      0x0B
#define QMC_STATUS         0x06
#define QMC_DATA_X_LSB     0x00
#define QMC_DATA_X_MSB     0x01
#define QMC_DATA_Y_LSB     0x02
#define QMC_DATA_Y_MSB     0x03
#define QMC_DATA_Z_LSB     0x04
#define QMC_DATA_Z_MSB     0x05

// Configuration Values
#define QMC_MODE_CONT      0x01
#define QMC_ODR_200HZ      0x11
#define QMC_RNG_2G         0x00
#define QMC_OSR_512        0x00

typedef struct {
	s16 mag_x;
	s16 mag_y;
	s16 mag_z;
} QMC5883L_Data_t;

extern QMC5883L_Data_t qmc_data;

// Function prototypes
void QMC5883L_Init(void);
u8 QMC5883L_TestConnection(void);
void QMC5883L_Read(QMC5883L_Data_t *data);
f32 QMC5883L_CalculateHeading(QMC5883L_Data_t *data);

#endif /* QMC_INT_H */