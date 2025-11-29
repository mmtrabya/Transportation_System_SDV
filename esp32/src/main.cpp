/*
 * SECURE ESP32 V2X System with REAL-TIME Firebase
 * 10Hz Firebase updates for real-time dashboard
 */

#include <WiFi.h>
#include <esp_now.h>
#include <Firebase_ESP_Client.h>
#include <ArduinoJson.h>
#include <mbedtls/aes.h>
#include <mbedtls/sha256.h>
#include "SecureCredentials.h"
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// ==================== SECURE CONFIGURATION ====================
SecureCredentialManager credManager;

// Firebase objects
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

bool firebaseReady = false;

// Message types
#define MSG_BSM 0x01
#define MSG_EMERGENCY 0x02
#define MSG_HAZARD 0x03

// Intervals - REAL-TIME CONFIGURATION
#define BSM_INTERVAL 100           // 10Hz - ESP-NOW broadcasts
#define FIREBASE_BSM_INTERVAL 100  // 10Hz - Real-time Firebase updates
#define FIREBASE_TELEMETRY_INTERVAL 1000  // 1Hz - Telemetry (less critical)
#define FIREBASE_STATUS_INTERVAL 5000     // 0.2Hz - System status

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
struct VehicleState {
  float latitude = 30.0444;
  float longitude = 31.2357;
  float altitude = 74.5;
  float speed = 0.0;
  float heading = 0.0;
  float acceleration = 0.0;
  uint8_t brakingStatus = 0;
  uint8_t batteryLevel = 85;
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
  uint32_t firebaseUploads = 0;
  uint32_t firebaseDownloads = 0;
  uint32_t firebaseErrors = 0;
} stats;

unsigned long lastBSMTime = 0;
unsigned long lastFirebaseBSMTime = 0;
unsigned long lastFirebaseTelemetryTime = 0;
unsigned long lastFirebaseStatusTime = 0;
unsigned long lastStatsTime = 0;

// Security keys (loaded from NVS)
uint8_t aesKey[16];
uint8_t hmacKey[32];

// ==================== FUNCTION PROTOTYPES ====================
void setupWiFi();
void setupFirebase();
void setupESPNow();
void onDataReceived(const uint8_t *mac, const uint8_t *data, int len);
void onDataSent(const uint8_t *mac, esp_now_send_status_t status);
void sendBSM();
void processReceivedBSM(BSMMessage* msg);
void processReceivedHazard(HazardMessage* msg);
void processReceivedEmergency(EmergencyMessage* msg);
void uploadBSMToFirebase();
void uploadTelemetryToFirebase();
void uploadSystemStatus();
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
  Serial.println("║  REAL-TIME ESP32 V2X with Firebase    ║");
  Serial.println("║  10Hz Firebase Updates                 ║");
  Serial.println("╚════════════════════════════════════════╝\n");
  
  // ✅ Load secure credentials from NVS
  if (!credManager.begin()) {
    Serial.println("\n❌ FATAL: Failed to load credentials from NVS!");
    Serial.println("💡 Solution: Run the setup script first to store credentials");
    while(1) delay(1000);
  }
  
  credManager.printStatus();
  
  // Load security keys
  credManager.getAESKey(aesKey);
  credManager.getHMACKey(hmacKey);
  
  Serial.print("Vehicle ID: ");
  Serial.println(credManager.getVehicleID());
  
  // Setup communication
  setupWiFi();
  setupFirebase();
  setupESPNow();
  
  Serial.println("\n✅ Real-time V2X System Ready!");
  Serial.println("📡 Firebase BSM: 10Hz (100ms)");
  Serial.println("📊 Firebase Telemetry: 1Hz (1000ms)");
  Serial.println("💚 Firebase Status: 0.2Hz (5000ms)\n");
}

