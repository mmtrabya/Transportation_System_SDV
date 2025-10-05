/*
 * raspberry_pi_protocol.h
 * Communication protocol with Raspberry Pi
 * 
 * Location: ATmega32_Project/APP/raspberry_pi_protocol.h
 * 
 * This header defines the protocol for communicating with Raspberry Pi
 * Give this file to your teammate for ATmega32 implementation
 */

#ifndef RASPBERRY_PI_PROTOCOL_H
#define RASPBERRY_PI_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>

/* ==================== PROTOCOL CONSTANTS ==================== */

#define START_BYTE              0xAA
#define END_BYTE                0x55
#define MAX_DATA_LENGTH         64
#define PACKET_OVERHEAD         5  // START + CMD + LEN + CHECKSUM + END

/* ==================== COMMAND CODES ==================== */

/* Motor Control Commands (0x01 - 0x0F) */
#define CMD_MOTOR_SET_SPEED         0x01
#define CMD_MOTOR_STOP              0x02
#define CMD_MOTOR_EMERGENCY_STOP    0x03

/* Sensor Request Commands (0x10 - 0x1F) */
#define CMD_GPS_REQUEST             0x10
#define CMD_IMU_REQUEST             0x11
#define CMD_ULTRASONIC_REQUEST      0x12
#define CMD_ALL_SENSORS_REQUEST     0x13

/* System Control Commands (0x20 - 0x2F) */
#define CMD_LED_CONTROL             0x20
#define CMD_BUZZER_CONTROL          0x21
#define CMD_SYSTEM_STATUS           0x22
#define CMD_RESET                   0x23

/* Response Codes (0xA0 - 0xBF) */
#define RESP_ACK                    0xA0
#define RESP_NACK                   0xA1
#define RESP_GPS_DATA               0xB0
#define RESP_IMU_DATA               0xB1
#define RESP_ULTRASONIC_DATA        0xB2
#define RESP_ALL_SENSORS_DATA       0xB3
#define RESP_SYSTEM_STATUS          0xB4

/* ==================== DATA STRUCTURES ==================== */

/**
 * Packet structure
 * Total size: 5 + data_length bytes
 */
typedef struct {
    uint8_t start;      // START_BYTE (0xAA)
    uint8_t cmd;        // Command code
    uint8_t length;     // Data length (0-64)
    uint8_t data[MAX_DATA_LENGTH];  // Payload
    uint8_t checksum;   // Checksum
    uint8_t end;        // END_BYTE (0x55)
} Packet_t;

/**
 * GPS Data structure
 * Size: 19 bytes
 */
typedef struct {
    float latitude;     // Decimal degrees
    float longitude;    // Decimal degrees
    float altitude;     // Meters
    float speed;        // km/h
    uint8_t satellites; // Number of satellites
    uint8_t fix_quality;// GPS fix quality (0-2)
    uint8_t valid;      // 1 if GPS has valid fix, 0 otherwise
} __attribute__((packed)) GPS_Data_t;

/**
 * IMU 9DOF Data structure
 * Size: 48 bytes (12 floats)
 */
typedef struct {
    // Accelerometer (m/s²)
    float accel_x;
    float accel_y;
    float accel_z;
    
    // Gyroscope (deg/s)
    float gyro_x;
    float gyro_y;
    float gyro_z;
    
    // Magnetometer (µT)
    float mag_x;
    float mag_y;
    float mag_z;
    
    // Calculated orientation (degrees)
    float roll;
    float pitch;
    float yaw;
} __attribute__((packed)) IMU_Data_t;

/**
 * Ultrasonic sensor data
 * Size: 16 bytes (4 floats)
 */
typedef struct {
    float front;    // Distance in cm
    float rear;     // Distance in cm
    float left;     // Distance in cm
    float right;    // Distance in cm
} __attribute__((packed)) Ultrasonic_Data_t;

/**
 * System status
 * Size: 10 bytes
 */
typedef struct {
    uint32_t uptime;        // Seconds since boot
    float battery_voltage;  // Volts
    uint8_t cpu_load;       // Percentage (0-100)
    uint8_t errors;         // Error count
} __attribute__((packed)) System_Status_t;

