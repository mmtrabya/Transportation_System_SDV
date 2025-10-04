
#include "MPU_Int.h"
#include <util/delay.h>

u8 arr[14];
s16 ACCX, ACCY, ACCZ, T, GYX, GYY, GYZ;
f32 AX, AY, AZ, TEM, GY, GX, GZ;

void MPU_Init(void)
{
	TWI_start();
	TWI_writeByte(MPU60X0_W);
	TWI_writeByte(PWR_1);
	TWI_writeByte(0x00);  
	TWI_stop();
	_delay_ms(100);  

	MPU_Write(MPU60X0_W, ACC_CONFIG, 0x00);

	MPU_Write(MPU60X0_W, GYRO_CONFIG, 0x00);
}
void MPU_Write(u8 dev_addr, u8 reg, u8 instr)
{
	TWI_start();
	TWI_writeByte(dev_addr);
	TWI_writeByte(reg);
	TWI_writeByte(instr);
	TWI_stop();
}
u8 MPU6050_TestConnection(void) {
	TWI_start();
	TWI_writeByte((MPU60X0_W));
	if (TWI_getStatus() != TWI_MT_SLA_W_ACK) { // SLA+W ACK
		TWI_stop();
		return 0; 
	}
	TWI_stop();
	return 1; 
}
void MPU_Readall()
{
	TWI_start();
	TWI_writeByte(MPU60X0_W);
	TWI_writeByte(MPU6050_ACCX);
	_delay_us(10);
	TWI_start();
	TWI_writeByte(MPU60X0_R);
	
	for (u8 i = 0; i < 13; i++)
	{
		arr[i] = TWI_readByteWithACK();
	}
	arr[13] = TWI_readByteWithNACK();
	TWI_stop();
	
	_delay_ms(5);
	
	ACCX = (s16)((arr[0] << 8) | arr[1]);
	ACCY = (s16)((arr[2] << 8) | arr[3]);
	ACCZ = (s16)((arr[4] << 8) | arr[5]);
	T = (s16)((arr[6] << 8) | arr[7]);
	GYX = (s16)((arr[8] << 8) | arr[9]);
	GYY = (s16)((arr[10] << 8) | arr[11]);
	GYZ = (s16)((arr[12] << 8) | arr[13]);
}
void MPU_Conv(void)
{
	MPU_Readall();
	AX = (ACCX / 16384.0) * 9.81;
	AY = (ACCY / 16384.0) * 9.81;
	AZ = (ACCZ / 16384.0) * 9.81;
	TEM = (T / 340.0) + 36.53;
	GX = GYX / 131.0;
	GY = GYY / 131.0;
	GZ = GYZ / 131.0;
}
void MPU6050_EnableBypassMode() {
	TWI_start();
	TWI_writeByte((MPU6050_ADDRESS << 1) | 0);
	TWI_writeByte(USER_CTRL);
	TWI_writeByte(0x00);
	TWI_stop();
	_delay_ms(10);
	
	TWI_start();
	TWI_writeByte((MPU6050_ADDRESS << 1) | 0);
	TWI_writeByte(INT_PIN_CFG);
	TWI_writeByte(0x02);
	TWI_stop();
	
	TWI_start();
	TWI_writeByte((MPU6050_ADDRESS << 1) | 0);
	TWI_writeByte(PWR_1);
	TWI_writeByte(0x00);
	TWI_stop();
	_delay_ms(10);
}



