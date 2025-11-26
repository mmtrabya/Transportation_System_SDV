#include <WiFi.h>
#include <esp_now.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <mbedtls/aes.h>
#include <mbedtls/sha256.h>

// ==================== CONFIGURATION ====================
#define WIFI_SSID "Tarabay madinaty"
#define WIFI_PASSWORD "Tarabay_2379"
#define MQTT_SERVER "b37.mqtt.one"
#define MQTT_PORT 1883
#define MQTT_USER "7ajsuv9561"
#define MQTT_PASSWORD "169cflptvw"
#define VEHICLE_ID "SDV002"

// MQTT Topic - Single topic for all messages
#define MQTT_TOPIC "7ajsuv9561/SDV"

// Message types
#define MSG_BSM 0x01          // Basic Safety Message
#define MSG_EMERGENCY 0x02    // Emergency Vehicle Alert
#define MSG_HAZARD 0x03       // Hazard Warning
#define MSG_SIGNAL 0x04       // Traffic Signal Phase
#define MSG_CAM 0x05          // Cooperative Awareness Message

// Communication channels
#define V2V_CHANNEL 1         // ESP-NOW channel for V2V
#define BSM_INTERVAL 100      // Send BSM every 100ms (10Hz)
#define V2I_INTERVAL 1000     // Send V2I data every 1s

// ==================== DATA STRUCTURES ====================

// Basic Safety Message structure
struct BSMMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  float latitude;
  float longitude;
  float altitude;
  float speed;
  float heading;
  float acceleration;
  uint8_t brakingStatus;
  uint16_t checksum;
  uint8_t signature[32]; // Simplified signature
};

// Hazard Warning Message
struct HazardMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  float latitude;
  float longitude;
  uint8_t hazardType; // 1=accident, 2=ice, 3=construction, etc.
  char description[64];
  uint16_t checksum;
};

// Emergency Vehicle Alert
struct EmergencyMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  float latitude;
  float longitude;
  uint8_t emergencyType; // 1=ambulance, 2=fire, 3=police
  float heading;
  uint16_t checksum;
};

// Traffic Signal Phase Message
struct SignalMessage {
  uint8_t msgType;
  char intersectionId[16];
  uint32_t timestamp;
  uint8_t currentPhase; // 0=red, 1=yellow, 2=green
  uint16_t timeRemaining; // seconds
  uint8_t nextPhase;
  uint16_t checksum;
};

// ==================== GLOBAL VARIABLES ====================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// Vehicle state
struct VehicleState {
  float latitude = 30.0444;
  float longitude = 31.2357;
  float altitude = 74.5;
  float speed = 0.0;
  float heading = 0.0;
  float acceleration = 0.0;
  uint8_t brakingStatus = 0;
  bool emergencyActive = false;
  uint8_t emergencyType = 0;
} vehicleState;

// Nearby vehicles tracking
struct NearbyVehicle {
  char vehicleId[16];
  float latitude;
  float longitude;
  float speed;
  uint32_t lastSeen;
  bool isEmergency;
};

#define MAX_NEARBY_VEHICLES 20
NearbyVehicle nearbyVehicles[MAX_NEARBY_VEHICLES];
int nearbyVehicleCount = 0;

// Communication statistics
struct Stats {
  uint32_t bsmSent = 0;
  uint32_t bsmReceived = 0;
  uint32_t hazardReceived = 0;
  uint32_t emergencyReceived = 0;
  uint32_t packetsDropped = 0;
  uint32_t mqttPublished = 0;
  uint32_t mqttReceived = 0;
} stats;

// Timing
unsigned long lastBSMTime = 0;
unsigned long lastV2ITime = 0;
unsigned long lastStatsTime = 0;

// Security key (in production, use secure key storage)
uint8_t aesKey[16] = {0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
                       0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};