// ==================== MAIN LOOP ====================
void loop() {
  unsigned long currentTime = millis();
  
  // Send BSM via ESP-NOW every 100ms (10Hz)
  if (currentTime - lastBSMTime >= BSM_INTERVAL) {
    sendBSM();
    lastBSMTime = currentTime;
  }
  
  // Upload BSM to Firebase every 100ms (10Hz) - REAL-TIME
  if (currentTime - lastFirebaseBSMTime >= FIREBASE_BSM_INTERVAL && firebaseReady) {
    uploadBSMToFirebase();
    lastFirebaseBSMTime = currentTime;
  }
  
  // Upload telemetry every 1 second (1Hz)
  if (currentTime - lastFirebaseTelemetryTime >= FIREBASE_TELEMETRY_INTERVAL && firebaseReady) {
    uploadTelemetryToFirebase();
    lastFirebaseTelemetryTime = currentTime;
  }
  
  // Upload system status every 5 seconds (0.2Hz)
  if (currentTime - lastFirebaseStatusTime >= FIREBASE_STATUS_INTERVAL && firebaseReady) {
    uploadSystemStatus();
    lastFirebaseStatusTime = currentTime;
  }
  
  // Print stats every 5 seconds
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

// ==================== FIREBASE SETUP ====================
void setupFirebase() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️  Cannot setup Firebase - No WiFi connection");
    return;
  }
  
  Serial.println("Setting up Firebase...");
  
  // Configure Firebase
  config.api_key = credManager.getAPIKey().c_str();
  config.database_url = credManager.getDatabaseURL().c_str();
  
  // Sign in
  auth.user.email = credManager.getUserEmail().c_str();
  auth.user.password = credManager.getUserPassword().c_str();
  
  // Assign callback function for token generation
  config.token_status_callback = tokenStatusCallback;
  
  // Initialize Firebase
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
  // Wait for token
  Serial.print("Waiting for Firebase token");
  int attempts = 0;
  while (!Firebase.ready() && attempts < 30) {
    Serial.print(".");
    delay(500);
    attempts++;
  }
  
  if (Firebase.ready()) {
    Serial.println("\n✅ Firebase Connected!");
    Serial.print("User UID: ");
    Serial.println(auth.token.uid.c_str());
    firebaseReady = true;
  } else {
    Serial.println("\n⚠️  Firebase connection failed");
    firebaseReady = false;
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

// ==================== FIREBASE UPLOAD - REAL-TIME ====================
void uploadBSMToFirebase() {
  if (!firebaseReady) return;
  
  // Path: /v2x/bsm/{vehicleId}
  String path = "/v2x/bsm/" + credManager.getVehicleID();
  
  FirebaseJson json;
  json.set("latitude", vehicleState.latitude);
  json.set("longitude", vehicleState.longitude);
  json.set("speed", vehicleState.speed);
  json.set("heading", vehicleState.heading);
  json.set("timestamp", (int)millis());
  
  // Use updateNodeSilent for faster non-blocking updates
  if (Firebase.RTDB.updateNodeSilent(&fbdo, path.c_str(), &json)) {
    stats.firebaseUploads++;
  } else {
    stats.firebaseErrors++;
  }
}

void uploadTelemetryToFirebase() {
  if (!firebaseReady) return;
  
  // Path: /telemetry/{vehicleId}
  String path = "/telemetry/" + credManager.getVehicleID();
  
  FirebaseJson json;
  json.set("battery_level", vehicleState.batteryLevel);
  
  FirebaseJson location;
  location.set("latitude", vehicleState.latitude);
  location.set("longitude", vehicleState.longitude);
  json.set("location", location);
  
  json.set("speed", vehicleState.speed);
  json.set("timestamp", (int)millis());
  
  if (Firebase.RTDB.updateNodeSilent(&fbdo, path.c_str(), &json)) {
    stats.firebaseUploads++;
  } else {
    stats.firebaseErrors++;
  }
}

void uploadSystemStatus() {
  if (!firebaseReady) return;
  
  // Path: /system_status/{vehicleId}
  String path = "/system_status/" + credManager.getVehicleID();
  
  FirebaseJson json;
  json.set("online", true);
  json.set("last_seen", (int)millis());
  
  if (Firebase.RTDB.updateNodeSilent(&fbdo, path.c_str(), &json)) {
    stats.firebaseUploads++;
  } else {
    stats.firebaseErrors++;
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
  
  // Simulate battery drain
  static unsigned long lastBatteryUpdate = 0;
  if (millis() - lastBatteryUpdate > 60000) {
    vehicleState.batteryLevel = max(0, vehicleState.batteryLevel - 1);
    lastBatteryUpdate = millis();
  }
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
  Serial.print("Firebase Uploads: "); Serial.println(stats.firebaseUploads);
  Serial.print("Firebase Errors: "); Serial.println(stats.firebaseErrors);
  Serial.print("Upload Rate: "); Serial.print(stats.firebaseUploads / (millis() / 1000.0)); Serial.println(" msg/s");
  Serial.print("Nearby Vehicles: "); Serial.println(nearbyVehicleCount);
  Serial.print("Firebase: "); Serial.println(firebaseReady ? "✓" : "✗");
  Serial.println("===================\n");
}