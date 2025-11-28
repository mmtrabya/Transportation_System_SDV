/*
 * SECURE ESP32 V2X System with NVS Credential Storage
 * No hardcoded credentials - all loaded from secure NVS
 */

#include <WiFi.h>
#include <esp_now.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <mbedtls/aes.h>
#include <mbedtls/sha256.h>
#include "SecureCredentials.h"

// ==================== SECURE CONFIGURATION ====================
// ✅ NO HARDCODED CREDENTIALS - All loaded from NVS
SecureCredentialManager credManager;

// Message types
#define MSG_BSM 0x01
#define MSG_EMERGENCY 0x02
#define MSG_HAZARD 0x03
#define MSG_SIGNAL 0x04

// Intervals
#define BSM_INTERVAL 100      // 10Hz
#define V2I_INTERVAL 1000     // 1Hz

// ==================== DATA STRUCTURES ====================
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
  uint8_t signature[32];
};

struct HazardMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  float latitude;
  float longitude;
  uint8_t hazardType;
  char description[64];
  uint16_t checksum;
};

struct EmergencyMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  float latitude;
  float longitude;
  uint8_t emergencyType;
  float heading;
  uint16_t checksum;
};

// ==================== GLOBAL VARIABLES ====================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

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

struct Stats {
  uint32_t bsmSent = 0;
  uint32_t bsmReceived = 0;
  uint32_t hazardReceived = 0;
  uint32_t emergencyReceived = 0;
  uint32_t packetsDropped = 0;
  uint32_t mqttPublished = 0;
  uint32_t mqttReceived = 0;
} stats;

unsigned long lastBSMTime = 0;
unsigned long lastV2ITime = 0;
unsigned long lastStatsTime = 0;

// Security keys (loaded from NVS)
uint8_t aesKey[16];
uint8_t hmacKey[32];

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
void serialCommandHandler();
void sendStatsToRaspberryPi();

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n╔════════════════════════════════════════╗");
  Serial.println("║  SECURE ESP32 V2X Communication System  ║");
  Serial.println("╚════════════════════════════════════════╝\n");
  
  // ✅ Load secure credentials from NVS
  if (!credManager.begin()) {
    Serial.println("\n❌ FATAL: Failed to load credentials from NVS!");
    Serial.println("💡 Solution: Run the setup script first to store credentials");
    Serial.println("   1. Flash setup_credentials_vX.cpp");
    Serial.println("   2. Wait for success message");
    Serial.println("   3. Flash this main application\n");
    while(1) delay(1000);
  }
  
  // Show credential status (masked for security)
  credManager.printStatus();
  
  // Load security keys
  credManager.getAESKey(aesKey);
  credManager.getHMACKey(hmacKey);
  
  Serial.print("Vehicle ID: ");
  Serial.println(credManager.getVehicleID());
  
  // Setup communication
  setupWiFi();
  setupMQTT();
  setupESPNow();
  
  Serial.println("\n✅ Secure V2X System Ready!");
  Serial.println("Commands: BSM, HAZARD, EMERGENCY, STATS\n");
}

// ==================== MAIN LOOP ====================
void loop() {
  unsigned long currentTime = millis();
  
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
  
  if (currentTime - lastBSMTime >= BSM_INTERVAL) {
    sendBSM();
    lastBSMTime = currentTime;
  }
  
  if (currentTime - lastV2ITime >= V2I_INTERVAL) {
    sendV2IData();
    lastV2ITime = currentTime;
  }
  
  if (currentTime - lastStatsTime >= 5000) {
    sendStatsToRaspberryPi();
    lastStatsTime = currentTime;
  }
  
  cleanupOldVehicles();
  
  if (Serial.available()) {
    serialCommandHandler();
  }
  
  updateVehicleState();
  delay(10);
}

// ==================== WiFi SETUP ====================
void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.print(credManager.getWiFiSSID());
  Serial.print("...");
  
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(
    credManager.getWiFiSSID().c_str(),
    credManager.getWiFiPassword().c_str()
  );
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("Channel: ");
    Serial.println(WiFi.channel());
  } else {
    Serial.println("\n⚠️  WiFi Failed - Continuing with ESP-NOW only");
  }
}

