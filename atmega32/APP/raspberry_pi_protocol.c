/*
 * raspberry_pi_protocol.c
 * Implementation of Raspberry Pi communication protocol
 * 
 * Location: atmega32/APP/raspberry_pi_protocol.c
 * 
 * GPS REMOVED - Connected directly to Raspberry Pi 5
 * Integrates: IMU (MPU9250), Motors (L298N), Ultrasonic sensors
 */

#include "raspberry_pi_protocol.h"
#include "../Application.h"

/* Forward declaration */
static void Protocol_ProcessCommand(u8 cmd, const u8* data, u8 length);

/* ==================== STATE MACHINE ==================== */

static enum {
    STATE_IDLE,
    STATE_CMD,
    STATE_LENGTH,
    STATE_DATA,
    STATE_CHECKSUM
} rx_state = STATE_IDLE;

static u8 rx_cmd;
static u8 rx_length;
static u8 rx_data[MAX_DATA_LENGTH];
static u8 rx_index;
static u8 rx_checksum;

/* ==================== SENSOR DATA STORAGE ==================== */

static IMU_Data_t current_imu;
static Ultrasonic_Data_t current_ultrasonic;
static System_Status_t system_status;

/* Timer for system uptime */
static u32 system_uptime = 0;

/* ==================== INITIALIZATION ==================== */

void Protocol_Init(void) {
    // Initialize UART for Raspberry Pi communication (115200 baud)
    UART_Init();
    
    // Initialize I2C for IMU sensor
    TWI_initMaster();
    
    // Initialize MPU9250 (accelerometer + gyroscope + magnetometer)
    MPU9250_Data_t mpu_data;
    MPU9250_InitData(&mpu_data);
    
    if (MPU9250_Init() != MPU9250_OK) {
        system_status.errors++;
    }
    _delay_ms(100);
    
    // Initialize motors
    DCM_Init_All();
    
    // Initialize ultrasonic sensors
    ULTRAS_INITI();
    
    // Initialize buzzer and LEDs
    BUZZER_Init();
    LED_Init();
    
    // Initialize system status
    system_status.uptime = 0;
    system_status.battery_voltage = 0.0;
    system_status.cpu_load = 0;
    system_status.errors = 0;
    
    // Reset protocol state machine
    rx_state = STATE_IDLE;
    rx_index = 0;
    
    // Initial LED indication - system ready
    LED_ON(GREEN_LED_PIN);
    _delay_ms(500);
    LED_OFF(GREEN_LED_PIN);
}

/* ==================== PACKET PROCESSING ==================== */

void Protocol_ProcessByte(u8 byte) {
    switch (rx_state) {
        case STATE_IDLE:
            if (byte == START_BYTE) {
                rx_state = STATE_CMD;
            }
            break;
            
        case STATE_CMD:
            rx_cmd = byte;
            rx_state = STATE_LENGTH;
            break;
            
        case STATE_LENGTH:
            rx_length = byte;
            if (rx_length > MAX_DATA_LENGTH) {
                rx_state = STATE_IDLE;  // Invalid length
            } else if (rx_length == 0) {
                rx_state = STATE_CHECKSUM;  // No data
            } else {
                rx_index = 0;
                rx_state = STATE_DATA;
            }
            break;
            
        case STATE_DATA:
            rx_data[rx_index++] = byte;
            if (rx_index >= rx_length) {
                rx_state = STATE_CHECKSUM;
            }
            break;
            
        case STATE_CHECKSUM:
            rx_checksum = byte;
            // Verify checksum
            u8 calculated = Protocol_CalculateChecksum(rx_cmd, rx_length, rx_data);
            if (calculated == rx_checksum) {
                // Process command
                Protocol_ProcessCommand(rx_cmd, rx_data, rx_length);
            } else {
                // Checksum error
                Protocol_SendNack();
            }
            rx_state = STATE_IDLE;
            break;
    }
}

