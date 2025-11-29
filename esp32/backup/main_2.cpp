/*
 * SECURE ESP32 V2X System - Vehicle 2 (SDV002)
 * Firebase Integration matching existing rules structure
 */

#include <WiFi.h>
#include <esp_now.h>
#include <Firebase_ESP_Client.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <mbedtls/aes.h>
#include <Preferences.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// ==================== SECURE CONFIGURATION ====================
Preferences preferences;

String WIFI_SSID;
String WIFI_PASSWORD;
String API_KEY;
String DATABASE_URL;
String USER_EMAIL;
String USER_PASSWORD;
String VEHICLE_ID = "SDV002";  // Vehicle 2

uint8_t HMAC_KEY[32];
uint8_t AES_KEY[16];

// Firebase objects
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;
bool firebaseReady = false;

// ==================== MESSAGE STRUCTURES ====================
#define MSG_BSM 0x01
#define MSG_EMERGENCY 0x02
#define MSG_HAZARD 0x03

struct SecureBSMMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  uint32_t nonce;
  float latitude;
  float longitude;
  float speed;
  float heading;
  uint8_t hmac[32];
};

struct SecureHazardMessage {
  uint8_t msgType;
  char vehicleId[16];
  uint32_t timestamp;
  uint32_t nonce;
  float latitude;
  float longitude;
  uint8_t hazardType;
  char description[64];
  uint8_t hmac[32];
};

// ==================== SECURITY STATE ====================
struct SecurityState {
  uint32_t messageCounter = 0;
  uint32_t receivedMessages = 0;
  uint32_t rejectedMessages = 0;
  uint32_t replayAttempts = 0;
  uint32_t authFailures = 0;
  uint32_t lastNonces[20];
  int nonceCount = 0;
} security;

struct RateLimiter {
  unsigned long lastMessageTime[10];
  int messageCount[10];
  String vehicleIds[10];
  int trackedVehicles = 0;
} rateLimiter;

struct Stats {
  uint32_t firebaseUploads = 0;
  uint32_t firebaseErrors = 0;
} stats;

struct VehicleState {
  float latitude = 30.0450;  // Different location for Vehicle 2
  float longitude = 31.2360;
  float speed = 22.3;
  float heading = 180.0;
  uint8_t batteryLevel = 92;
} vehicleState;

unsigned long lastFirebaseBSMUpload = 0;
unsigned long lastFirebaseTelemetryUpload = 0;
unsigned long lastFirebaseStatusUpload = 0;

// REAL-TIME Firebase Configuration
#define FIREBASE_BSM_INTERVAL 100        // 10Hz - Real-time position
#define FIREBASE_TELEMETRY_INTERVAL 1000 // 1Hz - Battery, etc
#define FIREBASE_STATUS_INTERVAL 5000    // 0.2Hz - System health

// ==================== FUNCTION PROTOTYPES ====================
bool loadSecureCredentials();
void setupWiFi();
void setupFirebase();
void setupSecureESPNow();
void calculateHMAC(uint8_t* data, size_t len, uint8_t* hmac);
bool verifyHMAC(uint8_t* data, size_t len, uint8_t* receivedHmac);
bool checkReplayAttack(uint32_t nonce, uint32_t timestamp);
bool checkRateLimit(const char* vehicleId);
void sendSecureBSM();
void onSecureDataReceived(const uint8_t *mac, const uint8_t *data, int len);
void processValidBSM(SecureBSMMessage* msg);
void onDataSent(const uint8_t *mac, esp_now_send_status_t status);
void uploadBSMToFirebase();
void uploadTelemetryToFirebase();
void uploadSystemStatus();
void printSecurityStatus();
void printSecurityStats();

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=== SECURE ESP32 V2X - Vehicle 2 (SDV002) ===");
  
  if (!loadSecureCredentials()) {
    Serial.println("ERROR: Failed to load credentials!");
    Serial.println("Please run credential setup first.");
    while(1) delay(1000);
  }
  
  Serial.print("Vehicle ID: ");
  Serial.println(VEHICLE_ID);
  
  setupWiFi();
  setupFirebase();
  setupSecureESPNow();
  
  Serial.println("✅ Secure V2X System Ready!");
  printSecurityStatus();
}

