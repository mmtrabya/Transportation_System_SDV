/*
 * TIMR0_program.c
 *
 * Created: 2/16/2024 3:04:06 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"

#include "TIMR0_interface.h"
#include "../../CFG/TIMR0_config.h"
#include "../../REGS.h"


static void(*Private_PCallBackOVF)(void) = NULL;
static void(*Private_PCallBackCTC)(void) = NULL;
static volatile u16 TIMR0_CTC_COUNTER ; 

void TIMR0_INTI  (void)
{

#if    TIMR0_Mode == Normal_Mode

// Select Normal Mode
CLR_BIT(TCCR0,WGM00);
CLR_BIT(TCCR0,WGM01);

// Preload Value
TCNT0 = TIMR0_Preload_Value;

// Enable Over Flow Flag 
SET_BIT(TIMSK,TOIE0);

#elif  TIMR0_Mode == CTC_Mode

// Select CTC Mode
CLR_BIT(TCCR0,WGM00);
SET_BIT(TCCR0,WGM01);

// Enable Output Compare Match Interrupt 
SET_BIT(TIMSK,OCIE0);

#elif  TIMR0_Mode == Fast_PWM

// Select Fast PWM
SET_BIT(TCCR0,WGM00);
SET_BIT(TCCR0,WGM01);

#if     TIMR0_FastPWM_Mode ==  FAST_PWM_Non_Inverting

// Select Non Inverting
CLR_BIT(TCCR0, COM00);
SET_BIT(TCCR0, COM01);


#elif   TIMR0_FastPWM_Mode ==  FAST_PWM_Inverting

// Select  Inverting
SET_BIT(TCCR0,COM00);
SET_BIT(TCCR0,COM01);

#endif

#endif




}
void TIMR0_Start (void)
{

// Set Prescaler 64
SET_BIT(TCCR0,CS00); 
SET_BIT(TCCR0,CS01);  
CLR_BIT(TCCR0,CS02);  

}
void TIMR0_Stop  (void)
{

// Set Prescaler 64
CLR_BIT(TCCR0,CS00); 
CLR_BIT(TCCR0,CS01);  
CLR_BIT(TCCR0,CS02);   

}
void TIMR0_SetCompareMatch (u8 CompareValue)
{
   OCR0 =  CompareValue; 
}
void TIMR0_MS_Delay (u16 Ms_Delay)
{
// Under Condition Tick time 4us     
 OCR0 = 249;
 TIMR0_CTC_COUNTER = Ms_Delay;
}
void TIMR0_CallBackOVF(void(*PtrToFun)(void))
{
  if (PtrToFun != NULL)
  {
    Private_PCallBackOVF = PtrToFun;
  }
    
}
void TIMR0_CallBackCTC(void(*PtrToFun)(void))
{
  if (PtrToFun != NULL)
  {
    Private_PCallBackCTC = PtrToFun;
  }
    
}
void TIMR0_DutyCycle (u8 Duty_Cycle )
{

if(Duty_Cycle <= 100) 
   {

#if     TIMR0_FastPWM_Mode ==  FAST_PWM_Non_Inverting

OCR0 = (((Duty_Cycle*TIMR0_Ticks)/100)-1);

#elif   TIMR0_FastPWM_Mode ==  FAST_PWM_Inverting

OCR0 = (255-((Duty_Cycle*TIMR0_Ticks)/100));

#endif
   }
}

// ISR TIMER0_OVFInterrupts
void __vector_11(void)__attribute__((signal));
void __vector_11(void)
{
	static u16 OVFCounter = 0;
	OVFCounter++;
	if(OVFCounter==TIMR0_OVER_FLOW_COUNTER){
	TCNT0 = TIMR0_Preload_Value; 
	OVFCounter = 0;
// Call Action
if(Private_PCallBackOVF != NULL)
    {
       Private_PCallBackOVF();
    } 

	  }
}

// ISR TIMER0_CTCInterrupts
void __vector_10(void)__attribute__((signal));
void __vector_10(void)
{
	static u16 CTCCounter = 0;
	CTCCounter++;
	if(CTCCounter== TIMR0_CTC_COUNTER){
	CTCCounter = 0;
// Call Action
if(Private_PCallBackCTC != NULL)
    {
       Private_PCallBackCTC();
    } 

	                                        }
}
