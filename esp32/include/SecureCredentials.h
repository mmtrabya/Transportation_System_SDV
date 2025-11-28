/*
 * SecureCredentials.h - Secure Credential Manager for ESP32
 * Stores and retrieves credentials from NVS (Non-Volatile Storage)
 * 
 * Usage:
 *   SecureCredentialManager credManager;
 *   credManager.begin();
 *   String ssid = credManager.getWiFiSSID();
 */

#ifndef SECURE_CREDENTIALS_H
#define SECURE_CREDENTIALS_H

#include <Arduino.h>
#include <Preferences.h>

class SecureCredentialManager {
private:
    Preferences preferences;
    bool initialized = false;
    
    // Cached credentials
    struct {
        String wifiSsid;
        String wifiPassword;
        String apiKey;
        String databaseUrl;
        String userEmail;
        String userPassword;
        String vehicleId;
        String mqttServer;
        String mqttUser;
        String mqttPassword;
    } creds;
    
    // Security keys
    uint8_t hmacKey[32];
    uint8_t aesKey[16];
    
public:
    SecureCredentialManager() {}
    
    // Initialize and load credentials
    bool begin() {
        Serial.println("\n=== Secure Credential Manager ===");
        
        if (loadCredentials()) {
            Serial.println("✓ Credentials loaded from secure storage");
            initialized = true;
            return true;
        } else {
            Serial.println("✗ Failed to load credentials from NVS");
            initialized = false;
            return false;
        }
    }
    
    // Load credentials from NVS
    bool loadCredentials() {
        preferences.begin("v2x-secure", true);  // Read-only
        
        // Load all credentials
        creds.wifiSsid = preferences.getString("wifi_ssid", "");
        creds.wifiPassword = preferences.getString("wifi_pass", "");
        creds.apiKey = preferences.getString("api_key", "");
        creds.databaseUrl = preferences.getString("db_url", "");
        creds.userEmail = preferences.getString("user_email", "");
        creds.userPassword = preferences.getString("user_pass", "");
        creds.vehicleId = preferences.getString("vehicle_id", "");
        creds.mqttServer = preferences.getString("mqtt_server", "");
        creds.mqttUser = preferences.getString("mqtt_user", "");
        creds.mqttPassword = preferences.getString("mqtt_pass", "");
        
        // Load security keys
        size_t hmacLen = preferences.getBytes("hmac_key", hmacKey, 32);
        size_t aesLen = preferences.getBytes("aes_key", aesKey, 16);
        
        preferences.end();
        
        // Validate all required credentials are present
        bool valid = (creds.wifiSsid.length() > 0 &&
                     creds.wifiPassword.length() > 0 &&
                     creds.vehicleId.length() > 0 &&
                     hmacLen == 32 &&
                     aesLen == 16);
        
        return valid;
    }
    
    // Getters for credentials
    String getWiFiSSID() { return creds.wifiSsid; }
    String getWiFiPassword() { return creds.wifiPassword; }
    String getAPIKey() { return creds.apiKey; }
    String getDatabaseURL() { return creds.databaseUrl; }
    String getUserEmail() { return creds.userEmail; }
    String getUserPassword() { return creds.userPassword; }
    String getVehicleID() { return creds.vehicleId; }
    String getMQTTServer() { return creds.mqttServer; }
    String getMQTTUser() { return creds.mqttUser; }
    String getMQTTPassword() { return creds.mqttPassword; }
    
    void getHMACKey(uint8_t* buffer) { memcpy(buffer, hmacKey, 32); }
    void getAESKey(uint8_t* buffer) { memcpy(buffer, aesKey, 16); }
    
    bool isInitialized() { return initialized; }
    
    // Print status (with masked credentials)
    void printStatus() {
        Serial.println("\n=== Credential Status ===");
        Serial.print("WiFi SSID: ");
        Serial.println(maskString(creds.wifiSsid));
        Serial.print("Vehicle ID: ");
        Serial.println(creds.vehicleId);
        Serial.print("MQTT Server: ");
        Serial.println(maskString(creds.mqttServer));
        Serial.print("Security Keys: ");
        Serial.println(initialized ? "✓ Loaded" : "✗ Missing");
        Serial.println("========================\n");
    }
    
    // Clear all credentials (for reset)
    void clearCredentials() {
        Serial.println("⚠️  Clearing all credentials...");
        preferences.begin("v2x-secure", false);
        preferences.clear();
        preferences.end();
        Serial.println("✓ Credentials cleared");
        initialized = false;
    }
    
private:
    // Mask sensitive strings for display
    String maskString(const String& str, int showChars = 4) {
        if (str.length() == 0) return "***";
        if (str.length() <= showChars) return "***";
        return str.substring(0, showChars) + "***";
    }
};

#endif // SECURE_CREDENTIALS_H