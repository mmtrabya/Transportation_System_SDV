/*
 * ============================================================================
 * MPU9250_interface.h
 * MPU9250 9-Axis IMU Driver Interface
 * Location: atmega32/HAL/IMU/MPU9250_interface.h
 * ============================================================================
 */

#ifndef MPU9250_INTERFACE_H_
#define MPU9250_INTERFACE_H_

#include "../../STD_TYPES.h"
#include "MPU9250_config.h"

/* ==================== Data Types ==================== */

/**
 * Accelerometer Range Options
 */
typedef enum {
    MPU9250_ACCEL_RANGE_2G = 0,   // ±2g
    MPU9250_ACCEL_RANGE_4G,       // ±4g
    MPU9250_ACCEL_RANGE_8G,       // ±8g
    MPU9250_ACCEL_RANGE_16G       // ±16g
} MPU9250_AccelRange_t;

/**
 * Gyroscope Range Options
 */
typedef enum {
    MPU9250_GYRO_RANGE_250DPS = 0,  // ±250 degrees/second
    MPU9250_GYRO_RANGE_500DPS,      // ±500 degrees/second
    MPU9250_GYRO_RANGE_1000DPS,     // ±1000 degrees/second
    MPU9250_GYRO_RANGE_2000DPS      // ±2000 degrees/second
} MPU9250_GyroRange_t;

/**
 * MPU9250 Status Codes
 */
typedef enum {
    MPU9250_OK = 0,
    MPU9250_ERROR,
    MPU9250_TIMEOUT,
    MPU9250_NOT_CONNECTED,
    MPU9250_MAG_ERROR
} MPU9250_Status_t;

/**
 * Complete IMU Data Structure
 */
typedef struct {
    /* Raw sensor values (16-bit) */
    s16 accel_raw_x, accel_raw_y, accel_raw_z;
    s16 gyro_raw_x, gyro_raw_y, gyro_raw_z;
    s16 mag_raw_x, mag_raw_y, mag_raw_z;
    s16 temp_raw;
    
    /* Calibrated sensor data */
    f32 accel_x, accel_y, accel_z;  // Acceleration in m/s²
    f32 gyro_x, gyro_y, gyro_z;     // Angular velocity in deg/s
    f32 mag_x, mag_y, mag_z;        // Magnetic field in µT
    f32 temperature;                 // Temperature in °C
    
    /* Orientation (Euler angles) */
    f32 roll;   // Rotation around X-axis (degrees)
    f32 pitch;  // Rotation around Y-axis (degrees)
    f32 yaw;    // Rotation around Z-axis (degrees)
    
    /* Calibration offsets */
    f32 accel_offset_x, accel_offset_y, accel_offset_z;
    f32 gyro_offset_x, gyro_offset_y, gyro_offset_z;
    f32 mag_offset_x, mag_offset_y, mag_offset_z;
    
    /* Magnetometer scaling factors */
    f32 mag_scale_x, mag_scale_y, mag_scale_z;
    
    /* Status flags */
    bool_t is_calibrated;
    bool_t mag_available;
    
} MPU9250_Data_t;


/* ==================== Core Functions ==================== */

/**
 * @brief Initialize MPU9250 sensor
 * @note I2C must be initialized before calling this function
 * @return MPU9250_Status_t initialization status
 */
MPU9250_Status_t MPU9250_Init(void);

/**
 * @brief Test MPU9250 connection
 * @return True if device is connected and responding
 */
bool_t MPU9250_TestConnection(void);

/**
 * @brief Read WHO_AM_I register
 * @return Device ID (should be 0x71 or 0x73)
 */
u8 MPU9250_GetDeviceID(void);


/* ==================== Configuration Functions ==================== */

/**
 * @brief Set accelerometer measurement range
 * @param range Accelerometer range (2g, 4g, 8g, 16g)
 */
void MPU9250_SetAccelRange(MPU9250_AccelRange_t range);

/**
 * @brief Set gyroscope measurement range
 * @param range Gyroscope range (250, 500, 1000, 2000 dps)
 */
void MPU9250_SetGyroRange(MPU9250_GyroRange_t range);

