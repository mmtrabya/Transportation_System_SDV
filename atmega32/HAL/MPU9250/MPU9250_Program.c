/*
 * ============================================================================
 * MPU9250_program.c
 * MPU9250 9DoF IMU Driver Implementation
 * Location: atmega32/HAL/IMU/MPU9250_program.c
 * ============================================================================
 */

#include "MPU9250_interface.h"
#include "../../MCAL/TWI/TWI_interface.h"
#include <util/delay.h>
#include <math.h>

/* ==================== Register Definitions ==================== */

/* MPU9250 Registers */
#define MPU9250_WHO_AM_I        0x75
#define MPU9250_PWR_MGMT_1      0x6B
#define MPU9250_PWR_MGMT_2      0x6C
#define MPU9250_CONFIG          0x1A
#define MPU9250_GYRO_CONFIG     0x1B
#define MPU9250_ACCEL_CONFIG    0x1C
#define MPU9250_ACCEL_CONFIG2   0x1D
#define MPU9250_SMPLRT_DIV      0x19
#define MPU9250_INT_PIN_CFG     0x37
#define MPU9250_INT_ENABLE      0x38
#define MPU9250_INT_STATUS      0x3A
#define MPU9250_ACCEL_XOUT_H    0x3B
#define MPU9250_TEMP_OUT_H      0x41
#define MPU9250_GYRO_XOUT_H     0x43
#define MPU9250_USER_CTRL       0x6A

/* AK8963 Magnetometer Registers */
#define AK8963_I2C_ADDR         0x0C
#define AK8963_WHO_AM_I         0x00
#define AK8963_INFO             0x01
#define AK8963_ST1              0x02
#define AK8963_HXL              0x03
#define AK8963_ST2              0x09
#define AK8963_CNTL1            0x0A
#define AK8963_CNTL2            0x0B
#define AK8963_ASAX             0x10

/* Scale Factors */
#define ACCEL_SCALE_2G          16384.0f
#define ACCEL_SCALE_4G          8192.0f
#define ACCEL_SCALE_8G          4096.0f
#define ACCEL_SCALE_16G         2048.0f

#define GYRO_SCALE_250          131.0f
#define GYRO_SCALE_500          65.5f
#define GYRO_SCALE_1000         32.8f
#define GYRO_SCALE_2000         16.4f

#define MAG_SCALE               0.6f  // µT per LSB for 16-bit
#define TEMP_SCALE              333.87f
#define TEMP_OFFSET             21.0f

#define GRAVITY                 9.81f
#define RAD_TO_DEG              57.295779513f
#define DEG_TO_RAD              0.017453292f

/* ==================== Private Variables ==================== */

static f32 accel_scale = ACCEL_SCALE_2G;
static f32 gyro_scale = GYRO_SCALE_250;

/* ==================== Private Function Prototypes ==================== */

static void MPU9250_WriteReg(u8 reg, u8 value);
static u8 MPU9250_ReadReg(u8 reg);
static void MPU9250_ReadBytes(u8 reg, u8* buffer, u8 length);
static void AK8963_WriteReg(u8 reg, u8 value);
static u8 AK8963_ReadReg(u8 reg);
static void AK8963_ReadBytes(u8 reg, u8* buffer, u8 length);
static MPU9250_Status_t AK8963_Init(void);

/* ==================== Private Functions ==================== */

static void MPU9250_WriteReg(u8 reg, u8 value) {
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(MPU9250_I2C_ADDRESS);
    TWI_sendMasterDataByte(reg);
    TWI_sendMasterDataByte(value);
    TWI_sendStopCondition();
    _delay_us(10);
}

static u8 MPU9250_ReadReg(u8 reg) {
    u8 data;
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(MPU9250_I2C_ADDRESS);
    TWI_sendMasterDataByte(reg);
    TWI_sendRepStartCondition();
    TWI_sendSlaveAddWithRead(MPU9250_I2C_ADDRESS);
    TWI_receiveMasterDataByteNack(&data);
    TWI_sendStopCondition();
    return data;
}