/**
 * Motor speed command
 * Size: 2 bytes
 */
typedef struct {
    int8_t left_speed;   // -100 to 100
    int8_t right_speed;  // -100 to 100
} __attribute__((packed)) Motor_Speed_t;

/* ==================== FUNCTION PROTOTYPES ==================== */

/**
 * Initialize protocol (call in main)
 */
void Protocol_Init(void);

/**
 * Process incoming byte from UART
 * Call this in UART RX interrupt or main loop
 */
void Protocol_ProcessByte(uint8_t byte);

/**
 * Send packet to Raspberry Pi
 * @param cmd Command code
 * @param data Pointer to data buffer
 * @param length Data length (0-64)
 * @return true if sent successfully
 */
bool Protocol_SendPacket(uint8_t cmd, const uint8_t* data, uint8_t length);

/**
 * Send ACK response
 */
void Protocol_SendAck(void);

/**
 * Send NACK response
 */
void Protocol_SendNack(void);

/**
 * Send GPS data to Raspberry Pi
 */
void Protocol_SendGPSData(const GPS_Data_t* gps);

/**
 * Send IMU data to Raspberry Pi
 */
void Protocol_SendIMUData(const IMU_Data_t* imu);

/**
 * Send ultrasonic data to Raspberry Pi
 */
void Protocol_SendUltrasonicData(const Ultrasonic_Data_t* ultrasonic);

/**
 * Send system status to Raspberry Pi
 */
void Protocol_SendSystemStatus(const System_Status_t* status);

/**
 * Calculate checksum for packet
 * @param cmd Command byte
 * @param length Data length
 * @param data Pointer to data
 * @return Calculated checksum
 */
uint8_t Protocol_CalculateChecksum(uint8_t cmd, uint8_t length, const uint8_t* data);

/* ==================== COMMAND HANDLERS (Implement these) ==================== */

/**
 * Handle motor speed command
 * Called when CMD_MOTOR_SET_SPEED is received
 * @param left Left motor speed (-100 to 100)
 * @param right Right motor speed (-100 to 100)
 */
extern void Handle_MotorSetSpeed(int8_t left, int8_t right);

/**
 * Handle motor stop command
 * Called when CMD_MOTOR_STOP is received
 */
extern void Handle_MotorStop(void);

/**
 * Handle emergency stop command
 * Called when CMD_MOTOR_EMERGENCY_STOP is received
 */
extern void Handle_EmergencyStop(void);

/**
 * Handle GPS data request
 * Called when CMD_GPS_REQUEST is received
 * Should call Protocol_SendGPSData() with current GPS data
 */
extern void Handle_GPSRequest(void);

/**
 * Handle IMU data request
 * Called when CMD_IMU_REQUEST is received
 * Should call Protocol_SendIMUData() with current IMU data
 */
extern void Handle_IMURequest(void);

/**
 * Handle ultrasonic data request
 * Called when CMD_ULTRASONIC_REQUEST is received
 */
extern void Handle_UltrasonicRequest(void);

/**
 * Handle system status request
 * Called when CMD_SYSTEM_STATUS is received
 */
extern void Handle_SystemStatusRequest(void);

/**
 * Handle LED control command
 * Called when CMD_LED_CONTROL is received
 * @param state 1 for ON, 0 for OFF
 */
extern void Handle_LEDControl(uint8_t state);

/**
 * Handle buzzer control command
 * Called when CMD_BUZZER_CONTROL is received
 * @param state 1 for ON, 0 for OFF
 */
extern void Handle_BuzzerControl(uint8_t state);

/**
 * Handle reset command
 * Called when CMD_RESET is received
 */
extern void Handle_Reset(void);


/* Update system uptime (call periodically) */
void Protocol_UpdateUptime(void);

#endif /* RASPBERRY_PI_PROTOCOL_H */


/* ==================== IMPLEMENTATION EXAMPLE ==================== */

/*
 * raspberry_pi_protocol.c
 * Implementation of communication protocol
 * 
 * Location: ATmega32_Project/APP/raspberry_pi_protocol.c
 */

#ifdef IMPLEMENTATION_EXAMPLE