// ==================== FUNCTION PROTOTYPES ====================
void setupWiFi();
void setupMQTT();
void reconnectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void setupESPNow();
void onDataReceived(const uint8_t *mac, const uint8_t *data, int len);
void onDataSent(const uint8_t *mac, esp_now_send_status_t status);
void sendBSM();
void sendHazardWarning(uint8_t hazardType, const char* description);
void sendEmergencyAlert();
void processReceivedBSM(BSMMessage* msg);
void processReceivedHazard(HazardMessage* msg);
void processReceivedEmergency(EmergencyMessage* msg);
void sendV2IData();
void publishBSMToMQTT(BSMMessage* msg);
void updateVehicleState();
void cleanupOldVehicles();
uint16_t calculateChecksum(uint8_t* data, size_t len);
bool verifyChecksum(uint8_t* data, size_t len, uint16_t checksum);
void generateSignature(uint8_t* data, size_t len, uint8_t* signature);
bool verifySignature(uint8_t* data, size_t len, uint8_t* signature);
void serialCommandHandler();
void sendStatsToRaspberryPi();

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== ESP32 V2X Communication System ===");
  Serial.print("Vehicle ID: ");
  Serial.println(VEHICLE_ID);
  
  // Setup WiFi and MQTT for V2I
  setupWiFi();
  setupMQTT();
  
  // Setup ESP-NOW for V2V
  setupESPNow();
  
  Serial.println("V2X System Ready!");
  Serial.println("Commands: BSM, HAZARD, EMERGENCY, STATS");
}

// ==================== MAIN LOOP ====================
void loop() {
  unsigned long currentTime = millis();
  
  // Handle MQTT connection
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
  
  // Send BSM periodically (10Hz)
  if (currentTime - lastBSMTime >= BSM_INTERVAL) {
    sendBSM();
    lastBSMTime = currentTime;
  }
  
  // Send V2I data periodically (1Hz)
  if (currentTime - lastV2ITime >= V2I_INTERVAL) {
    sendV2IData();
    lastV2ITime = currentTime;
  }
  
  // Send stats every 5 seconds
  if (currentTime - lastStatsTime >= 5000) {
    sendStatsToRaspberryPi();
    lastStatsTime = currentTime;
  }
  
  // Cleanup old vehicle records
  cleanupOldVehicles();
  
  // Handle serial commands from Raspberry Pi
  if (Serial.available()) {
    serialCommandHandler();
  }
  
  // Update vehicle state (would come from Pi in real system)
  updateVehicleState();
  
  delay(10);
}

// ==================== WiFi SETUP ====================
void setupWiFi() {
  Serial.print("Connecting to WiFi...");
  WiFi.mode(WIFI_AP_STA); // AP+STA mode for ESP-NOW and WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed. Continuing with ESP-NOW only.");
  }
}

// ==================== MQTT SETUP ====================
void setupMQTT() {
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(1024); // Increase buffer for larger messages
  
  reconnectMQTT();
}

