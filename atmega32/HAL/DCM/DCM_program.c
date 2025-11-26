/*
 * DCM_program.c
 * H-Bridge DC Motor Driver with Custom Grouping
 * Group 1: Motor A & C | Group 2: Motor B & D
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#include "../../STD_TYPES.h"
#include "../../BIT_MATH.h"
#include "../../MCAL/DIO/DIO_interface.h"
#include "../../MCAL/TIMER0/TIMR0_interface.h"
#include "../../CFG/TIMR0_config.h"
#include "DCM_interface.h"
#include "../../CFG/DCM_config.h"


void DCM_Inti_Motor_A (void)
{
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MA_IN_PORT, DCM_MA_IN1); 
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MA_IN_PORT, DCM_MA_IN2);
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MA_ENABLE_PORT, DCM_MA_ENABLE);
    
    DIO_setPinValue(DCM_PIN_LOW, DCM_MA_IN_PORT, DCM_MA_IN1);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MA_IN_PORT, DCM_MA_IN2);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MA_ENABLE_PORT, DCM_MA_ENABLE);
}

void DCM_Inti_Motor_B (void)
{
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MB_IN_PORT, DCM_MB_IN3);
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MB_IN_PORT, DCM_MB_IN4);
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MB_ENABLE_PORT, DCM_MB_ENABLE);
    
    DIO_setPinValue(DCM_PIN_LOW, DCM_MB_IN_PORT, DCM_MB_IN3);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MB_IN_PORT, DCM_MB_IN4);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MB_ENABLE_PORT, DCM_MB_ENABLE);
}

void DCM_Inti_Motor_C (void)
{
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MC_IN_PORT, DCM_MC_IN1); 
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MC_IN_PORT, DCM_MC_IN2);
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MC_ENABLE_PORT, DCM_MC_ENABLE);
    
    DIO_setPinValue(DCM_PIN_LOW, DCM_MC_IN_PORT, DCM_MC_IN1);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MC_IN_PORT, DCM_MC_IN2);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MC_ENABLE_PORT, DCM_MC_ENABLE);
}

void DCM_Inti_Motor_D (void)
{
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MD_IN_PORT, DCM_MD_IN3);
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MD_IN_PORT, DCM_MD_IN4);
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_MD_ENABLE_PORT, DCM_MD_ENABLE);
    
    DIO_setPinValue(DCM_PIN_LOW, DCM_MD_IN_PORT, DCM_MD_IN3);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MD_IN_PORT, DCM_MD_IN4);
    DIO_setPinValue(DCM_PIN_LOW, DCM_MD_ENABLE_PORT, DCM_MD_ENABLE);
}

void DCM_Init_All(void)
{
    DCM_Inti_Motor_A();
    DCM_Inti_Motor_B();
    DCM_Inti_Motor_C();
    DCM_Inti_Motor_D();
    
    // Initialize PWM pin
    DIO_setPinDirection(DCM_PIN_OUTPUT, DCM_PWM_PORT, DCM_PWM_PIN);
    
    // Initialize Timer0 for PWM
    TIMR0_INTI();
    TIMR0_Start();
}

void DCM_Speed (u8 Speed, u8 Motor, u8 Direction)
{
    if (Speed <= 100 && Motor <= 3 && Direction <= 1)
    {
        // Set PWM duty cycle once for all motors
        TIMR0_DutyCycle(Speed);
        
        switch (Motor)
        {
            case DCM_Motor_A:
                DIO_setPinValue(DCM_PIN_HIGH, DCM_MA_ENABLE_PORT, DCM_MA_ENABLE);
                
                switch(Direction)
                {
                    case DCM_CW:
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MA_IN_PORT, DCM_MA_IN1);
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MA_IN_PORT, DCM_MA_IN2);
                        break; 

                    case DCM_CCW:
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MA_IN_PORT, DCM_MA_IN1);
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MA_IN_PORT, DCM_MA_IN2);
                        break;
                }
                break;

            case DCM_Motor_B:
                DIO_setPinValue(DCM_PIN_HIGH, DCM_MB_ENABLE_PORT, DCM_MB_ENABLE);
                
                switch(Direction)
                {
                    case DCM_CW:
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MB_IN_PORT, DCM_MB_IN3);
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MB_IN_PORT, DCM_MB_IN4);
                        break; 

                    case DCM_CCW:
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MB_IN_PORT, DCM_MB_IN3);
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MB_IN_PORT, DCM_MB_IN4);
                        break;
                }
                break;

            case DCM_Motor_C:
                DIO_setPinValue(DCM_PIN_HIGH, DCM_MC_ENABLE_PORT, DCM_MC_ENABLE);
                
                switch(Direction)
                {
                    case DCM_CW:
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MC_IN_PORT, DCM_MC_IN1);
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MC_IN_PORT, DCM_MC_IN2);
                        break; 

                    case DCM_CCW:
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MC_IN_PORT, DCM_MC_IN1);
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MC_IN_PORT, DCM_MC_IN2);
                        break;
                }
                break;

            case DCM_Motor_D:
                DIO_setPinValue(DCM_PIN_HIGH, DCM_MD_ENABLE_PORT, DCM_MD_ENABLE);
                
                switch(Direction)
                {
                    case DCM_CW:
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MD_IN_PORT, DCM_MD_IN3);
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MD_IN_PORT, DCM_MD_IN4);
                        break; 

                    case DCM_CCW:
                        DIO_setPinValue(DCM_PIN_LOW, DCM_MD_IN_PORT, DCM_MD_IN3);
                        DIO_setPinValue(DCM_PIN_HIGH, DCM_MD_IN_PORT, DCM_MD_IN4);
                        break;
                }
                break;
        }
    }   
}

void DCM_OFF(u8 Motor)
{
    if (Motor <= 3)
    {
        switch (Motor)
        {
            case DCM_Motor_A:
                DIO_setPinValue(DCM_PIN_LOW, DCM_MA_IN_PORT, DCM_MA_IN1);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MA_IN_PORT, DCM_MA_IN2);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MA_ENABLE_PORT, DCM_MA_ENABLE);
                break;

            case DCM_Motor_B:
                DIO_setPinValue(DCM_PIN_LOW, DCM_MB_IN_PORT, DCM_MB_IN3);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MB_IN_PORT, DCM_MB_IN4);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MB_ENABLE_PORT, DCM_MB_ENABLE);
                break;

            case DCM_Motor_C:
                DIO_setPinValue(DCM_PIN_LOW, DCM_MC_IN_PORT, DCM_MC_IN1);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MC_IN_PORT, DCM_MC_IN2);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MC_ENABLE_PORT, DCM_MC_ENABLE);
                break;

            case DCM_Motor_D:
                DIO_setPinValue(DCM_PIN_LOW, DCM_MD_IN_PORT, DCM_MD_IN3);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MD_IN_PORT, DCM_MD_IN4);
                DIO_setPinValue(DCM_PIN_LOW, DCM_MD_ENABLE_PORT, DCM_MD_ENABLE);
                break;
        }
    }
}

// ============ PAIRED MOTOR CONTROL - Group 1: A&C, Group 2: B&D ============

void DCM_Group1_Speed(u8 Speed, u8 Direction)
{
    // Control Motor A and Motor C together (Group 1)
    DCM_Speed(Speed, DCM_Motor_A, Direction);
    DCM_Speed(Speed, DCM_Motor_C, Direction);
}

void DCM_Group2_Speed(u8 Speed, u8 Direction)
{
    // Control Motor B and Motor D together (Group 2)
    DCM_Speed(Speed, DCM_Motor_B, Direction);
    DCM_Speed(Speed, DCM_Motor_D, Direction);
}

void DCM_Group1_OFF(void)
{
    // Stop Motor A and Motor C
    DCM_OFF(DCM_Motor_A);
    DCM_OFF(DCM_Motor_C);
}

void DCM_Group2_OFF(void)
{
    // Stop Motor B and Motor D
    DCM_OFF(DCM_Motor_B);
    DCM_OFF(DCM_Motor_D);
}

void DCM_All_OFF(void)
{
    // Stop all motors
    DCM_OFF(DCM_Motor_A);
    DCM_OFF(DCM_Motor_B);
    DCM_OFF(DCM_Motor_C);
    DCM_OFF(DCM_Motor_D);
}

// ============ ROBOT MOVEMENT FUNCTIONS ============

void DCM_Move_Forward(u8 Speed)
{
    // Both groups move forward
    DCM_Group1_Speed(Speed, DCM_CW);
    DCM_Group2_Speed(Speed, DCM_CW);
}

void DCM_Move_Backward(u8 Speed)
{
    // Both groups move backward
    DCM_Group1_Speed(Speed, DCM_CCW);
    DCM_Group2_Speed(Speed, DCM_CCW);
}

void DCM_Turn_Right(u8 Speed)
{
    // Group 1 (A&C) forward, Group 2 (B&D) backward
    DCM_Group1_Speed(Speed, DCM_CW);
    DCM_Group2_Speed(Speed, DCM_CCW);
}

void DCM_Turn_Left(u8 Speed)
{
    // Group 1 (A&C) backward, Group 2 (B&D) forward
    DCM_Group1_Speed(Speed, DCM_CCW);
    DCM_Group2_Speed(Speed, DCM_CW);
}

void DCM_Stop(void)
{
    // Stop all motors
    DCM_All_OFF();
}