

#ifndef STRING_H_
#define STRING_H_

#include "../../STD_TYPES.h"

void Remove_string(s8*str);
u8 string_length(s8 *str);
void string_reverse(s8 *str);
u8 string_compare(u8*str1,u8*str2);
void NUM_tostring(s8 *str,S32 num);



#endif /* STRING_H_ */