void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 3) {
    Serial.print("Connecting to MQTT broker at ");
    Serial.print(MQTT_SERVER);
    Serial.print("...");
    
    String clientId = "ESP32" + String(VEHICLE_ID);
    
    // Connect with username and password
    if (mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
      Serial.println("Connected!");
      Serial.print("Client ID: ");
      Serial.println(clientId);
      
      // Subscribe to single topic
      mqttClient.subscribe(MQTT_TOPIC);
      
      Serial.print("Subscribed to: ");
      Serial.println(MQTT_TOPIC);
      
    } else {
      Serial.print("Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" retrying...");
      delay(2000);
      attempts++;
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT RX [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.print(length);
  Serial.println("B");
  
  stats.mqttReceived++;
  
  // Parse JSON message
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.print("JSON parse error: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Check message type field
  const char* msgType = doc["type"];
  
  if (msgType == NULL) {
    Serial.println("No message type");
    return;
  }
  
  // Handle different message types
  if (strcmp(msgType, "signal") == 0) {
    const char* intersectionId = doc["intersection_id"];
    uint8_t currentPhase = doc["current_phase"];
    uint16_t timeRemaining = doc["time_remaining"];
    
    // Forward to Raspberry Pi
    Serial.print("SIGNAL:");
    Serial.print(intersectionId);
    Serial.print(",");
    Serial.print(currentPhase);
    Serial.print(",");
    Serial.println(timeRemaining);
  }
  else if (strcmp(msgType, "emergency") == 0) {
    const char* vehicleId = doc["vehicle_id"];
    uint8_t emergencyType = doc["emergency_type"];
    float lat = doc["latitude"];
    float lon = doc["longitude"];
    
    Serial.print("INFRA_EMERGENCY:");
    Serial.print(vehicleId);
    Serial.print(",");
    Serial.print(emergencyType);
    Serial.print(",");
    Serial.print(lat, 6);
    Serial.print(",");
    Serial.println(lon, 6);
  }
  else if (strcmp(msgType, "bsm") == 0) {
    const char* vehicleId = doc["vehicle_id"];
    float lat = doc["latitude"];
    float lon = doc["longitude"];
    float speed = doc["speed"];
    
    Serial.print("MQTT_BSM:");
    Serial.print(vehicleId);
    Serial.print(",");
    Serial.print(lat, 6);
    Serial.print(",");
    Serial.print(lon, 6);
    Serial.print(",");
    Serial.println(speed);
  }
  else if (strcmp(msgType, "hazard") == 0) {
    const char* vehicleId = doc["vehicle_id"];
    uint8_t hazardType = doc["hazard_type"];
    float lat = doc["latitude"];
    float lon = doc["longitude"];
    const char* description = doc["description"];
    
    Serial.print("MQTT_HAZARD:");
    Serial.print(vehicleId);
    Serial.print(",");
    Serial.print(hazardType);
    Serial.print(",");
    Serial.print(lat, 6);
    Serial.print(",");
    Serial.print(lon, 6);
    Serial.print(",");
    Serial.println(description);
  }
}

// ==================== ESP-NOW SETUP ====================
void setupESPNow() {
  // Get current WiFi channel
  uint8_t wifiChannel = 1;
  if (WiFi.status() == WL_CONNECTED) {
    wifiChannel = WiFi.channel();
  }
  
  Serial.print("WiFi Channel: ");
  Serial.println(wifiChannel);
  
  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed!");
    return;
  }
  
  Serial.println("ESP-NOW initialized");
  
  // Register callbacks
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataReceived);
  
  // Add broadcast peer with WiFi channel
  esp_now_peer_info_t peerInfo = {};
  memset(&peerInfo, 0, sizeof(peerInfo));
  uint8_t broadcastAddr[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  memcpy(peerInfo.peer_addr, broadcastAddr, 6);
  peerInfo.channel = wifiChannel;  // Use WiFi channel
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add broadcast peer");
  } else {
    Serial.print("Broadcast peer added on channel: ");
    Serial.println(wifiChannel);
  }
}

// ==================== ESP-NOW CALLBACKS ====================
void onDataSent(const uint8_t *mac, esp_now_send_status_t status) {
  if (status != ESP_NOW_SEND_SUCCESS) {
    stats.packetsDropped++;
  }
}

void onDataReceived(const uint8_t *mac, const uint8_t *data, int len) {
  Serial.print("RX:");
  Serial.print(len);
  Serial.print("B from ");
  for(int i=0; i<6; i++) {
    Serial.printf("%02X", mac[i]);
    if(i<5) Serial.print(":");
  }

  if (len < 1) {
    Serial.println(" TOO SHORT");
    return;
  }
  
  uint8_t msgType = data[0];
  Serial.print(" Type:");
  Serial.println(msgType, HEX);
  
  switch (msgType) {
    case MSG_BSM:
      if (len == sizeof(BSMMessage)) {
        BSMMessage* bsm = (BSMMessage*)data;
        
        // FIXED: Calculate checksum excluding BOTH checksum (2 bytes) and signature (32 bytes)
        if (verifyChecksum((uint8_t*)bsm, sizeof(BSMMessage) - 34, bsm->checksum)) {
          processReceivedBSM(bsm);
          stats.bsmReceived++;
          publishBSMToMQTT(bsm);
          Serial.println("  BSM OK");
        } else {
          Serial.println("  Checksum FAIL");
        }
      } else {
        Serial.print("  Size mismatch: ");
        Serial.print(len);
        Serial.print(" vs ");
        Serial.println(sizeof(BSMMessage));
      }
      break;
      
    case MSG_HAZARD:
      if (len == sizeof(HazardMessage)) {
        HazardMessage* hazard = (HazardMessage*)data;
        if (verifyChecksum((uint8_t*)hazard, sizeof(HazardMessage) - 2, hazard->checksum)) {
          processReceivedHazard(hazard);
          stats.hazardReceived++;
          Serial.println("  Hazard OK");
        }
      }
      break;
      
    case MSG_EMERGENCY:
      if (len == sizeof(EmergencyMessage)) {
        EmergencyMessage* emergency = (EmergencyMessage*)data;
        if (verifyChecksum((uint8_t*)emergency, sizeof(EmergencyMessage) - 2, emergency->checksum)) {
          processReceivedEmergency(emergency);
          stats.emergencyReceived++;
          Serial.println("  Emergency OK");
        }
      }
      break;
      
    default:
      Serial.print("  Unknown type: ");
      Serial.println(msgType, HEX);
      break;
  }
}

// ==================== SEND MESSAGES ====================
void sendBSM() {
  BSMMessage bsm;
  memset(&bsm, 0, sizeof(BSMMessage)); // Zero out first
  
  bsm.msgType = MSG_BSM;
  strncpy(bsm.vehicleId, VEHICLE_ID, 16);
  bsm.timestamp = millis();
  bsm.latitude = vehicleState.latitude;
  bsm.longitude = vehicleState.longitude;
  bsm.altitude = vehicleState.altitude;
  bsm.speed = vehicleState.speed;
  bsm.heading = vehicleState.heading;
  bsm.acceleration = vehicleState.acceleration;
  bsm.brakingStatus = vehicleState.brakingStatus;
  
  // FIXED: Calculate checksum excluding checksum field (2 bytes) and signature (32 bytes)
  bsm.checksum = calculateChecksum((uint8_t*)&bsm, sizeof(BSMMessage) - 34);
  generateSignature((uint8_t*)&bsm, sizeof(BSMMessage) - 34, bsm.signature);
  
  uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t*)&bsm, sizeof(BSMMessage));
  
  if (result != ESP_OK) {
    Serial.print("ESP-NOW send failed: ");
    Serial.println(result);
  }
  
  stats.bsmSent++;
}