// ==================== CREDENTIAL MANAGEMENT ====================
bool loadSecureCredentials() {
  preferences.begin("v2x-secure", true);
  
  WIFI_SSID = preferences.getString("wifi_ssid", "");
  WIFI_PASSWORD = preferences.getString("wifi_pass", "");
  API_KEY = preferences.getString("api_key", "");
  DATABASE_URL = preferences.getString("db_url", "");
  USER_EMAIL = preferences.getString("user_email", "");
  USER_PASSWORD = preferences.getString("user_pass", "");
  VEHICLE_ID = preferences.getString("vehicle_id", "SDV002");
  
  size_t hmacLen = preferences.getBytes("hmac_key", HMAC_KEY, 32);
  size_t aesLen = preferences.getBytes("aes_key", AES_KEY, 16);
  
  preferences.end();
  
  bool valid = (WIFI_SSID.length() > 0 && 
                WIFI_PASSWORD.length() > 0 &&
                hmacLen == 32 && 
                aesLen == 16);
  
  if (!valid) {
    Serial.println("⚠️  Missing credentials in secure storage");
  }
  
  return valid;
}

// ==================== WIFI SETUP ====================
void setupWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(WIFI_SSID.c_str(), WIFI_PASSWORD.c_str());
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠️  WiFi Failed");
  }
}

// ==================== FIREBASE SETUP ====================
void setupFirebase() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️  Cannot setup Firebase - No WiFi");
    return;
  }
  
  Serial.println("Setting up Firebase...");
  
  config.api_key = API_KEY.c_str();
  config.database_url = DATABASE_URL.c_str();
  
  auth.user.email = USER_EMAIL.c_str();
  auth.user.password = USER_PASSWORD.c_str();
  
  config.token_status_callback = tokenStatusCallback;
  
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
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
void setupSecureESPNow() {
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ ESP-NOW init failed!");
    return;
  }
  
  Serial.println("✅ ESP-NOW initialized (secure mode)");
  
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onSecureDataReceived);
  
  esp_now_peer_info_t peerInfo = {};
  uint8_t broadcastAddr[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  memcpy(peerInfo.peer_addr, broadcastAddr, 6);
  peerInfo.channel = WiFi.channel();
  peerInfo.encrypt = false;  // Broadcast doesn't support encryption
  
  if (esp_now_add_peer(&peerInfo) == ESP_OK) {
    Serial.println("✅ Broadcast peer added");
  }
}

// ==================== HMAC AUTHENTICATION ====================
void calculateHMAC(uint8_t* data, size_t len, uint8_t* hmac) {
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
  
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, HMAC_KEY, 32);
  mbedtls_md_hmac_update(&ctx, data, len);
  mbedtls_md_hmac_finish(&ctx, hmac);
  mbedtls_md_free(&ctx);
}

bool verifyHMAC(uint8_t* data, size_t len, uint8_t* receivedHmac) {
  uint8_t calculatedHmac[32];
  calculateHMAC(data, len, calculatedHmac);
  
  uint8_t diff = 0;
  for (int i = 0; i < 32; i++) {
    diff |= calculatedHmac[i] ^ receivedHmac[i];
  }
  
  return (diff == 0);
}

// ==================== REPLAY PROTECTION ====================
bool checkReplayAttack(uint32_t nonce, uint32_t timestamp) {
  for (int i = 0; i < security.nonceCount; i++) {
    if (security.lastNonces[i] == nonce) {
      security.replayAttempts++;
      return true;
    }
  }
  
  unsigned long currentTime = millis();
  if (abs((long)(currentTime - timestamp)) > 5000) {
    return true;
  }
  
  if (security.nonceCount < 20) {
    security.lastNonces[security.nonceCount++] = nonce;
  } else {
    for (int i = 0; i < 19; i++) {
      security.lastNonces[i] = security.lastNonces[i + 1];
    }
    security.lastNonces[19] = nonce;
  }
  
  return false;
}

