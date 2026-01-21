/*
 * ESP32 Code for Sending Pressure Data to Python Backend
 * 
 * This code sends pressure readings to your FastAPI backend, which then:
 * 1. Stores the data in the database
 * 2. Calculates gait metrics (cadence, swing time, stance time, symmetry)
 * 3. Calculates pressure ratings (Normal/Weak/High)
 * 4. Sends everything to Blynk automatically
 * 
 * MULTI-PATIENT SUPPORT:
 * - Set the patientID constant below to match the patient in your app
 * - To find patient IDs: Open Streamlit app → Sidebar → View patient list
 * - Demo patient is ID=1 (John Doe Demo)
 * - Create new patients in the app and use their ID here
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// WiFi Credentials
const char* ssid = "se";
const char* password = "44448888";

// Backend API Configuration
const char* backendURL = "http://your-backend-url:8000/api/pressure";
const char* blynkUpdateURL = "http://your-backend-url:8000/api/blynk/update";

// Device Configuration
const char* deviceID = "ESP32_01";

// Patient Configuration
// IMPORTANT: Set this to the patient ID from your Streamlit app
// - Use "1" for the demo patient (John Doe Demo)
// - Or create a new patient in the app and use that ID
const int patientID = 1;  // Change this to match your patient

// Timing
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 2000; // Send every 2 seconds

// Sensor pins (configure based on your hardware)
const int BIGTOE_PIN = 34;
const int PINKYTOE_PIN = 35;
const int METAOUT_PIN = 32;
const int METAIN_PIN = 33;
const int HEEL_PIN = 25;

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n✓ WiFi Connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  unsigned long currentTime = millis();
  
  // Send data every sendInterval milliseconds
  if (currentTime - lastSendTime >= sendInterval) {
    lastSendTime = currentTime;
    
    // Read pressure sensors
    float bigToePressure = readPressureSensor(BIGTOE_PIN);
    float pinkyToePressure = readPressureSensor(PINKYTOE_PIN);
    float metaOutPressure = readPressureSensor(METAOUT_PIN);
    float metaInPressure = readPressureSensor(METAIN_PIN);
    float heelPressure = readPressureSensor(HEEL_PIN);
    
    // Send to backend
    bool success = sendToBackend(
      bigToePressure,
      pinkyToePressure,
      metaOutPressure,
      metaInPressure,
      heelPressure
    );
    
    if (success) {
      Serial.println("✓ Data sent to backend successfully");
      
      // Optional: Trigger Blynk update after every N readings
      // Uncomment to enable:
      // triggerBlynkUpdate();
    } else {
      Serial.println("✗ Failed to send data");
    }
  }
}

/**
 * Read pressure from sensor
 * Replace this with your actual sensor reading logic
 */
float readPressureSensor(int pin) {
  // Read analog value (0-4095 on ESP32)
  int rawValue = analogRead(pin);
  
  // Convert to pressure value (adjust based on your sensor calibration)
  float pressure = map(rawValue, 0, 4095, 0, 100);
  
  return pressure;
}

/**
 * Send pressure data to FastAPI backend
 * Backend will automatically calculate metrics and send to Blynk
 */
bool sendToBackend(float bigToe, float pinkyToe, float metaOut, float metaIn, float heel) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return false;
  }
  
  HTTPClient http;
  
  // Build URL with patient_id query parameter
  String url = String(backendURL) + "?patient_id=" + String(patientID);
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload using the compact format
  // Format: {"device_id": "ESP32_01", "readings": [{"timestamp": 1234567890, "s1": 25.3, ...}]}
  
  StaticJsonDocument<512> doc;
  doc["device_id"] = deviceID;
  
  JsonArray readings = doc.createNestedArray("readings");
  JsonObject reading = readings.createNestedObject();
  
  // Get current timestamp (Unix epoch)
  unsigned long timestamp = millis() / 1000; // Simple timestamp for demo
  reading["timestamp"] = timestamp;
  
  // Right foot sensors (s1-s5)
  reading["s1"] = bigToe;
  reading["s2"] = pinkyToe;
  reading["s3"] = metaOut;
  reading["s4"] = metaIn;
  reading["s5"] = heel;
  
  // Left foot sensors (s6-s10) - set to 0 if you don't have left foot sensors
  reading["s6"] = 0.0;
  reading["s7"] = 0.0;
  reading["s8"] = 0.0;
  reading["s9"] = 0.0;
  reading["s10"] = 0.0;
  
  // Serialize JSON
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Debug output
  Serial.print("Sending: ");
  Serial.println(jsonString);
  
  // Send POST request
  int httpResponseCode = http.POST(jsonString);
  
  http.end();
  
  return (httpResponseCode == 201 || httpResponseCode == 200);
}

/**
 * Trigger Blynk update manually
 * Call this after you've accumulated enough data points (e.g., every 50 readings)
 */
void triggerBlynkUpdate() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  HTTPClient http;
  
  // Build URL with patient_id query parameter
  String url = String(blynkUpdateURL) + "?patient_id=" + String(patientID);
  http.begin(url);
  
  int httpResponseCode = http.POST("");
  
  if (httpResponseCode == 200) {
    Serial.println("✓ Blynk update triggered");
  } else {
    Serial.print("✗ Blynk update failed: ");
    Serial.println(httpResponseCode);
  }
  
  http.end();
}