void sendHazardWarning(uint8_t hazardType, const char* description) {
  HazardMessage hazard;
  memset(&hazard, 0, sizeof(HazardMessage));
  
  hazard.msgType = MSG_HAZARD;
  strncpy(hazard.vehicleId, VEHICLE_ID, 16);
  hazard.timestamp = millis();
  hazard.latitude = vehicleState.latitude;
  hazard.longitude = vehicleState.longitude;
  hazard.hazardType = hazardType;
  strncpy(hazard.description, description, 64);
  
  hazard.checksum = calculateChecksum((uint8_t*)&hazard, sizeof(HazardMessage) - 2);
  
  // Send via ESP-NOW
  uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_now_send(broadcastAddress, (uint8_t*)&hazard, sizeof(HazardMessage));
  
  // Also publish to MQTT
  if (mqttClient.connected()) {
    StaticJsonDocument<256> doc;
    doc["type"] = "hazard";
    doc["vehicle_id"] = VEHICLE_ID;
    doc["timestamp"] = millis();
    doc["latitude"] = vehicleState.latitude;
    doc["longitude"] = vehicleState.longitude;
    doc["hazard_type"] = hazardType;
    doc["description"] = description;
    
    char jsonBuffer[256];
    serializeJson(doc, jsonBuffer);
    mqttClient.publish(MQTT_TOPIC, jsonBuffer);
    stats.mqttPublished++;
  }
  
  Serial.println("Hazard warning sent!");
}

void sendEmergencyAlert() {
  EmergencyMessage emergency;
  memset(&emergency, 0, sizeof(EmergencyMessage));
  
  emergency.msgType = MSG_EMERGENCY;
  strncpy(emergency.vehicleId, VEHICLE_ID, 16);
  emergency.timestamp = millis();
  emergency.latitude = vehicleState.latitude;
  emergency.longitude = vehicleState.longitude;
  emergency.emergencyType = vehicleState.emergencyType;
  emergency.heading = vehicleState.heading;
  
  emergency.checksum = calculateChecksum((uint8_t*)&emergency, sizeof(EmergencyMessage) - 2);
  
  // Send via ESP-NOW
  uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_now_send(broadcastAddress, (uint8_t*)&emergency, sizeof(EmergencyMessage));
  
  // Also publish to MQTT
  if (mqttClient.connected()) {
    StaticJsonDocument<256> doc;
    doc["type"] = "emergency";
    doc["vehicle_id"] = VEHICLE_ID;
    doc["timestamp"] = millis();
    doc["latitude"] = vehicleState.latitude;
    doc["longitude"] = vehicleState.longitude;
    doc["emergency_type"] = vehicleState.emergencyType;
    doc["heading"] = vehicleState.heading;
    
    char jsonBuffer[256];
    serializeJson(doc, jsonBuffer);
    mqttClient.publish(MQTT_TOPIC, jsonBuffer);
    stats.mqttPublished++;
  }
  
  Serial.println("Emergency alert sent!");
}

