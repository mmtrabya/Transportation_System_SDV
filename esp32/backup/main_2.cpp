#include <WiFi.h>
#include <esp_now.h>
#include <Firebase_ESP_Client.h>
#include <ArduinoJson.h>
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>

// ==================== FIREBASE CONFIGURATION ====================
#define WIFI_SSID "Tarabay madinaty"
#define WIFI_PASSWORD "Tarabay_2379"

// Firebase Project Configuration
#define API_KEY "AIzaSyDPEAz-ao5mRfyLRwf4VtYjsiiiYat5Hfs"
#define DATABASE_URL "https://sdv-ota-system-default-rtdb.europe-west1.firebasedatabase.app"
#define USER_EMAIL "sdv002@kynetic.com"
#define USER_PASSWORD "Kynetic2025"

#define VEHICLE_ID "SDV002"

// ==================== V2X MESSAGE TYPES ====================
#define MSG_BSM 0x01
#define MSG_EMERGENCY 0x02
#define MSG_HAZARD 0x03
#define MSG_SIGNAL 0x04

#define BSM_INTERVAL 100      // 10Hz
#define FIREBASE_SYNC_INTERVAL 1000  // 1Hz

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
FirebaseData fbdo;
FirebaseData stream;
FirebaseAuth auth;
FirebaseConfig config;

bool firebaseReady = false;
unsigned long lastBSMTime = 0;
unsigned long lastFirebaseSyncTime = 0;
unsigned long dataUpdateMillis = 0;

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
  uint32_t firebaseSynced = 0;
  uint32_t firebaseErrors = 0;
} stats;

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=== ESP32 Firebase V2X System ===");
  Serial.print("Vehicle ID: ");
  Serial.println(VEHICLE_ID);
  
  // Setup WiFi
  setupWiFi();
  
  // Setup Firebase
  setupFirebase();
  
  // Setup ESP-NOW
  setupESPNow();
  
  Serial.println("V2X System Ready!");
}

// ==================== MAIN LOOP ====================
void loop() {
  unsigned long currentTime = millis();
  
  // Send BSM via ESP-NOW (10Hz)
  if (currentTime - lastBSMTime >= BSM_INTERVAL) {
    sendBSM();
    lastBSMTime = currentTime;
  }
  
  // Sync with Firebase (1Hz)
  if (currentTime - lastFirebaseSyncTime >= FIREBASE_SYNC_INTERVAL) {
    syncWithFirebase();
    lastFirebaseSyncTime = currentTime;
  }
  
  // Handle serial commands
  if (Serial.available()) {
    serialCommandHandler();
  }
  
  // Update vehicle state
  updateVehicleState();
  
  // Cleanup old vehicles
  cleanupOldVehicles();
  
  delay(10);
}

// ==================== WiFi SETUP ====================
void setupWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_AP_STA);
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
    Serial.println("\nWiFi Failed! Continuing with ESP-NOW only.");
  }
}

// ==================== FIREBASE SETUP ====================
void setupFirebase() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("No WiFi - Firebase disabled");
    return;
  }
  
  Serial.println("Initializing Firebase...");
  
  // Configure Firebase
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  
  // Sign in
  auth.user.email = USER_EMAIL;
  auth.user.password = USER_PASSWORD;
  
  // Token status callback
  config.token_status_callback = tokenStatusCallback;
  
  // Initialize
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
  // Set buffer sizes
  fbdo.setBSSLBufferSize(2048, 1024);
  
  Serial.println("Firebase initialized");
  
  // Setup stream for real-time messages
  setupFirebaseStream();
}

void tokenStatusCallback(TokenInfo info) {
  Serial.printf("Token: %s\n", info.status == token_status_ready ? "Ready" : "Not Ready");
  firebaseReady = (info.status == token_status_ready);
}