static void Protocol_ProcessCommand(u8 cmd, const u8* data, u8 length) {
    switch (cmd) {
        case CMD_MOTOR_SET_SPEED:
            if (length == 2) {
                Motor_Speed_t* speed = (Motor_Speed_t*)data;
                Handle_MotorSetSpeed(speed->left_speed, speed->right_speed);
                Protocol_SendAck();
            } else {
                Protocol_SendNack();
            }
            break;
            
        case CMD_MOTOR_STOP:
            Handle_MotorStop();
            Protocol_SendAck();
            break;
            
        case CMD_MOTOR_EMERGENCY_STOP:
            Handle_EmergencyStop();
            Protocol_SendAck();
            break;
            
        case CMD_IMU_REQUEST:
            Handle_IMURequest();
            break;
            
        case CMD_ULTRASONIC_REQUEST:
            Handle_UltrasonicRequest();
            break;
            
        case CMD_ALL_SENSORS_REQUEST:
            Handle_IMURequest();
            _delay_ms(10);
            Handle_UltrasonicRequest();
            break;
            
        case CMD_SYSTEM_STATUS:
            Handle_SystemStatusRequest();
            break;
            
        case CMD_LED_CONTROL:
            if (length == 1) {
                Handle_LEDControl(data[0]);
                Protocol_SendAck();
            } else {
                Protocol_SendNack();
            }
            break;
            
        case CMD_BUZZER_CONTROL:
            if (length == 1) {
                Handle_BuzzerControl(data[0]);
                Protocol_SendAck();
            } else {
                Protocol_SendNack();
            }
            break;
            
        case CMD_RESET:
            Handle_Reset();
            break;
            
        default:
            Protocol_SendNack();
            break;
    }
}

/* ==================== SENDING FUNCTIONS ==================== */

bool Protocol_SendPacket(u8 cmd, const u8* data, u8 length) {
    if (length > MAX_DATA_LENGTH) {
        return false;
    }
    
    // Send START byte
    UART_SendByte(START_BYTE);
    
    // Send command
    UART_SendByte(cmd);
    
    // Send length
    UART_SendByte(length);
    
    // Send data
    for (u8 i = 0; i < length; i++) {
        UART_SendByte(data[i]);
    }
    
    // Calculate and send checksum
    u8 checksum = Protocol_CalculateChecksum(cmd, length, data);
    UART_SendByte(checksum);
    
    // Send END byte
    UART_SendByte(END_BYTE);
    
    return true;
}

void Protocol_SendAck(void) {
    Protocol_SendPacket(RESP_ACK, NULL, 0);
}

void Protocol_SendNack(void) {
    Protocol_SendPacket(RESP_NACK, NULL, 0);
}

void Protocol_SendIMUData(const IMU_Data_t* imu) {
    Protocol_SendPacket(RESP_IMU_DATA, (const u8*)imu, sizeof(IMU_Data_t));
}

void Protocol_SendUltrasonicData(const Ultrasonic_Data_t* ultrasonic) {
    Protocol_SendPacket(RESP_ULTRASONIC_DATA, (const u8*)ultrasonic, sizeof(Ultrasonic_Data_t));
}

void Protocol_SendSystemStatus(const System_Status_t* status) {
    Protocol_SendPacket(RESP_SYSTEM_STATUS, (const u8*)status, sizeof(System_Status_t));
}

u8 Protocol_CalculateChecksum(u8 cmd, u8 length, const u8* data) {
    u8 checksum = cmd + length;
    
    for (u8 i = 0; i < length; i++) {
        checksum += data[i];
    }
    
    return checksum;
}

/* ==================== COMMAND HANDLERS ==================== */

void Handle_MotorSetSpeed(int8_t left, int8_t right) {
    // Convert -100 to 100 range to motor control
    // Positive = forward, Negative = backward
    
    if (left >= 0) {
        DCM_Group1_Speed((u8)left, DCM_CW);  // Left side forward
    } else {
        DCM_Group1_Speed((u8)(-left), DCM_CCW);  // Left side backward
    }
    
    if (right >= 0) {
        DCM_Group2_Speed((u8)right, DCM_CW);  // Right side forward
    } else {
        DCM_Group2_Speed((u8)(-right), DCM_CCW);  // Right side backward
    }
}

