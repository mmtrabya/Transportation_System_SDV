/*
 * ============================================================================
 * MPU9250_config.h
 * MPU9250 Configuration File
 * Location: atmega32/HAL/IMU/MPU9250_config.h
 * ============================================================================
 */

#ifndef MPU9250_CONFIG_H_
#define MPU9250_CONFIG_H_

/* ==================== I2C Configuration ==================== */

/**
 * MPU9250 I2C Address Selection
 * 0x68: AD0 pin LOW (default)
 * 0x69: AD0 pin HIGH
 */
#define MPU9250_I2C_ADDRESS         0x68

/**
 * I2C Timeout (milliseconds)
 */
#define MPU9250_I2C_TIMEOUT         1000


/* ==================== Sensor Range Configuration ==================== */

/**
 * Default Accelerometer Range
 * Options: MPU9250_ACCEL_RANGE_2G
 *          MPU9250_ACCEL_RANGE_4G
 *          MPU9250_ACCEL_RANGE_8G
 *          MPU9250_ACCEL_RANGE_16G
 */
#define MPU9250_DEFAULT_ACCEL_RANGE     MPU9250_ACCEL_RANGE_2G

/**
 * Default Gyroscope Range
 * Options: MPU9250_GYRO_RANGE_250DPS
 *          MPU9250_GYRO_RANGE_500DPS
 *          MPU9250_GYRO_RANGE_1000DPS
 *          MPU9250_GYRO_RANGE_2000DPS
 */
#define MPU9250_DEFAULT_GYRO_RANGE      MPU9250_GYRO_RANGE_250DPS


/* ==================== Filter Configuration ==================== */

/**
 * Digital Low Pass Filter (DLPF) Configuration
 * Affects both accelerometer and gyroscope
 * 
 * Value | Accel BW | Gyro BW  | Delay
 * ------|----------|----------|-------
 *   0   | 460 Hz   | 250 Hz   | 0.97ms
 *   1   | 184 Hz   | 184 Hz   | 2.9ms
 *   2   | 92 Hz    | 92 Hz    | 3.9ms
 *   3   | 41 Hz    | 41 Hz    | 5.9ms
 *   4   | 20 Hz    | 20 Hz    | 9.9ms
 *   5   | 10 Hz    | 10 Hz    | 17.85ms
 *   6   | 5 Hz     | 5 Hz     | 33.48ms
 */
#define MPU9250_DLPF_CONFIG             3  // 41 Hz bandwidth


/* ==================== Sample Rate Configuration ==================== */

/**
 * Sample Rate Divider
 * Sample Rate = Internal_Sample_Rate / (1 + SMPLRT_DIV)
 * Internal_Sample_Rate = 1kHz (when DLPF is enabled)
 * 
 * Example: SMPLRT_DIV = 9 → Sample Rate = 1000/(1+9) = 100Hz
 */
#define MPU9250_SAMPLE_RATE_DIV         9  // 100 Hz sample rate


/* ==================== Magnetometer Configuration ==================== */

/**
 * AK8963 Magnetometer Mode
 * 0x00: Power-down mode
 * 0x01: Single measurement mode
 * 0x02: Continuous measurement mode 1 (8Hz)
 * 0x06: Continuous measurement mode 2 (100Hz)
 * 0x04: External trigger measurement mode
 * 0x08: Self-test mode
 * 0x0F: Fuse ROM access mode
 */
#define AK8963_MODE                     0x06  // Continuous 100Hz

/**
 * AK8963 Output Bit Setting
 * 0: 14-bit output
 * 1: 16-bit output (adds bit 4 to mode)
 */
#define AK8963_BIT_OUTPUT_16BIT         1     // Use 16-bit


/* ==================== Calibration Configuration ==================== */

/**
 * Number of samples for gyroscope calibration
 */
#define MPU9250_GYRO_CALIB_SAMPLES      1000

/**
 * Number of samples for accelerometer calibration
 */
#define MPU9250_ACCEL_CALIB_SAMPLES     1000

/**
 * Number of samples for magnetometer calibration
 */
#define MPU9250_MAG_CALIB_SAMPLES       500

/**
 * Enable/Disable automatic calibration on init
 * 1: Enable automatic calibration
 * 0: Manual calibration required
 */
#define MPU9250_AUTO_CALIBRATE          0


/* ==================== Interrupt Configuration ==================== */

/**
 * Enable Data Ready Interrupt
 * 1: Enable
 * 0: Disable
 */
#define MPU9250_ENABLE_INT              0

/**
 * Interrupt Pin Configuration
 * Bit 7: INT_LEVEL (0=active high, 1=active low)
 * Bit 6: INT_OPEN (0=push-pull, 1=open-drain)
 * Bit 5: LATCH_INT_EN (0=50us pulse, 1=held until cleared)
 * Bit 4: INT_RD_CLEAR (0=status bits cleared on any read, 1=only by reading INT_STATUS)
 */
#define MPU9250_INT_PIN_CONFIG          0x00


/* ==================== Power Management ==================== */

/**
 * Clock Source Selection
 * 0: Internal 8MHz oscillator
 * 1: PLL with X axis gyroscope reference
 * 2: PLL with Y axis gyroscope reference
 * 3: PLL with Z axis gyroscope reference
 * 4: PLL with external 32.768kHz reference
 * 5: PLL with external 19.2MHz reference
 * 6: Reserved
 * 7: Stops the clock and keeps timing generator in reset
 */
#define MPU9250_CLOCK_SOURCE            1  // PLL with X-gyro


/* ==================== Temperature Sensor ==================== */

/**
 * Enable Temperature Sensor
 * 1: Enable
 * 0: Disable (saves power)
 */
#define MPU9250_ENABLE_TEMP_SENSOR      1


/* ==================== Advanced Features ==================== */

/**
 * Enable Complementary Filter for Orientation
 * 1: Use complementary filter (gyro + accel)
 * 0: Use only accelerometer for tilt
 */
#define MPU9250_USE_COMPLEMENTARY_FILTER    1

/**
 * Complementary Filter Alpha (0.0 to 1.0)
 * Higher value = trust gyro more
 * Lower value = trust accel more
 * Typical: 0.98 for dt=10ms
 */
#define MPU9250_FILTER_ALPHA            0.98f

/**
 * Enable Magnetometer for Yaw Calculation
 * 1: Calculate yaw from magnetometer
 * 0: Yaw from gyro integration only
 */
#define MPU9250_USE_MAG_YAW             1


/* ==================== Debug Configuration ==================== */

/**
 * Enable Debug Output
 * 1: Enable (requires UART/LCD for output)
 * 0: Disable
 */
#define MPU9250_DEBUG                   0


#endif /* MPU9250_CONFIG_H_ */