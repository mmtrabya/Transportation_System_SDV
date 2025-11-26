/*
 * EXIT_interface.h
 *
 * Created: 2/10/2024 1:51:41 PM
 *  Author: Mohammed Tarabay & Mahmoud Mahgoup
 */ 


#ifndef EXIT_INTERFACE_H_
#define EXIT_INTERFACE_H_

void EXIT_Enable  (u8 EXIT_Source,u8 EXIT_Triggre);
void EXIT_Disable (u8 EXIT_Source);
void EXIT_CallBack(void(*PtrToFUN)(void));


#endif /* EXIT_INTERFACE_H_ */