void sendV2IData() {
  if (!mqttClient.connected()) return;
  
  StaticJsonDocument<512> doc;
  doc["type"] = "status";
  doc["vehicle_id"] = VEHICLE_ID;
  doc["timestamp"] = millis();
  doc["latitude"] = vehicleState.latitude;
  doc["longitude"] = vehicleState.longitude;
  doc["altitude"] = vehicleState.altitude;
  doc["speed"] = vehicleState.speed;
  doc["heading"] = vehicleState.heading;
  doc["acceleration"] = vehicleState.acceleration;
  doc["nearby_vehicles"] = nearbyVehicleCount;
  doc["emergency_active"] = vehicleState.emergencyActive;
  
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  
  if (mqttClient.publish(MQTT_TOPIC, jsonBuffer)) {
    stats.mqttPublished++;
  }
}

void publishBSMToMQTT(BSMMessage* msg) {
  if (!mqttClient.connected()) return;
  
  // Don't publish own messages
  if (strcmp(msg->vehicleId, VEHICLE_ID) == 0) return;
  
  StaticJsonDocument<384> doc;
  doc["type"] = "bsm";
  doc["vehicle_id"] = msg->vehicleId;
  doc["timestamp"] = msg->timestamp;
  doc["latitude"] = msg->latitude;
  doc["longitude"] = msg->longitude;
  doc["altitude"] = msg->altitude;
  doc["speed"] = msg->speed;
  doc["heading"] = msg->heading;
  doc["acceleration"] = msg->acceleration;
  doc["braking_status"] = msg->brakingStatus;
  
  char jsonBuffer[384];
  serializeJson(doc, jsonBuffer);
  
  if (mqttClient.publish(MQTT_TOPIC, jsonBuffer)) {
    stats.mqttPublished++;
  }
}

// ==================== PROCESS RECEIVED MESSAGES ====================
void processReceivedBSM(BSMMessage* msg) {
  // Don't process own messages
  if (strcmp(msg->vehicleId, VEHICLE_ID) == 0) return;
  
  // Update or add to nearby vehicles
  bool found = false;
  for (int i = 0; i < nearbyVehicleCount; i++) {
    if (strcmp(nearbyVehicles[i].vehicleId, msg->vehicleId) == 0) {
      nearbyVehicles[i].latitude = msg->latitude;
      nearbyVehicles[i].longitude = msg->longitude;
      nearbyVehicles[i].speed = msg->speed;
      nearbyVehicles[i].lastSeen = millis();
      found = true;
      break;
    }
  }
  
  if (!found && nearbyVehicleCount < MAX_NEARBY_VEHICLES) {
    strncpy(nearbyVehicles[nearbyVehicleCount].vehicleId, msg->vehicleId, 16);
    nearbyVehicles[nearbyVehicleCount].latitude = msg->latitude;
    nearbyVehicles[nearbyVehicleCount].longitude = msg->longitude;
    nearbyVehicles[nearbyVehicleCount].speed = msg->speed;
    nearbyVehicles[nearbyVehicleCount].lastSeen = millis();
    nearbyVehicles[nearbyVehicleCount].isEmergency = false;
    nearbyVehicleCount++;
  }
  
  // Forward to Raspberry Pi
  Serial.print("V2V_BSM:");
  Serial.print(msg->vehicleId);
  Serial.print(",");
  Serial.print(msg->latitude, 6);
  Serial.print(",");
  Serial.print(msg->longitude, 6);
  Serial.print(",");
  Serial.println(msg->speed);
}

void processReceivedHazard(HazardMessage* msg) {
  Serial.print("V2V_HAZARD:");
  Serial.print(msg->vehicleId);
  Serial.print(",");
  Serial.print(msg->hazardType);
  Serial.print(",");
  Serial.print(msg->latitude, 6);
  Serial.print(",");
  Serial.print(msg->longitude, 6);
  Serial.print(",");
  Serial.println(msg->description);
}

void processReceivedEmergency(EmergencyMessage* msg) {
  // Mark vehicle as emergency
  for (int i = 0; i < nearbyVehicleCount; i++) {
    if (strcmp(nearbyVehicles[i].vehicleId, msg->vehicleId) == 0) {
      nearbyVehicles[i].isEmergency = true;
      break;
    }
  }
  
  Serial.print("V2V_EMERGENCY:");
  Serial.print(msg->vehicleId);
  Serial.print(",");
  Serial.print(msg->emergencyType);
  Serial.print(",");
  Serial.print(msg->latitude, 6);
  Serial.print(",");
  Serial.println(msg->longitude, 6);
}