static void MPU9250_ReadBytes(u8 reg, u8* buffer, u8 length) {
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(MPU9250_I2C_ADDRESS);
    TWI_sendMasterDataByte(reg);
    TWI_sendRepStartCondition();
    TWI_sendSlaveAddWithRead(MPU9250_I2C_ADDRESS);
    
    for (u8 i = 0; i < length - 1; i++) {
        TWI_receiveMasterDataByteAck(&buffer[i]);
    }
    TWI_receiveMasterDataByteNack(&buffer[length - 1]);
    TWI_sendStopCondition();
}

static void AK8963_WriteReg(u8 reg, u8 value) {
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(AK8963_I2C_ADDR);
    TWI_sendMasterDataByte(reg);
    TWI_sendMasterDataByte(value);
    TWI_sendStopCondition();
    _delay_us(10);
}

static u8 AK8963_ReadReg(u8 reg) {
    u8 data;
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(AK8963_I2C_ADDR);
    TWI_sendMasterDataByte(reg);
    TWI_sendRepStartCondition();
    TWI_sendSlaveAddWithRead(AK8963_I2C_ADDR);
    TWI_receiveMasterDataByteNack(&data);
    TWI_sendStopCondition();
    return data;
}

static void AK8963_ReadBytes(u8 reg, u8* buffer, u8 length) {
    TWI_sendStartCondition();
    TWI_sendSlaveAddWithWrite(AK8963_I2C_ADDR);
    TWI_sendMasterDataByte(reg);
    TWI_sendRepStartCondition();
    TWI_sendSlaveAddWithRead(AK8963_I2C_ADDR);
    
    for (u8 i = 0; i < length - 1; i++) {
        TWI_receiveMasterDataByteAck(&buffer[i]);
    }
    TWI_receiveMasterDataByteNack(&buffer[length - 1]);
    TWI_sendStopCondition();
}

static MPU9250_Status_t AK8963_Init(void) {
    u8 who_am_i;
    
    // Check AK8963 WHO_AM_I
    who_am_i = AK8963_ReadReg(AK8963_WHO_AM_I);
    if (who_am_i != 0x48) {
        return MPU9250_MAG_ERROR;
    }
    
    // Reset magnetometer
    AK8963_WriteReg(AK8963_CNTL2, 0x01);
    _delay_ms(10);
    
    // Set to power-down mode
    AK8963_WriteReg(AK8963_CNTL1, 0x00);
    _delay_ms(10);
    
    // Set to fuse ROM access mode to read sensitivity adjustment values
    AK8963_WriteReg(AK8963_CNTL1, 0x0F);
    _delay_ms(10);
    
    // Read sensitivity adjustment values (optional)
    // Can be used for better calibration
    
    // Set to power-down mode
    AK8963_WriteReg(AK8963_CNTL1, 0x00);
    _delay_ms(10);
    
    // Configure magnetometer for continuous measurement
    // 0x16 = 16-bit output, continuous mode 2 (100Hz)
    u8 mag_mode = AK8963_MODE;
    if (AK8963_BIT_OUTPUT_16BIT) {
        mag_mode |= 0x10;  // Add 16-bit flag
    }
    AK8963_WriteReg(AK8963_CNTL1, mag_mode);
    _delay_ms(10);
    
    return MPU9250_OK;
}

/* ==================== Public Functions ==================== */

MPU9250_Status_t MPU9250_Init(void) {
    // Note: TWI/I2C must be initialized before calling this function
    // Since it's shared with LCD, we don't initialize it here
    
    _delay_ms(100);
    
    // Test connection
    if (!MPU9250_TestConnection()) {
        return MPU9250_NOT_CONNECTED;
    }
    
    // Reset device
    MPU9250_WriteReg(MPU9250_PWR_MGMT_1, 0x80);
    _delay_ms(100);
    
    // Wake up device and set clock source
    MPU9250_WriteReg(MPU9250_PWR_MGMT_1, MPU9250_CLOCK_SOURCE);
    _delay_ms(10);
    
    // Enable all sensors
    MPU9250_WriteReg(MPU9250_PWR_MGMT_2, 0x00);
    _delay_ms(10);
    
    // Configure accelerometer
    MPU9250_SetAccelRange(MPU9250_DEFAULT_ACCEL_RANGE);
    
    // Configure gyroscope
    MPU9250_SetGyroRange(MPU9250_DEFAULT_GYRO_RANGE);
    
    // Configure DLPF
    MPU9250_SetDLPF(MPU9250_DLPF_CONFIG);
    
    // Set sample rate
    MPU9250_SetSampleRate(MPU9250_SAMPLE_RATE_DIV);
    
    // Enable bypass mode for magnetometer access
    MPU9250_WriteReg(MPU9250_INT_PIN_CFG, 0x02);
    _delay_ms(10);
    
    // Disable I2C master mode
    MPU9250_WriteReg(MPU9250_USER_CTRL, 0x00);
    _delay_ms(10);
    
    // Initialize magnetometer
    MPU9250_Status_t mag_status = AK8963_Init();
    if (mag_status != MPU9250_OK) {
        return mag_status;
    }
    
    return MPU9250_OK;
}

