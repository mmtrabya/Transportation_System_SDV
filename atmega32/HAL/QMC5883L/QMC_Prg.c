
#include "QMC_Int.h"

void QMC5883L_Init(void) {
	TWI_start();
	TWI_writeByte((QMC5883L_ADDR << 1) | 0);
	TWI_writeByte(QMC_CONFIG_1);
	TWI_writeByte(QMC_OSR_512 | QMC_RNG_2G | QMC_ODR_200HZ | QMC_MODE_CONT);
	TWI_stop();
	_delay_ms(10);
	
}

u8 QMC5883L_TestConnection(void) {
	TWI_start();
	TWI_writeByte((QMC5883L_ADDR << 1) | 0);
	if (TWI_getStatus() != TWI_MT_SLA_W_ACK) { // SLA+W ACK
		TWI_stop();
		return 0;
	}
	TWI_stop();
	return 1;
}

void QMC5883L_Read(QMC5883L_Data_t *data) {
	
	TWI_start();
	TWI_writeByte((QMC5883L_ADDR << 1) | 0);
	TWI_writeByte(QMC_DATA_X_LSB);
	TWI_stop();

	TWI_start();
	TWI_writeByte((QMC5883L_ADDR << 1) | 1);

	data->mag_x = (s16)(((s16)TWI_readByteWithACK() ) | ((s16)TWI_readByteWithACK() << 8));
	data->mag_y = (s16)(((s16)TWI_readByteWithACK() ) | ((s16)TWI_readByteWithACK() << 8));
	data->mag_z = (s16)(((s16)TWI_readByteWithACK() ) | ((s16)TWI_readByteWithNACK() << 8));

	TWI_stop();
}

f32 QMC5883L_CalculateHeading(QMC5883L_Data_t *data) {
	f32 heading = atan2((f32)data->mag_y, (f32)data->mag_x) * 180.0 / M_PI;
	if (heading < 0) heading += 360.0;
	return heading;
}
