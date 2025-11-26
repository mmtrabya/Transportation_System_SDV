/*
 * DCM_interface.h
 * DC Motor Driver with Custom Paired Motor Control
 * Group 1: Motor A & C | Group 2: Motor B & D
 * Created: 2/24/2024 1:10:44 PM
 * Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 

#ifndef DCM_INTERFACE_H_
#define DCM_INTERFACE_H_

#include "../../STD_TYPES.h"

// Individual motor initialization
void DCM_Inti_Motor_A  (void);
void DCM_Inti_Motor_B  (void);
void DCM_Inti_Motor_C  (void);
void DCM_Inti_Motor_D  (void);

// Initialize all motors
void DCM_Init_All(void);

// Individual motor control
void DCM_Speed (u8 Speed, u8 Motor, u8 Direction);
void DCM_OFF   (u8 Motor);

// Paired motor control functions
// Group 1: Motor A & C (e.g., left side of robot)
// Group 2: Motor B & D (e.g., right side of robot)
void DCM_Group1_Speed(u8 Speed, u8 Direction);  // Controls Motor A & C together
void DCM_Group2_Speed(u8 Speed, u8 Direction);  // Controls Motor B & D together
void DCM_Group1_OFF(void);                       // Stop Motor A & C
void DCM_Group2_OFF(void);                       // Stop Motor B & D
void DCM_All_OFF(void);                          // Stop all motors

// Robot movement functions
// NOTE: These assume Group1 (A&C) is LEFT side, Group2 (B&D) is RIGHT side
void DCM_Move_Forward(u8 Speed);
void DCM_Move_Backward(u8 Speed);
void DCM_Turn_Right(u8 Speed);
void DCM_Turn_Left(u8 Speed);
void DCM_Stop(void);

#endif /* DCM_INTERFACE_H_ */