bool_t MPU9250_TestConnection(void) {
    u8 who_am_i = MPU9250_ReadReg(MPU9250_WHO_AM_I);
    return (who_am_i == 0x71 || who_am_i == 0x73);
}

u8 MPU9250_GetDeviceID(void) {
    return MPU9250_ReadReg(MPU9250_WHO_AM_I);
}

void MPU9250_SetAccelRange(MPU9250_AccelRange_t range) {
    MPU9250_WriteReg(MPU9250_ACCEL_CONFIG, range << 3);
    
    switch (range) {
        case MPU9250_ACCEL_RANGE_2G:
            accel_scale = ACCEL_SCALE_2G;
            break;
        case MPU9250_ACCEL_RANGE_4G:
            accel_scale = ACCEL_SCALE_4G;
            break;
        case MPU9250_ACCEL_RANGE_8G:
            accel_scale = ACCEL_SCALE_8G;
            break;
        case MPU9250_ACCEL_RANGE_16G:
            accel_scale = ACCEL_SCALE_16G;
            break;
    }
}

void MPU9250_SetGyroRange(MPU9250_GyroRange_t range) {
    MPU9250_WriteReg(MPU9250_GYRO_CONFIG, range << 3);
    
    switch (range) {
        case MPU9250_GYRO_RANGE_250DPS:
            gyro_scale = GYRO_SCALE_250;
            break;
        case MPU9250_GYRO_RANGE_500DPS:
            gyro_scale = GYRO_SCALE_500;
            break;
        case MPU9250_GYRO_RANGE_1000DPS:
            gyro_scale = GYRO_SCALE_1000;
            break;
        case MPU9250_GYRO_RANGE_2000DPS:
            gyro_scale = GYRO_SCALE_2000;
            break;
    }
}

void MPU9250_SetDLPF(u8 config) {
    if (config > 6) config = 6;
    MPU9250_WriteReg(MPU9250_CONFIG, config);
}

void MPU9250_SetSampleRate(u8 divider) {
    MPU9250_WriteReg(MPU9250_SMPLRT_DIV, divider);
}

void MPU9250_InitData(MPU9250_Data_t* data) {
    // Zero all raw values
    data->accel_raw_x = data->accel_raw_y = data->accel_raw_z = 0;
    data->gyro_raw_x = data->gyro_raw_y = data->gyro_raw_z = 0;
    data->mag_raw_x = data->mag_raw_y = data->mag_raw_z = 0;
    data->temp_raw = 0;
    
    // Zero all converted values
    data->accel_x = data->accel_y = data->accel_z = 0.0f;
    data->gyro_x = data->gyro_y = data->gyro_z = 0.0f;
    data->mag_x = data->mag_y = data->mag_z = 0.0f;
    data->temperature = 0.0f;
    
    // Zero orientation
    data->roll = data->pitch = data->yaw = 0.0f;
    
    // Zero calibration offsets
    data->accel_offset_x = data->accel_offset_y = data->accel_offset_z = 0.0f;
    data->gyro_offset_x = data->gyro_offset_y = data->gyro_offset_z = 0.0f;
    data->mag_offset_x = data->mag_offset_y = data->mag_offset_z = 0.0f;
    
    // Set default magnetometer scale to 1.0
    data->mag_scale_x = data->mag_scale_y = data->mag_scale_z = 1.0f;
    
    // Set flags
    data->is_calibrated = False;
    data->mag_available = True;
}