/**
 * @brief Set digital low-pass filter configuration
 * @param config DLPF configuration (0-6)
 */
void MPU9250_SetDLPF(u8 config);

/**
 * @brief Set sample rate divider
 * @param divider Sample rate divider (0-255)
 */
void MPU9250_SetSampleRate(u8 divider);


/* ==================== Data Reading Functions ==================== */

/**
 * @brief Read all sensor data (accel + gyro + mag + temp)
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_ReadAll(MPU9250_Data_t* data);

/**
 * @brief Read accelerometer data only
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_ReadAccel(MPU9250_Data_t* data);

/**
 * @brief Read gyroscope data only
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_ReadGyro(MPU9250_Data_t* data);

/**
 * @brief Read magnetometer data only
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_ReadMag(MPU9250_Data_t* data);

/**
 * @brief Read temperature sensor
 * @return Temperature in degrees Celsius
 */
f32 MPU9250_ReadTemperature(void);


/* ==================== Orientation Calculation ==================== */

/**
 * @brief Calculate roll, pitch, and yaw angles
 * @param data Pointer to MPU9250_Data_t structure
 * @note Updates roll, pitch, yaw fields in data structure
 */
void MPU9250_CalculateOrientation(MPU9250_Data_t* data);

/**
 * @brief Update orientation using complementary filter
 * @param data Pointer to MPU9250_Data_t structure
 * @param dt Time delta in seconds since last update
 */
void MPU9250_UpdateOrientation(MPU9250_Data_t* data, f32 dt);

/**
 * @brief Get roll angle from accelerometer
 * @param data Pointer to MPU9250_Data_t structure
 * @return Roll angle in degrees
 */
f32 MPU9250_GetRoll(MPU9250_Data_t* data);

/**
 * @brief Get pitch angle from accelerometer
 * @param data Pointer to MPU9250_Data_t structure
 * @return Pitch angle in degrees
 */
f32 MPU9250_GetPitch(MPU9250_Data_t* data);

/**
 * @brief Get yaw angle from magnetometer
 * @param data Pointer to MPU9250_Data_t structure
 * @return Yaw angle in degrees (0-360)
 */
f32 MPU9250_GetYaw(MPU9250_Data_t* data);


/* ==================== Calibration Functions ==================== */

/**
 * @brief Calibrate gyroscope (sensor must be stationary)
 * @param data Pointer to MPU9250_Data_t structure
 * @note Takes multiple samples and calculates offset
 */
void MPU9250_CalibrateGyro(MPU9250_Data_t* data);

/**
 * @brief Calibrate accelerometer
 * @param data Pointer to MPU9250_Data_t structure
 * @note Sensor should be placed flat for best results
 */
void MPU9250_CalibrateAccel(MPU9250_Data_t* data);

/**
 * @brief Calibrate magnetometer (hard iron calibration)
 * @param data Pointer to MPU9250_Data_t structure
 * @note Rotate sensor in figure-8 pattern during calibration
 */
void MPU9250_CalibrateMag(MPU9250_Data_t* data);

/**
 * @brief Perform full sensor calibration
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_CalibrateAll(MPU9250_Data_t* data);

/**
 * @brief Reset all calibration values to zero
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_ResetCalibration(MPU9250_Data_t* data);


/* ==================== Power Management ==================== */

/**
 * @brief Put sensor in sleep mode
 */
void MPU9250_Sleep(void);

/**
 * @brief Wake sensor from sleep mode
 */
void MPU9250_Wake(void);

/**
 * @brief Perform software reset
 */
void MPU9250_Reset(void);


/* ==================== Utility Functions ==================== */

/**
 * @brief Check if new data is available
 * @return True if new data is ready to be read
 */
bool_t MPU9250_DataReady(void);

/**
 * @brief Get magnetometer status
 * @return True if magnetometer is functioning properly
 */
bool_t MPU9250_MagReady(void);

/**
 * @brief Initialize data structure with default values
 * @param data Pointer to MPU9250_Data_t structure
 */
void MPU9250_InitData(MPU9250_Data_t* data);


#endif /* MPU9250_INTERFACE_H_ */