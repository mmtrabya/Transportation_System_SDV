
#include "I2C_Int.h"
#include "../../BIT_MATH.h"
#include "../../STD_TYPES.h"
#include "../../REGS.h"

void TWI_init(void)
{
    TWBR = 0x32;
	TWSR = 0x00;	
    TWCR = (1<<TWEN); 
}

void TWI_start(void)
{
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
    while (!GET_BIT(TWCR, TWINT));

}

void TWI_stop(void)
{
    TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
}

void TWI_writeByte(u8 data)
{
    TWDR = data;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!GET_BIT(TWCR, TWINT));

}

u8 TWI_readByteWithACK(void)
{
    TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWEA);
    while (!GET_BIT(TWCR, TWINT));
    return TWDR;
}

u8 TWI_readByteWithNACK(void)
{
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!GET_BIT(TWCR, TWINT));
    return TWDR;
}

u8 TWI_getStatus(void)
{
    u8 status;
    status = TWSR & 0xF8;
    return status;
}