void Handle_MotorStop(void) {
    DCM_Stop();
}

void Handle_EmergencyStop(void) {
    DCM_Stop();
    // Flash red LED for emergency indication
    LED_ON(RED_LED_PIN);
}

void Handle_IMURequest(void) {
    // Read MPU9250 (accelerometer + gyroscope + magnetometer)
    MPU9250_Data_t mpu_data;
    MPU9250_InitData(&mpu_data);
    
    // Read all sensor data
    MPU9250_ReadAll(&mpu_data);
    
    // Fill IMU data structure
    current_imu.accel_x = mpu_data.accel_x;
    current_imu.accel_y = mpu_data.accel_y;
    current_imu.accel_z = mpu_data.accel_z;
    
    current_imu.gyro_x = mpu_data.gyro_x;
    current_imu.gyro_y = mpu_data.gyro_y;
    current_imu.gyro_z = mpu_data.gyro_z;
    
    current_imu.mag_x = mpu_data.mag_x;
    current_imu.mag_y = mpu_data.mag_y;
    current_imu.mag_z = mpu_data.mag_z;
    
    current_imu.roll = mpu_data.roll;
    current_imu.pitch = mpu_data.pitch;
    current_imu.yaw = mpu_data.yaw;
    
    // Send to Raspberry Pi
    Protocol_SendIMUData(&current_imu);
}

void Handle_UltrasonicRequest(void) {
    // Read all 4 ultrasonic sensors
    f32 distance;
    
    // Front sensor
    ULTRAS_Read(&distance, ULTRASONIC1_TRIG_PIN);
    current_ultrasonic.front = (distance >= 0) ? distance : 400.0;
    
    _delay_ms(50);  // Delay between readings
    
    // Rear sensor
    ULTRAS_Read(&distance, ULTRASONIC2_TRIG_PIN);
    current_ultrasonic.rear = (distance >= 0) ? distance : 400.0;
    
    _delay_ms(50);
    
    // Left sensor
    ULTRAS_Read(&distance, ULTRASONIC3_TRIG_PIN);
    current_ultrasonic.left = (distance >= 0) ? distance : 400.0;
    
    _delay_ms(50);
    
    // Right sensor
    ULTRAS_Read(&distance, ULTRASONIC4_TRIG_PIN);
    current_ultrasonic.right = (distance >= 0) ? distance : 400.0;
    
    // Send to Raspberry Pi
    Protocol_SendUltrasonicData(&current_ultrasonic);
}

void Handle_SystemStatusRequest(void) {
    // Update system status
    system_status.uptime = system_uptime;
    
    // Read battery voltage (if connected to ADC)
    // ADC_Read(ADC_Channle_0);  // Uncomment if battery monitoring connected
    system_status.battery_voltage = 12.0;  // Placeholder
    
    system_status.cpu_load = 50;  // Placeholder - can implement actual measurement
    
    // Send to Raspberry Pi
    Protocol_SendSystemStatus(&system_status);
}

void Handle_LEDControl(u8 state) {
    if (state) {
        LED_ON(BLUE_LED_PIN);
    } else {
        LED_OFF(BLUE_LED_PIN);
    }
}

void Handle_BuzzerControl(u8 state) {
    if (state) {
        BUZZER_ON();
    } else {
        BUZZER_OFF();
    }
}

void Handle_Reset(void) {
    // Send acknowledgment before reset
    Protocol_SendAck();
    _delay_ms(100);
    
    // Perform software reset
    // Enable watchdog with shortest timeout
    WDT_Enable(WDT_16300_us);
    while(1);  // Wait for watchdog reset
}

/* ==================== UTILITY FUNCTIONS ==================== */

void Protocol_UpdateUptime(void) {
    // Call this function every second from main loop or timer interrupt
    system_uptime++;
}