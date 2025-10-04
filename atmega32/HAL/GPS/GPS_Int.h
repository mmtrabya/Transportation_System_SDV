
#ifndef GPS_INT_H_
#define GPS_INT_H_
#include "../../STD_TYPES.h"
#include "../../MCAL/String/String.h"
#include "../../MCAL/UART/UART_interface.h"
#include <math.h> 


typedef struct {
	u8 time[10];
	f64 latitude ;
	f64 longitude;
	bool_t valid;
	f64 speed;  
	f64 course; 
} GPSData;

void GPS_Init(void);
bool_t GPS_ReadData(GPSData* data);
f64 GPS_Distance(f64 lat1, f64 lon1, f64 lat2, f64 lon2);
float convertToDecimal(float nmea);

#endif /* GPS_INT_H_*/