// ==================== MQTT SETUP ====================
void setupMQTT() {
  String mqttServer = credManager.getMQTTServer();
  if (mqttServer.length() == 0) {
    Serial.println("⚠️  No MQTT server configured");
    return;
  }
  
  mqttClient.setServer(mqttServer.c_str(), 1883);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(1024);
  
  reconnectMQTT();
}

void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  String mqttServer = credManager.getMQTTServer();
  if (mqttServer.length() == 0) return;
  
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 3) {
    Serial.print("Connecting to MQTT: ");
    Serial.print(mqttServer);
    Serial.print("...");
    
    String clientId = "ESP32_" + credManager.getVehicleID();
    
    if (mqttClient.connect(
          clientId.c_str(),
          credManager.getMQTTUser().c_str(),
          credManager.getMQTTPassword().c_str())) {
      
      Serial.println("Connected!");
      
      // Subscribe to topic
      String topic = credManager.getMQTTUser() + "/SDV";
      mqttClient.subscribe(topic.c_str());
      
      Serial.print("Subscribed to: ");
      Serial.println(topic);
      
    } else {
      Serial.print("Failed (rc=");
      Serial.print(mqttClient.state());
      Serial.println(")");
      delay(2000);
      attempts++;
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  stats.mqttReceived++;
  
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) return;
  
  const char* msgType = doc["type"];
  if (msgType == NULL) return;
  
  if (strcmp(msgType, "signal") == 0) {
    Serial.print("SIGNAL:");
    Serial.print(doc["intersection_id"].as<const char*>());
    Serial.print(",");
    Serial.print(doc["current_phase"].as<uint8_t>());
    Serial.print(",");
    Serial.println(doc["time_remaining"].as<uint16_t>());
  }
}

// ==================== ESP-NOW SETUP ====================
void setupESPNow() {
  uint8_t wifiChannel = WiFi.status() == WL_CONNECTED ? WiFi.channel() : 1;
  
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ ESP-NOW init failed!");
    return;
  }
  
  Serial.println("✅ ESP-NOW initialized");
  
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataReceived);
  
  esp_now_peer_info_t peerInfo = {};
  uint8_t broadcastAddr[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  memcpy(peerInfo.peer_addr, broadcastAddr, 6);
  peerInfo.channel = wifiChannel;
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) == ESP_OK) {
    Serial.print("✅ Broadcast peer added (channel ");
    Serial.print(wifiChannel);
    Serial.println(")");
  }
}

// ==================== ESP-NOW CALLBACKS ====================
void onDataSent(const uint8_t *mac, esp_now_send_status_t status) {
  if (status != ESP_NOW_SEND_SUCCESS) {
    stats.packetsDropped++;
  }
}

void onDataReceived(const uint8_t *mac, const uint8_t *data, int len) {
  if (len < 1) return;
  
  uint8_t msgType = data[0];
  
  switch (msgType) {
    case MSG_BSM:
      if (len == sizeof(BSMMessage)) {
        BSMMessage* bsm = (BSMMessage*)data;
        if (verifyChecksum((uint8_t*)bsm, sizeof(BSMMessage) - 34, bsm->checksum)) {
          processReceivedBSM(bsm);
          stats.bsmReceived++;
          publishBSMToMQTT(bsm);
        }
      }
      break;
      
    case MSG_HAZARD:
      if (len == sizeof(HazardMessage)) {
        HazardMessage* hazard = (HazardMessage*)data;
        if (verifyChecksum((uint8_t*)hazard, sizeof(HazardMessage) - 2, hazard->checksum)) {
          processReceivedHazard(hazard);
          stats.hazardReceived++;
        }
      }
      break;
      
    case MSG_EMERGENCY:
      if (len == sizeof(EmergencyMessage)) {
        EmergencyMessage* emergency = (EmergencyMessage*)data;
        if (verifyChecksum((uint8_t*)emergency, sizeof(EmergencyMessage) - 2, emergency->checksum)) {
          processReceivedEmergency(emergency);
          stats.emergencyReceived++;
        }
      }
      break;
  }
}