void MPU9250_ReadAccel(MPU9250_Data_t* data) {
    u8 raw_data[6];
    
    MPU9250_ReadBytes(MPU9250_ACCEL_XOUT_H, raw_data, 6);
    
    // Combine high and low bytes
    data->accel_raw_x = (s16)((raw_data[0] << 8) | raw_data[1]);
    data->accel_raw_y = (s16)((raw_data[2] << 8) | raw_data[3]);
    data->accel_raw_z = (s16)((raw_data[4] << 8) | raw_data[5]);
    
    // Convert to m/s² and apply calibration
    data->accel_x = ((f32)data->accel_raw_x / accel_scale) * GRAVITY - data->accel_offset_x;
    data->accel_y = ((f32)data->accel_raw_y / accel_scale) * GRAVITY - data->accel_offset_y;
    data->accel_z = ((f32)data->accel_raw_z / accel_scale) * GRAVITY - data->accel_offset_z;
}

void MPU9250_ReadGyro(MPU9250_Data_t* data) {
    u8 raw_data[6];
    
    MPU9250_ReadBytes(MPU9250_GYRO_XOUT_H, raw_data, 6);
    
    // Combine high and low bytes
    data->gyro_raw_x = (s16)((raw_data[0] << 8) | raw_data[1]);
    data->gyro_raw_y = (s16)((raw_data[2] << 8) | raw_data[3]);
    data->gyro_raw_z = (s16)((raw_data[4] << 8) | raw_data[5]);
    
    // Convert to deg/s and apply calibration
    data->gyro_x = ((f32)data->gyro_raw_x / gyro_scale) - data->gyro_offset_x;
    data->gyro_y = ((f32)data->gyro_raw_y / gyro_scale) - data->gyro_offset_y;
    data->gyro_z = ((f32)data->gyro_raw_z / gyro_scale) - data->gyro_offset_z;
}

void MPU9250_ReadMag(MPU9250_Data_t* data) {
    u8 raw_data[7];
    u8 st1, st2;
    
    // Check if data is ready
    st1 = AK8963_ReadReg(AK8963_ST1);
    if ((st1 & 0x01) == 0) {
        return;  // Data not ready
    }
    
    // Read magnetometer data
    AK8963_ReadBytes(AK8963_HXL, raw_data, 7);
    
    // Check for magnetic sensor overflow
    st2 = raw_data[6];
    if (st2 & 0x08) {
        return;  // Overflow occurred
    }
    
    // Combine bytes (magnetometer is little-endian)
    data->mag_raw_x = (s16)((raw_data[1] << 8) | raw_data[0]);
    data->mag_raw_y = (s16)((raw_data[3] << 8) | raw_data[2]);
    data->mag_raw_z = (s16)((raw_data[5] << 8) | raw_data[4]);
    
    // Convert to µT and apply calibration
    data->mag_x = ((f32)data->mag_raw_x * MAG_SCALE - data->mag_offset_x) * data->mag_scale_x;
    data->mag_y = ((f32)data->mag_raw_y * MAG_SCALE - data->mag_offset_y) * data->mag_scale_y;
    data->mag_z = ((f32)data->mag_raw_z * MAG_SCALE - data->mag_offset_z) * data->mag_scale_z;
}

f32 MPU9250_ReadTemperature(void) {
    u8 raw_data[2];
    s16 temp_raw;
    
    MPU9250_ReadBytes(MPU9250_TEMP_OUT_H, raw_data, 2);
    temp_raw = (s16)((raw_data[0] << 8) | raw_data[1]);
    
    // Convert to Celsius
    return ((f32)temp_raw / TEMP_SCALE) + TEMP_OFFSET;
}

void MPU9250_ReadAll(MPU9250_Data_t* data) {
    MPU9250_ReadAccel(data);
    MPU9250_ReadGyro(data);
    MPU9250_ReadMag(data);
    data->temperature = MPU9250_ReadTemperature();
    MPU9250_CalculateOrientation(data);
}

f32 MPU9250_GetRoll(MPU9250_Data_t* data) {
    return atan2f(data->accel_y, data->accel_z) * RAD_TO_DEG;
}