// ==================== UTILITY FUNCTIONS ====================
void cleanupOldVehicles() {
  unsigned long currentTime = millis();
  
  for (int i = 0; i < nearbyVehicleCount; i++) {
    if (currentTime - nearbyVehicles[i].lastSeen > 5000) { // 5 second timeout
      // Remove vehicle by shifting array
      for (int j = i; j < nearbyVehicleCount - 1; j++) {
        nearbyVehicles[j] = nearbyVehicles[j + 1];
      }
      nearbyVehicleCount--;
      i--;
    }
  }
}

uint16_t calculateChecksum(uint8_t* data, size_t len) {
  uint16_t checksum = 0;
  for (size_t i = 0; i < len; i++) {
    checksum += data[i];
  }
  return checksum;
}

bool verifyChecksum(uint8_t* data, size_t len, uint16_t checksum) {
  return calculateChecksum(data, len) == checksum;
}

void generateSignature(uint8_t* data, size_t len, uint8_t* signature) {
  // Simplified HMAC-like signature using SHA256
  mbedtls_sha256_context ctx;
  mbedtls_sha256_init(&ctx);
  mbedtls_sha256_starts(&ctx, 0);
  mbedtls_sha256_update(&ctx, aesKey, 16);
  mbedtls_sha256_update(&ctx, data, len);
  mbedtls_sha256_finish(&ctx, signature);
  mbedtls_sha256_free(&ctx);
}

bool verifySignature(uint8_t* data, size_t len, uint8_t* signature) {
  uint8_t computed[32];
  generateSignature(data, len, computed);
  return memcmp(computed, signature, 32) == 0;
}

void updateVehicleState() {
  // In production, this receives data from Raspberry Pi via Serial
  // For now, simulate some movement
  static float simSpeed = 0.0;
  simSpeed += random(-5, 6) / 100.0;
  simSpeed = constrain(simSpeed, 0.0, 30.0);
  vehicleState.speed = simSpeed;
}

void serialCommandHandler() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  
  if (cmd.startsWith("UPDATE:")) {
    // Format: UPDATE:lat,lon,speed,heading,accel
    int idx = 7;
    vehicleState.latitude = cmd.substring(idx, cmd.indexOf(',', idx)).toFloat();
    idx = cmd.indexOf(',', idx) + 1;
    vehicleState.longitude = cmd.substring(idx, cmd.indexOf(',', idx)).toFloat();
    idx = cmd.indexOf(',', idx) + 1;
    vehicleState.speed = cmd.substring(idx, cmd.indexOf(',', idx)).toFloat();
    idx = cmd.indexOf(',', idx) + 1;
    vehicleState.heading = cmd.substring(idx, cmd.indexOf(',', idx)).toFloat();
    idx = cmd.indexOf(',', idx) + 1;
    vehicleState.acceleration = cmd.substring(idx).toFloat();
    
  } else if (cmd == "BSM") {
    sendBSM();
    Serial.println("Manual BSM sent");
    
  } else if (cmd.startsWith("HAZARD:")) {
    uint8_t type = cmd.substring(7, cmd.indexOf(',')).toInt();
    String desc = cmd.substring(cmd.indexOf(',') + 1);
    sendHazardWarning(type, desc.c_str());
    
  } else if (cmd == "EMERGENCY") {
    vehicleState.emergencyActive = true;
    sendEmergencyAlert();
    
  } else if (cmd == "STATS") {
    sendStatsToRaspberryPi();
  }
}

void sendStatsToRaspberryPi() {
  Serial.println("=== V2X Statistics ===");
  Serial.print("BSM Sent: "); Serial.println(stats.bsmSent);
  Serial.print("BSM Received: "); Serial.println(stats.bsmReceived);
  Serial.print("Hazards Received: "); Serial.println(stats.hazardReceived);
  Serial.print("Emergencies Received: "); Serial.println(stats.emergencyReceived);
  Serial.print("Packets Dropped: "); Serial.println(stats.packetsDropped);
  Serial.print("MQTT Published: "); Serial.println(stats.mqttPublished);
  Serial.print("MQTT Received: "); Serial.println(stats.mqttReceived);
  Serial.print("Nearby Vehicles: "); Serial.println(nearbyVehicleCount);
  Serial.print("MQTT Connected: "); Serial.println(mqttClient.connected() ? "Yes" : "No");
  Serial.println("===================");
}