/*
 * EXIT_program.c
 *
 * Created: 2/10/2024 1:52:16 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

// UTAL
#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"

//MCAL
#include "EXIT_interface.h"
#include "../../CFG/EXIT_config.h"
#include"../../REGS.h"


static void(*Private_PCallBack)(void) = NULL;

void EXIT_Enable  (u8 EXIT_Source,u8 EXIT_Triggre)
{
 if (EXIT_Source <= EXIT_Interrupts && EXIT_Triggre <= EXIT_MODES )
 {   

   switch (EXIT_Source)
   {
    case EXIT_INT0 :
                    switch (EXIT_Triggre)
                    {

                     case LOW_LEVEL :
                                     CLR_BIT(MCUCR,ISC01);
                                     CLR_BIT(MCUCR,ISC00);  
                     break;

                     case ANY_LOGICAL_CHANGE :
                                     CLR_BIT(MCUCR,ISC01);
                                     SET_BIT(MCUCR,ISC00);  
                     break;

                     case FALLING_EDGE :
                                     SET_BIT(MCUCR,ISC01);
                                     CLR_BIT(MCUCR,ISC00);  
                     break;

                     case RISING_EDGE :
                                     SET_BIT(MCUCR,ISC01);
                                     SET_BIT(MCUCR,ISC00);  
                     break;

                    } 
        SET_BIT(GICR,INT0);                
    break;
   
       case EXIT_INT1 :
                    switch (EXIT_Triggre)
                    {

                     case LOW_LEVEL :
                                     CLR_BIT(MCUCR,ISC11);
                                     CLR_BIT(MCUCR,ISC10);  
                     break;

                     case ANY_LOGICAL_CHANGE :
                                     CLR_BIT(MCUCR,ISC11);
                                     SET_BIT(MCUCR,ISC10);  
                     break;

                     case FALLING_EDGE :
                                     SET_BIT(MCUCR,ISC11);
                                     CLR_BIT(MCUCR,ISC10);  
                     break;

                     case RISING_EDGE :
                                     SET_BIT(MCUCR,ISC11);
                                     SET_BIT(MCUCR,ISC10);  
                     break;

                    }
        SET_BIT(GICR,INT1);                      
    break;
   
    case EXIT_INT2 :
                    switch (EXIT_Triggre)
                    {

                     case RISING_EDGE :
                                     SET_BIT(MCUCSR,ISC2); 
                     break;

                     case FALLING_EDGE :
                                     CLR_BIT(MCUCSR,ISC2);  
                     break;

                    }
        SET_BIT(GICR,INT2);                      
    break;
   }
 }
}
void EXIT_Disable (u8 EXIT_Source)
{
 if (EXIT_Source <= EXIT_Interrupts)
 {
    switch (EXIT_Source)
    {
    case EXIT_INT0 :
                    CLR_BIT(GICR,INT0);
        break;

    case EXIT_INT1 :
                    CLR_BIT(GICR,INT1);
        break;

    case EXIT_INT2 :
                    CLR_BIT(GICR,INT2);
        break;            

    }
 }     
}

void EXIT_CallBack(void(*PtrToFUN)(void))
  {
    if(PtrToFUN != NULL)
       {
         Private_PCallBack = PtrToFUN;
       }
  }



// ISR EXIT_Interrupts
void __vector_1(void)__attribute__((signal));
void __vector_1(void)
{
      if(Private_PCallBack != NULL)
       {
         Private_PCallBack();
       }
}