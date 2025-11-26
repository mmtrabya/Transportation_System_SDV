/*
 * TWI_program.c
 *
 * Created: 10/7/2023 10:36:30 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


 /* UTILES_LIB */
#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"

/* MCAL */
#include "TWI_interface.h"
#include "TWI_private.h"


void TWI_initMaster(void)
{
	// Set Prescaller = 1 >> Set Freq. = 400KHZ
	CLR_BIT(TWSR,TWPS0);
	CLR_BIT(TWSR,TWPS1);
	TWBR = 12;
	
	// Enable ACK
	SET_BIT(TWCR,TWEA);
	
	// Enable TWI Peripheral
	SET_BIT(TWCR,TWEN);
}


void TWI_sendStartCondition(void)
{
	// Request Start Condition
	SET_BIT(TWCR,TWSTA);
	
	// Clear flag to start current job
	SET_BIT(TWCR,TWINT);
	
	// Busy Wait for the flag 
	while(0 == GET_BIT(TWCR,TWINT));
	
	// Check ACK = SC ACK
	while(TWI_STATUS_VALUE != TWI_START_CONDITION_ACK);
}


void TWI_sendRepStartCondition(void)
{
	// Request Start Condition
	SET_BIT(TWCR,TWSTA);
	
	// Clear flag to start current job
	SET_BIT(TWCR,TWINT);
	
	// Busy Wait for the flag 
	while(0 == GET_BIT(TWCR,TWINT));
	
	// Check ACK = Repeated SC ACK
	while(TWI_STATUS_VALUE != TWI_REP_START_CONDITION_ACK);
}


void TWI_sendStopCondition(void)
{
	// Request Stop Condition
	SET_BIT(TWCR,TWSTO);
	
	// Clear flag to start current job
	SET_BIT(TWCR,TWINT);
}


void TWI_sendSlaveAddWithWrite(u8 slaveAdd)
{
	if(slaveAdd<128)
	{
		TWDR = slaveAdd<<1;
		
		// Select write operation
		CLR_BIT(TWDR,0);
		
		// Clear SC bit
		CLR_BIT(TWCR,TWSTA);
		
		// Clear flag to start current job
	    SET_BIT(TWCR,TWINT);
	    
	    // Busy Wait for the flag 
	    while(0 == GET_BIT(TWCR,TWINT));
		
		// Check ACK = Master transmit ( slave address + Write request )
		while(TWI_STATUS_VALUE != TWI_SLAVE_ADDRESS_WRITE_ACK);
	}
}


void TWI_sendSlaveAddWithRead(u8 slaveAdd)
{
	if(slaveAdd<128)
	{
		TWDR = slaveAdd<<1;
		
		// Select read operation
		SET_BIT(TWDR,0);
		
		// Clear SC bit
		CLR_BIT(TWCR,TWSTA);
		
		// Clear flag to start current job
	    SET_BIT(TWCR,TWINT);
	    
	    // Busy Wait for the flag 
	    while(0 == GET_BIT(TWCR,TWINT));
		
		 // Check ACK = Master transmit ( slave address + Read request ) ACK
		while(TWI_STATUS_VALUE != TWI_SLAVE_ADDRESS_READ_ACK);
	}
}


void TWI_sendMasterDataByte(u8 TxData)
{
	// Write Data into data register
	TWDR = TxData;
	
	// Clear flag to start current job
	SET_BIT(TWCR,TWINT);
	
	// Busy Wait for the flag 
	while(0 == GET_BIT(TWCR,TWINT));
	
	// Check ACK = Master transmit data ACK
	while(TWI_STATUS_VALUE != TWI_MASTER_DATA_TRANSMIT_ACK);
}


void TWI_receiveMasterDataByteAck(u8* RxData)
{
	if(RxData != NULL)
	{
		// Clear flag to start current job
	    SET_BIT(TWCR,TWINT);
		
		// Busy Wait for the flag 
	    while(0 == GET_BIT(TWCR,TWINT));
		
		// Check ACK = Master received data with ACK
		while(TWI_STATUS_VALUE != TWI_MASTER_DATA_RECIEVE_ACK);
		
		// Read Data from data register
		*RxData = TWDR;
	}
}


void TWI_receiveMasterDataByteNack(u8* RxData)
{
	if(RxData != NULL)
	{
		// Disable ACK
		CLR_BIT(TWCR,TWEA);
		
		// Clear flag to start current job
		SET_BIT(TWCR,TWINT);
		
		// Busy Wait for the flag
		while(0 == GET_BIT(TWCR,TWINT));
		
		// Check ACK = Master received data with NACK
		while(TWI_STATUS_VALUE != TWI_MASTER_DATA_RECIEVE_NACK);
		
		// Read Data from data register
		*RxData = TWDR;
		
		// Enable ACK
		SET_BIT(TWCR,TWEA);
	}
}
// Wrapper functions for compatibility
void TWI_start(void) {
    TWI_sendStartCondition();
}

void TWI_stop(void) {
    TWI_sendStopCondition();
}

void TWI_writeByte(u8 data) {
    TWI_sendMasterDataByte(data);
}

u8 TWI_readByteWithACK(void) {
    u8 data;
    TWI_receiveMasterDataByteAck(&data);
    return data;
}

u8 TWI_readByteWithNACK(void) {
    u8 data;
    TWI_receiveMasterDataByteNack(&data);
    return data;
}
