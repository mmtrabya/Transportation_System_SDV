#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"
#include "../../REGS.h"
#include "EEPROM_Int.h"


static void (*eeprom_ready)(void) = NULL;

void EEPROM_Write(u8 data, u16 address)
{
	/* Wait for completion of previous write */
	while(GET_BIT(EECR, EEWE));
	
	/*******write address & data*******/
	EEAR = address;
	EEDR = data;
	
	/******* enable write *******/
	// Disable global interrupt
	cli();
	
	// Set EEPROM Master Write Enable
	SET_BIT(EECR, EEMWE);
	
	// Start EEPROM write by setting EEWE
	// Must be done within four clock cycles after setting EEMWE
	SET_BIT(EECR, EEWE);
	
	// Enable global interrupt
	sei();
}


u8 EEPROM_Read(u16 address)
{
	/* Wait for completion of previous write */
	while(GET_BIT(EECR, EEWE));
	
	/*******Write address*******/
	EEAR = address;
	
	/*******Enable Read*******/
	SET_BIT(EECR, EERE);
	
	return EEDR;
}


void EEPROM_InterruptEnable(void)
{
	SET_BIT(EECR, EERIE);
}

void EEPROM_InterruptDisable(void)
{
	CLR_BIT(EECR, EERIE);
}


void EEPROM_SetCallback(void (*localFptr)(void))
{
	eeprom_ready = localFptr;
}


ISR(EE_RDY_vect)
{
	if (eeprom_ready != NULL)
	{
		eeprom_ready();
	}
}