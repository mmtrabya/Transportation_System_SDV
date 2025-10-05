/************************************************************************
 *                                                                      *
 *************************  Date    : 18/08/2023      *******************
 *************************  Name    : Mahmoud Mahgoup *******************
 *************************  Version : 1.0             *******************
 *************************  SWC     : STD TYPES       *******************
 *                                                                      *
 ************************************************************************/
#ifndef STD_TYPES_H_ 
#define STD_TYPES_H_

typedef unsigned  char       u8;
typedef signed char          s8;
typedef char c8;

typedef unsigned short int  u16;
typedef unsigned long int   u32;

typedef signed short int    s16;
typedef signed long int     S32;

typedef float           f32;
typedef double          f64;

#define  Max_u8  255
#define  Max_s8  127
#define  Min_u8   0
#define  Min_s8  -128

typedef enum
{
	False=0x55,
	True=0xAA
}bool_t;


typedef enum 
{
	OK,
	NOK,
	INPROGRESS
}Return_t;

#define  NULL  ((void*)0)
#endif 