f32 MPU9250_GetPitch(MPU9250_Data_t* data) {
    return atan2f(-data->accel_x, sqrtf(data->accel_y * data->accel_y + 
                                         data->accel_z * data->accel_z)) * RAD_TO_DEG;
}

f32 MPU9250_GetYaw(MPU9250_Data_t* data) {
    f32 yaw;
    f32 roll_rad = data->roll * DEG_TO_RAD;
    f32 pitch_rad = data->pitch * DEG_TO_RAD;
    
    // Tilt compensated yaw
    f32 mag_x_comp = data->mag_x * cosf(pitch_rad) + 
                     data->mag_z * sinf(pitch_rad);
    f32 mag_y_comp = data->mag_x * sinf(roll_rad) * sinf(pitch_rad) + 
                     data->mag_y * cosf(roll_rad) - 
                     data->mag_z * sinf(roll_rad) * cosf(pitch_rad);
    
    yaw = atan2f(mag_y_comp, mag_x_comp) * RAD_TO_DEG;
    
    // Convert to 0-360 range
    if (yaw < 0) {
        yaw += 360.0f;
    }
    
    return yaw;
}

void MPU9250_CalculateOrientation(MPU9250_Data_t* data) {
    // Calculate roll and pitch from accelerometer
    data->roll = MPU9250_GetRoll(data);
    data->pitch = MPU9250_GetPitch(data);
    
    // Calculate yaw from magnetometer if enabled
    #if MPU9250_USE_MAG_YAW
    if (data->mag_available) {
        data->yaw = MPU9250_GetYaw(data);
    }
    #endif
}

void MPU9250_UpdateOrientation(MPU9250_Data_t* data, f32 dt) {
    #if MPU9250_USE_COMPLEMENTARY_FILTER
    // Get accelerometer angles
    f32 accel_roll = MPU9250_GetRoll(data);
    f32 accel_pitch = MPU9250_GetPitch(data);
    
    // Integrate gyroscope
    data->roll += data->gyro_x * dt;
    data->pitch += data->gyro_y * dt;
    data->yaw += data->gyro_z * dt;
    
    // Apply complementary filter
    data->roll = MPU9250_FILTER_ALPHA * data->roll + 
                 (1.0f - MPU9250_FILTER_ALPHA) * accel_roll;
    data->pitch = MPU9250_FILTER_ALPHA * data->pitch + 
                  (1.0f - MPU9250_FILTER_ALPHA) * accel_pitch;
    
    // Update yaw from magnetometer
    #if MPU9250_USE_MAG_YAW
    if (data->mag_available) {
        f32 mag_yaw = MPU9250_GetYaw(data);
        data->yaw = MPU9250_FILTER_ALPHA * data->yaw + 
                    (1.0f - MPU9250_FILTER_ALPHA) * mag_yaw;
    }
    #endif
    
    // Keep yaw in 0-360 range
    if (data->yaw < 0) data->yaw += 360.0f;
    if (data->yaw >= 360.0f) data->yaw -= 360.0f;
    
    #else
    // Simple calculation without filter
    MPU9250_CalculateOrientation(data);
    #endif
}

void MPU9250_CalibrateGyro(MPU9250_Data_t* data) {
    f32 sum_x = 0, sum_y = 0, sum_z = 0;
    u16 samples = MPU9250_GYRO_CALIB_SAMPLES;
    
    for (u16 i = 0; i < samples; i++) {
        MPU9250_ReadGyro(data);
        sum_x += data->gyro_x + data->gyro_offset_x;  // Add back offset
        sum_y += data->gyro_y + data->gyro_offset_y;
        sum_z += data->gyro_z + data->gyro_offset_z;
        _delay_ms(2);
    }
    
    data->gyro_offset_x = sum_x / (f32)samples;
    data->gyro_offset_y = sum_y / (f32)samples;
    data->gyro_offset_z = sum_z / (f32)samples;
}

