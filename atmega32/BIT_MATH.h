/************************************************************************
 *                                                                      *
 *************************  Date    : 18/08/2023      *******************
 *************************  Name    : Mahmoud Mahgoup *******************
 *************************  Version : 1.0             *******************
 *************************  SWC     : BIT MATH        *******************
 *                                                                      *
 ************************************************************************/
 
#ifndef BIT_MATH_H_ 
#define BIT_MATH_H_

//PIN
#define SET_BIT(REG,BIT_NUM)    REG|=(1<<BIT_NUM)
#define CLR_BIT(REG,BIT_NUM)    REG&=(~(1<<BIT_NUM))
#define TOG_BIT(REG,BIT_NUM)    REG^=(1<<BIT_NUM)
#define GET_BIT(REG,BIT_NUM)    ((REG>>BIT_NUM)&1)

//PORT
#define SET_PORT(REG)    REG|=(0xFF)
#define CLR_PORT(REG)    REG&=(0x00)
#define TOG_PORT(REG)    REG^=(0xFF)
#define GET_PORT(REG)    ((REG>>BIT_NUM)&1)


#endif