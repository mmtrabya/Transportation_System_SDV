

#include "../../STD_TYPES.h"


void Remove_string(s8*str)
{
	u8 i;
	for(i=0;str[i];i++)
	{
		str[i]=0;
	}
}
u8 string_length(s8 *str)
{
	u8 i=0;
	for (i=0;str[i];i++);
	return i;
}

void string_reverse(s8 *str)
{
	u8 temp,len,i;
	
	len=string_length(str);
	for(i=0;i<=len-1;i++)
	{
		temp=str[i];
		str[i]=str[len-1];
		str[len-1]=temp;
		len--;
	}

}

u8 string_compare(u8*str1,u8*str2)
{
	int i;
	for (i=0;str1[i];i++)
	{
		if (str1[i]!=str2[i])
		{
			return 0;
		}
	}
	return 1;
}
void NUM_tostring(s8 *str,S32 num)
{
	u8 i=0,flag=0;
	S32 r=0;
	
	if (num==0)
	{
		str[0]='0';
		str[9]=0;
	}
	if (num<0)
	{
		num=num*(-1);
		flag=1;
	}
	for (i=0;num!=0;i++)
	{
		r=num%10;
		r=r+'0';
		str[i]=r;
		num=num/10;
	}
	if (flag==1)
	{
		str[i]='-';
		i++;
	}
	str[i]=0;
	string_reverse(str);
}