// ==================== RATE LIMITING ====================
bool checkRateLimit(const char* vehicleId) {
  unsigned long currentTime = millis();
  
  int idx = -1;
  for (int i = 0; i < rateLimiter.trackedVehicles; i++) {
    if (rateLimiter.vehicleIds[i] == String(vehicleId)) {
      idx = i;
      break;
    }
  }
  
  if (idx == -1 && rateLimiter.trackedVehicles < 10) {
    idx = rateLimiter.trackedVehicles++;
    rateLimiter.vehicleIds[idx] = String(vehicleId);
    rateLimiter.messageCount[idx] = 0;
    rateLimiter.lastMessageTime[idx] = currentTime;
  }
  
  if (idx == -1) return false;
  
  if (currentTime - rateLimiter.lastMessageTime[idx] < 1000) {
    rateLimiter.messageCount[idx]++;
    if (rateLimiter.messageCount[idx] > 50) {
      Serial.printf("⚠️  Rate limit exceeded for %s\n", vehicleId);
      return false;
    }
  } else {
    rateLimiter.messageCount[idx] = 1;
    rateLimiter.lastMessageTime[idx] = currentTime;
  }
  
  return true;
}

// ==================== SEND BSM ====================
void sendSecureBSM() {
  SecureBSMMessage msg;
  memset(&msg, 0, sizeof(SecureBSMMessage));
  
  msg.msgType = MSG_BSM;
  strncpy(msg.vehicleId, VEHICLE_ID.c_str(), 15);
  msg.vehicleId[15] = '\0';
  msg.timestamp = millis();
  msg.nonce = security.messageCounter++;
  
  msg.latitude = vehicleState.latitude;
  msg.longitude = vehicleState.longitude;
  msg.speed = vehicleState.speed;
  msg.heading = vehicleState.heading;
  
  calculateHMAC((uint8_t*)&msg, sizeof(SecureBSMMessage) - 32, msg.hmac);
  
  uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_now_send(broadcastAddress, (uint8_t*)&msg, sizeof(SecureBSMMessage));
}

// ==================== RECEIVE MESSAGES ====================
void onSecureDataReceived(const uint8_t *mac, const uint8_t *data, int len) {
  if (len < 1) return;
  
  uint8_t msgType = data[0];
  
  if (msgType == MSG_BSM && len == sizeof(SecureBSMMessage)) {
    SecureBSMMessage* msg = (SecureBSMMessage*)data;
    
    if (!verifyHMAC((uint8_t*)msg, sizeof(SecureBSMMessage) - 32, msg->hmac)) {
      security.authFailures++;
      Serial.println("❌ HMAC verification failed!");
      return;
    }
    
    if (checkReplayAttack(msg->nonce, msg->timestamp)) {
      Serial.println("❌ Replay attack detected!");
      return;
    }
    
    if (!checkRateLimit(msg->vehicleId)) {
      Serial.println("❌ Rate limit exceeded!");
      return;
    }
    
    security.receivedMessages++;
    processValidBSM(msg);
  }
}

void processValidBSM(SecureBSMMessage* msg) {
  if (String(msg->vehicleId) == VEHICLE_ID) return;
  
  Serial.print("✅ BSM from ");
  Serial.print(msg->vehicleId);
  Serial.print(": ");
  Serial.print(msg->latitude, 6);
  Serial.print(",");
  Serial.print(msg->longitude, 6);
  Serial.print(" @ ");
  Serial.print(msg->speed);
  Serial.println(" km/h");
}