void MPU9250_CalibrateAccel(MPU9250_Data_t* data) {
    f32 sum_x = 0, sum_y = 0, sum_z = 0;
    u16 samples = MPU9250_ACCEL_CALIB_SAMPLES;
    
    for (u16 i = 0; i < samples; i++) {
        MPU9250_ReadAccel(data);
        sum_x += data->accel_x + data->accel_offset_x;
        sum_y += data->accel_y + data->accel_offset_y;
        sum_z += data->accel_z + data->accel_offset_z;
        _delay_ms(2);
    }
    
    data->accel_offset_x = sum_x / (f32)samples;
    data->accel_offset_y = sum_y / (f32)samples;
    data->accel_offset_z = (sum_z / (f32)samples) - GRAVITY;  // Subtract 1g
}

void MPU9250_CalibrateMag(MPU9250_Data_t* data) {
    f32 mag_max_x = -32768, mag_max_y = -32768, mag_max_z = -32768;
    f32 mag_min_x = 32767, mag_min_y = 32767, mag_min_z = 32767;
    u16 samples = MPU9250_MAG_CALIB_SAMPLES;
    
    for (u16 i = 0; i < samples; i++) {
        MPU9250_ReadMag(data);
        
        if (data->mag_x > mag_max_x) mag_max_x = data->mag_x;
        if (data->mag_x < mag_min_x) mag_min_x = data->mag_x;
        if (data->mag_y > mag_max_y) mag_max_y = data->mag_y;
        if (data->mag_y < mag_min_y) mag_min_y = data->mag_y;
        if (data->mag_z > mag_max_z) mag_max_z = data->mag_z;
        if (data->mag_z < mag_min_z) mag_min_z = data->mag_z;
        
        _delay_ms(10);
    }
    
    // Calculate hard iron offset
    data->mag_offset_x = (mag_max_x + mag_min_x) / 2.0f;
    data->mag_offset_y = (mag_max_y + mag_min_y) / 2.0f;
    data->mag_offset_z = (mag_max_z + mag_min_z) / 2.0f;
    
    // Calculate soft iron scale
    f32 avg_delta = ((mag_max_x - mag_min_x) + (mag_max_y - mag_min_y) + 
                     (mag_max_z - mag_min_z)) / 3.0f;
    
    data->mag_scale_x = avg_delta / (mag_max_x - mag_min_x);
    data->mag_scale_y = avg_delta / (mag_max_y - mag_min_y);
    data->mag_scale_z = avg_delta / (mag_max_z - mag_min_z);
}

void MPU9250_CalibrateAll(MPU9250_Data_t* data) {
    MPU9250_CalibrateGyro(data);
    MPU9250_CalibrateAccel(data);
    MPU9250_CalibrateMag(data);
    data->is_calibrated = True;
}

void MPU9250_ResetCalibration(MPU9250_Data_t* data) {
    data->accel_offset_x = data->accel_offset_y = data->accel_offset_z = 0.0f;
    data->gyro_offset_x = data->gyro_offset_y = data->gyro_offset_z = 0.0f;
    data->mag_offset_x = data->mag_offset_y = data->mag_offset_z = 0.0f;
    data->mag_scale_x = data->mag_scale_y = data->mag_scale_z = 1.0f;
    data->is_calibrated = False;
}

void MPU9250_Sleep(void) {
    u8 pwr_mgmt = MPU9250_ReadReg(MPU9250_PWR_MGMT_1);
    MPU9250_WriteReg(MPU9250_PWR_MGMT_1, pwr_mgmt | 0x40);
}

void MPU9250_Wake(void) {
    u8 pwr_mgmt = MPU9250_ReadReg(MPU9250_PWR_MGMT_1);
    MPU9250_WriteReg(MPU9250_PWR_MGMT_1, pwr_mgmt & ~0x40);
    _delay_ms(10);
}

void MPU9250_Reset(void) {
    MPU9250_WriteReg(MPU9250_PWR_MGMT_1, 0x80);
    _delay_ms(100);
}

bool_t MPU9250_DataReady(void) {
    u8 status = MPU9250_ReadReg(MPU9250_INT_STATUS);
    return (status & 0x01) ? True : False;
}

bool_t MPU9250_MagReady(void) {
    u8 st1 = AK8963_ReadReg(AK8963_ST1);
    return (st1 & 0x01) ? True : False;
}

/* ==================== End of File ==================== */