void setupFirebaseStream() {
  if (!Firebase.ready()) return;
  
  // Stream for receiving V2X messages
  String streamPath = "/v2x/messages/" + String(VEHICLE_ID);
  
  if (Firebase.RTDB.beginStream(&stream, streamPath.c_str())) {
    Serial.println("Firebase stream started");
    Firebase.RTDB.setStreamCallback(&stream, streamCallback, streamTimeoutCallback);
  } else {
    Serial.printf("Stream failed: %s\n", stream.errorReason().c_str());
  }
}

void streamCallback(FirebaseStream data) {
  Serial.println("Firebase stream data received");
  
  if (data.dataType() == "json") {
    FirebaseJson json = data.jsonObject();
    
    // Parse and process V2X message
    FirebaseJsonData type;
    if (json.get(type, "type")) {
      String msgType = type.stringValue;
      
      if (msgType == "emergency") {
        processFirebaseEmergency(json);
      } else if (msgType == "hazard") {
        processFirebaseHazard(json);
      } else if (msgType == "signal") {
        processFirebaseSignal(json);
      }
    }
  }
}

void streamTimeoutCallback(bool timeout) {
  if (timeout) {
    Serial.println("Firebase stream timeout");
  }
}

// ==================== ESP-NOW SETUP ====================
void setupESPNow() {
  uint8_t wifiChannel = WiFi.channel();
  Serial.print("WiFi Channel: ");
  Serial.println(wifiChannel);
  
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed!");
    return;
  }
  
  Serial.println("ESP-NOW initialized");
  
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataReceived);
  
  // Add broadcast peer
  esp_now_peer_info_t peerInfo = {};
  uint8_t broadcastAddr[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  memcpy(peerInfo.peer_addr, broadcastAddr, 6);
  peerInfo.channel = wifiChannel;
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) == ESP_OK) {
    Serial.println("Broadcast peer added");
  }
}

// ==================== ESP-NOW CALLBACKS ====================
void onDataSent(const uint8_t *mac, esp_now_send_status_t status) {
  // Silent on success
}

