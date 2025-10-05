/*
 * GI_program.c
 *
 * Created: 2/10/2024 1:53:39 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

// UTAL
#include"../../STD_TYPES.h"
#include"../../BIT_MATH.h"

// MCAL
#include "GI_interface.h"
#include "../../REGS.h"

void GIE_Initi (u8 Value )
{
    switch (Value)
    {
        
    case Enable_GIE :
                     SET_BIT(SREG,I);               
    break;

    case Disable_GIE :
                     CLR_BIT(SREG,I);               
    break;

    }
}