#include "raspberry_pi_protocol.h"
#include "uart.h"  // Your UART driver
#include <string.h>

/* State machine for packet reception */
static enum {
    STATE_IDLE,
    STATE_CMD,
    STATE_LENGTH,
    STATE_DATA,
    STATE_CHECKSUM
} rx_state = STATE_IDLE;

static uint8_t rx_cmd;
static uint8_t rx_length;
static uint8_t rx_data[MAX_DATA_LENGTH];
static uint8_t rx_index;
static uint8_t rx_checksum;

/* ==================== INITIALIZATION ==================== */

void Protocol_Init(void) {
    rx_state = STATE_IDLE;
    rx_index = 0;
}

/* ==================== PACKET PROCESSING ==================== */

void Protocol_ProcessByte(uint8_t byte) {
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
            uint8_t calculated = Protocol_CalculateChecksum(rx_cmd, rx_length, rx_data);
            if (calculated == rx_checksum) {
                // Wait for end byte
                // For simplicity, we'll process command here
                Protocol_ProcessCommand(rx_cmd, rx_data, rx_length);
            }
            rx_state = STATE_IDLE;
            break;
    }
}

/* ==================== COMMAND PROCESSING ==================== */

static void Protocol_ProcessCommand(uint8_t cmd, const uint8_t* data, uint8_t length) {
    switch (cmd) {
        case CMD_MOTOR_SET_SPEED:
            if (length == 2) {
                Motor_Speed_t* speed = (Motor_Speed_t*)data;
                Handle_MotorSetSpeed(speed->left_speed, speed->right_speed);
                Protocol_SendAck();
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
            
        case CMD_GPS_REQUEST:
            Handle_GPSRequest();
            break;
            
        case CMD_IMU_REQUEST:
            Handle_IMURequest();
            break;
            
        case CMD_ULTRASONIC_REQUEST:
            Handle_UltrasonicRequest();
            break;
            
        case CMD_ALL_SENSORS_REQUEST:
            // Send all sensor data
            Handle_GPSRequest();
            Handle_IMURequest();
            Handle_UltrasonicRequest();
            break;
            
        case CMD_SYSTEM_STATUS:
            Handle_SystemStatusRequest();
            break;
            
        case CMD_LED_CONTROL:
            if (length == 1) {
                Handle_LEDControl(data[0]);
                Protocol_SendAck();
            }
            break;
            
        case CMD_BUZZER_CONTROL:
            if (length == 1) {
                Handle_BuzzerControl(data[0]);
                Protocol_SendAck();
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

bool Protocol_SendPacket(uint8_t cmd, const uint8_t* data, uint8_t length) {
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
    for (uint8_t i = 0; i < length; i++) {
        UART_SendByte(data[i]);
    }
    
    // Calculate and send checksum
    uint8_t checksum = Protocol_CalculateChecksum(cmd, length, data);
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

void Protocol_SendGPSData(const GPS_Data_t* gps) {
    Protocol_SendPacket(RESP_GPS_DATA, (const uint8_t*)gps, sizeof(GPS_Data_t));
}

void Protocol_SendIMUData(const IMU_Data_t* imu) {
    Protocol_SendPacket(RESP_IMU_DATA, (const uint8_t*)imu, sizeof(IMU_Data_t));
}

void Protocol_SendUltrasonicData(const Ultrasonic_Data_t* ultrasonic) {
    Protocol_SendPacket(RESP_ULTRASONIC_DATA, (const uint8_t*)ultrasonic, sizeof(Ultrasonic_Data_t));
}

void Protocol_SendSystemStatus(const System_Status_t* status) {
    Protocol_SendPacket(RESP_SYSTEM_STATUS, (const uint8_t*)status, sizeof(System_Status_t));
}

/* ==================== UTILITY FUNCTIONS ==================== */

uint8_t Protocol_CalculateChecksum(uint8_t cmd, uint8_t length, const uint8_t* data) {
    uint8_t checksum = cmd + length;
    
    for (uint8_t i = 0; i < length; i++) {
        checksum += data[i];
    }
    
    return checksum;
}
void Protocol_UpdateUptime(void);

#endif /* IMPLEMENTATION_EXAMPLE */