// ==================== FIREBASE UPLOAD ====================
void uploadBSMToFirebase() {
  if (!firebaseReady) return;
  
  // Path: /v2x/bsm/SDV002
  String path = "/v2x/bsm/" + VEHICLE_ID;
  
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
  
  // Path: /telemetry/SDV002
  String path = "/telemetry/" + VEHICLE_ID;
  
  FirebaseJson json;
  json.set("battery_level", vehicleState.batteryLevel);
  
  FirebaseJson location;
  location.set("latitude", vehicleState.latitude);
  location.set("longitude", vehicleState.longitude);
  json.set("location", location);
  
  json.set("speed", vehicleState.speed);
  json.set("timestamp", (int)millis());
  
  if (Firebase.RTDB.setJSON(&fbdo, path.c_str(), &json)) {
    stats.firebaseUploads++;
  } else {
    stats.firebaseErrors++;
    Serial.print("Telemetry upload failed: ");
    Serial.println(fbdo.errorReason());
  }
}

void uploadSystemStatus() {
  if (!firebaseReady) return;
  
  // Path: /system_status/SDV002
  String path = "/system_status/" + VEHICLE_ID;
  
  FirebaseJson json;
  json.set("online", true);
  json.set("last_seen", (int)millis());
  
  if (Firebase.RTDB.setJSON(&fbdo, path.c_str(), &json)) {
    stats.firebaseUploads++;
  } else {
    stats.firebaseErrors++;
  }
}

// ==================== STATUS ====================
void printSecurityStatus() {
  Serial.println("\n=== SECURITY STATUS ===");
  Serial.println("✅ HMAC-SHA256 Authentication: ENABLED");
  Serial.println("✅ Replay Protection: ACTIVE");
  Serial.println("✅ Rate Limiting: ENABLED");
  Serial.println("✅ Secure Credentials: LOADED");
  Serial.print("✅ Firebase: ");
  Serial.println(firebaseReady ? "CONNECTED" : "DISCONNECTED");
  Serial.println("=======================\n");
}

void printSecurityStats() {
  Serial.println("\n=== SECURITY STATISTICS ===");
  Serial.printf("Messages Received: %u\n", security.receivedMessages);
  Serial.printf("Messages Rejected: %u\n", security.rejectedMessages);
  Serial.printf("Replay Attempts: %u\n", security.replayAttempts);
  Serial.printf("Auth Failures: %u\n", security.authFailures);
  Serial.printf("Firebase Uploads: %u\n", stats.firebaseUploads);
  Serial.printf("Firebase Errors: %u\n", stats.firebaseErrors);
  Serial.println("==========================\n");
}

// ==================== MAIN LOOP ====================
void loop() {
  static unsigned long lastBSM = 0;
  static unsigned long lastStats = 0;
  
  unsigned long currentTime = millis();
  
  // Send BSM every 100ms (10Hz)
  if (currentTime - lastBSM >= 100) {
    sendSecureBSM();
    lastBSM = currentTime;
  }
  
  // Upload BSM to Firebase every 100ms (10Hz) - REAL-TIME
  if (currentTime - lastFirebaseBSMUpload >= FIREBASE_BSM_INTERVAL && firebaseReady) {
    uploadBSMToFirebase();
    lastFirebaseBSMUpload = currentTime;
  }
  
  // Upload telemetry every 1 second (1Hz)
  if (currentTime - lastFirebaseTelemetryUpload >= FIREBASE_TELEMETRY_INTERVAL && firebaseReady) {
    uploadTelemetryToFirebase();
    lastFirebaseTelemetryUpload = currentTime;
  }
  
  // Upload system status every 5 seconds (0.2Hz)
  if (currentTime - lastFirebaseStatusUpload >= FIREBASE_STATUS_INTERVAL && firebaseReady) {
    uploadSystemStatus();
    lastFirebaseStatusUpload = currentTime;
  }
  
  // Print stats every 10 seconds
  if (currentTime - lastStats >= 10000) {
    printSecurityStats();
    lastStats = currentTime;
  }
  
  delay(10);
}

// ==================== CALLBACKS ====================
void onDataSent(const uint8_t *mac, esp_now_send_status_t status) {
  // Silent on success
}