void onDataReceived(const uint8_t *mac, const uint8_t *data, int len) {
  if (len < 1) return;
  
  uint8_t msgType = data[0];
  
  switch (msgType) {
    case MSG_BSM:
      if (len == sizeof(BSMMessage)) {
        BSMMessage* bsm = (BSMMessage*)data;
        if (verifyChecksum((uint8_t*)bsm, sizeof(BSMMessage) - 2, bsm->checksum)) {
          processReceivedBSM(bsm);
          stats.bsmReceived++;
          
          // Forward to Firebase
          publishBSMToFirebase(bsm);
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
  strncpy(bsm.vehicleId, VEHICLE_ID, 16);
  bsm.timestamp = millis();
  bsm.latitude = vehicleState.latitude;
  bsm.longitude = vehicleState.longitude;
  bsm.altitude = vehicleState.altitude;
  bsm.speed = vehicleState.speed;
  bsm.heading = vehicleState.heading;
  bsm.acceleration = vehicleState.acceleration;
  bsm.brakingStatus = vehicleState.brakingStatus;
  
  bsm.checksum = calculateChecksum((uint8_t*)&bsm, sizeof(BSMMessage) - 2);
  
  uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_now_send(broadcastAddress, (uint8_t*)&bsm, sizeof(BSMMessage));
  
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
  
  // Also publish to Firebase
  publishHazardToFirebase(&hazard);
  
  Serial.println("Hazard warning sent!");
}

// ==================== FIREBASE OPERATIONS ====================
void syncWithFirebase() {
  if (!Firebase.ready()) return;
  
  // Update vehicle status
  String statusPath = "/vehicles/" + String(VEHICLE_ID) + "/status";
  
  FirebaseJson json;
  json.set("latitude", vehicleState.latitude);
  json.set("longitude", vehicleState.longitude);
  json.set("speed", vehicleState.speed);
  json.set("heading", vehicleState.heading);
  json.set("nearby_vehicles", nearbyVehicleCount);
  json.set("timestamp", millis());
  json.set("bsm_sent", stats.bsmSent);
  json.set("bsm_received", stats.bsmReceived);
  
  if (Firebase.RTDB.setJSON(&fbdo, statusPath.c_str(), &json)) {
    stats.firebaseSynced++;
  } else {
    stats.firebaseErrors++;
  }
}

void publishBSMToFirebase(BSMMessage* msg) {
  if (!Firebase.ready()) return;
  if (strcmp(msg->vehicleId, VEHICLE_ID) == 0) return;  // Don't publish own messages
  
  String path = "/v2x/bsm/" + String(msg->vehicleId);
  
  FirebaseJson json;
  json.set("vehicle_id", msg->vehicleId);
  json.set("latitude", msg->latitude);
  json.set("longitude", msg->longitude);
  json.set("speed", msg->speed);
  json.set("heading", msg->heading);
  json.set("timestamp", msg->timestamp);
  
  Firebase.RTDB.setJSONAsync(&fbdo, path.c_str(), &json);
}

void publishHazardToFirebase(HazardMessage* msg) {
  if (!Firebase.ready()) return;
  
  String path = "/v2x/hazards/" + String(millis());
  
  FirebaseJson json;
  json.set("vehicle_id", msg->vehicleId);
  json.set("latitude", msg->latitude);
  json.set("longitude", msg->longitude);
  json.set("hazard_type", msg->hazardType);
  json.set("description", msg->description);
  json.set("timestamp", msg->timestamp);
  
  Firebase.RTDB.setJSONAsync(&fbdo, path.c_str(), &json);
}

void processFirebaseEmergency(FirebaseJson& json) {
  FirebaseJsonData data;
  
  if (json.get(data, "vehicle_id")) {
    String vehicleId = data.stringValue;
    Serial.print("FIREBASE_EMERGENCY:");
    Serial.println(vehicleId);
  }
}

void processFirebaseHazard(FirebaseJson& json) {
  Serial.println("FIREBASE_HAZARD received");
}

void processFirebaseSignal(FirebaseJson& json) {
  Serial.println("FIREBASE_SIGNAL received");
}

// ==================== PROCESS RECEIVED MESSAGES ====================
void processReceivedBSM(BSMMessage* msg) {
  if (strcmp(msg->vehicleId, VEHICLE_ID) == 0) return;
  
  // Update nearby vehicles
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
  
  // Forward to Pi
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
  Serial.print(msg->description);
  Serial.println();
}

void processReceivedEmergency(EmergencyMessage* msg) {
  Serial.print("V2V_EMERGENCY:");
  Serial.print(msg->vehicleId);
  Serial.print(",");
  Serial.print(msg->emergencyType);
  Serial.println();
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

void updateVehicleState() {
  // Simulate movement
  static float simSpeed = 0.0;
  simSpeed += random(-5, 6) / 100.0;
  simSpeed = constrain(simSpeed, 0.0, 30.0);
  vehicleState.speed = simSpeed;
}

void serialCommandHandler() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  
  if (cmd.startsWith("UPDATE:")) {
    // Parse: UPDATE:lat,lon,speed,heading,accel
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
    
  } else if (cmd == "STATS") {
    Serial.println("=== V2X Statistics ===");
    Serial.print("BSM Sent: "); Serial.println(stats.bsmSent);
    Serial.print("BSM Received: "); Serial.println(stats.bsmReceived);
    Serial.print("Nearby Vehicles: "); Serial.println(nearbyVehicleCount);
    Serial.print("Firebase Syncs: "); Serial.println(stats.firebaseSynced);
    Serial.print("Firebase Errors: "); Serial.println(stats.firebaseErrors);
    Serial.print("Firebase Ready: "); Serial.println(firebaseReady ? "Yes" : "No");
    Serial.println("===================");
    
  } else if (cmd.startsWith("HAZARD:")) {
    uint8_t type = cmd.substring(7, cmd.indexOf(',')).toInt();
    String desc = cmd.substring(cmd.indexOf(',') + 1);
    sendHazardWarning(type, desc.c_str());
  }
}