// ==================== SEND MESSAGES ====================
void sendBSM() {
  BSMMessage bsm;
  memset(&bsm, 0, sizeof(BSMMessage));
  
  bsm.msgType = MSG_BSM;
  String vehicleId = credManager.getVehicleID();
  strncpy(bsm.vehicleId, vehicleId.c_str(), 15);
  bsm.vehicleId[15] = '\0';
  
  bsm.timestamp = millis();
  bsm.latitude = vehicleState.latitude;
  bsm.longitude = vehicleState.longitude;
  bsm.altitude = vehicleState.altitude;
  bsm.speed = vehicleState.speed;
  bsm.heading = vehicleState.heading;
  bsm.acceleration = vehicleState.acceleration;
  bsm.brakingStatus = vehicleState.brakingStatus;
  
  bsm.checksum = calculateChecksum((uint8_t*)&bsm, sizeof(BSMMessage) - 34);
  generateSignature((uint8_t*)&bsm, sizeof(BSMMessage) - 34, bsm.signature);
  
  uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_now_send(broadcastAddress, (uint8_t*)&bsm, sizeof(BSMMessage));
  
  stats.bsmSent++;
}

void sendV2IData() {
  if (!mqttClient.connected()) return;
  
  StaticJsonDocument<512> doc;
  doc["type"] = "status";
  doc["vehicle_id"] = credManager.getVehicleID();
  doc["timestamp"] = millis();
  doc["latitude"] = vehicleState.latitude;
  doc["longitude"] = vehicleState.longitude;
  doc["speed"] = vehicleState.speed;
  doc["nearby_vehicles"] = nearbyVehicleCount;
  
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  
  String topic = credManager.getMQTTUser() + "/SDV";
  if (mqttClient.publish(topic.c_str(), jsonBuffer)) {
    stats.mqttPublished++;
  }
}

void publishBSMToMQTT(BSMMessage* msg) {
  if (!mqttClient.connected()) return;
  
  String myVehicleId = credManager.getVehicleID();
  if (strcmp(msg->vehicleId, myVehicleId.c_str()) == 0) return;
  
  StaticJsonDocument<384> doc;
  doc["type"] = "bsm";
  doc["vehicle_id"] = msg->vehicleId;
  doc["timestamp"] = msg->timestamp;
  doc["latitude"] = msg->latitude;
  doc["longitude"] = msg->longitude;
  doc["speed"] = msg->speed;
  
  char jsonBuffer[384];
  serializeJson(doc, jsonBuffer);
  
  String topic = credManager.getMQTTUser() + "/SDV";
  if (mqttClient.publish(topic.c_str(), jsonBuffer)) {
    stats.mqttPublished++;
  }
}

// ==================== PROCESS MESSAGES ====================
void processReceivedBSM(BSMMessage* msg) {
  String myVehicleId = credManager.getVehicleID();
  if (strcmp(msg->vehicleId, myVehicleId.c_str()) == 0) return;
  
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
    if (currentTime - nearbyVehicles[i].lastSeen > 5000) {
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
  mbedtls_sha256_context ctx;
  mbedtls_sha256_init(&ctx);
  mbedtls_sha256_starts(&ctx, 0);
  mbedtls_sha256_update(&ctx, aesKey, 16);
  mbedtls_sha256_update(&ctx, data, len);
  mbedtls_sha256_finish(&ctx, signature);
  mbedtls_sha256_free(&ctx);
}

void updateVehicleState() {
  static float simSpeed = 0.0;
  simSpeed += random(-5, 6) / 100.0;
  simSpeed = constrain(simSpeed, 0.0, 30.0);
  vehicleState.speed = simSpeed;
}

void serialCommandHandler() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  
  if (cmd == "STATS") {
    sendStatsToRaspberryPi();
  } else if (cmd == "STATUS") {
    credManager.printStatus();
  }
}

void sendStatsToRaspberryPi() {
  Serial.println("\n=== V2X Statistics ===");
  Serial.print("Vehicle ID: "); Serial.println(credManager.getVehicleID());
  Serial.print("BSM Sent: "); Serial.println(stats.bsmSent);
  Serial.print("BSM Received: "); Serial.println(stats.bsmReceived);
  Serial.print("Hazards: "); Serial.println(stats.hazardReceived);
  Serial.print("Emergencies: "); Serial.println(stats.emergencyReceived);
  Serial.print("MQTT Published: "); Serial.println(stats.mqttPublished);
  Serial.print("MQTT Received: "); Serial.println(stats.mqttReceived);
  Serial.print("Nearby Vehicles: "); Serial.println(nearbyVehicleCount);
  Serial.print("MQTT: "); Serial.println(mqttClient.connected() ? "✓" : "✗");
  Serial.println("===================\n");
}