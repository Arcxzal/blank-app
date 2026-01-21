/*
 * ESP32 Code for LEFT FOOT Pressure Sensors
 * 
 * This code sends LEFT FOOT pressure readings to your FastAPI backend.
 * Backend processes: stores data → calculates gait metrics → sends to Blynk
 * 
 * DEVICE: LEFT FOOT (sensors s6-s10)
 * 
 * MULTI-PATIENT SUPPORT:
 * - Set the patientID constant below to match the patient in your app
 * - To find patient IDs: Open Streamlit app → Sidebar → View patient list
 * - Demo patient is ID=1 (John Doe Demo)
 * - Create new patients in the app and use their ID here
 */

// Required Libraries
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

// WiFi Credentials
const char* ssid = "se";
const char* pass = "44448888";

// Backend API Configuration
const char* serverUrl = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/pressure";

// Device Configuration
const char* deviceID = "ESP32_LEFT_FOOT";  // Left foot device identifier

// Patient Configuration (append as query parameter)
// IMPORTANT: Set this to the patient ID from your Streamlit app
// - Use "1" for the demo patient (John Doe Demo)
// - Or create a new patient in the app and use that ID
const int patientID = 1;  // Change this to match your patient

// LEFT FOOT Sensor pins (configure based on your hardware)
#define bigToePin 34        // s6 - Left Big Toe
#define pinkyToePin 35      // s7 - Left Pinky Toe
#define metaHeadOutPin 32   // s8 - Left Meta Out
#define metaHeadInPin 33    // s9 - Left Meta In
#define heelPin 39          // s10 - Left Heel

// Sampling Configuration
#define sampleInterval 40      // ms (25 Hz sampling rate)
#define NUM_SAMPLES 25         // Number of samples to buffer before sending
unsigned long timestamps[NUM_SAMPLES];
uint16_t s6_buf[NUM_SAMPLES];
uint16_t s7_buf[NUM_SAMPLES];
uint16_t s8_buf[NUM_SAMPLES];
uint16_t s9_buf[NUM_SAMPLES];
uint16_t s10_buf[NUM_SAMPLES];
uint8_t sampleIndex = 0;
bool sending = false;

// Timing variables
unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(115200);
  
  Serial.println("========================================");
  Serial.println("ESP32 LEFT FOOT Pressure Sensor System");
  Serial.println("========================================");
  
  // Configure sensor pins
  pinMode(bigToePin, INPUT);
  pinMode(pinkyToePin, INPUT);
  pinMode(metaHeadOutPin, INPUT);
  pinMode(metaHeadInPin, INPUT);
  pinMode(heelPin, INPUT);
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n✓ WiFi Connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Device ID: ");
  Serial.println(deviceID);
  Serial.print("Patient ID: ");
  Serial.println(patientID);
  
  // Start NTP (UTC). We'll wait briefly for time to be obtained.
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  Serial.print("Waiting for NTP time");
  time_t now = time(nullptr);
  unsigned long start = millis();
  while (now < 1600000000UL && (millis() - start) < 10000) { // wait up to 10s
    delay(200);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println();
  if (now < 1600000000UL) {
    Serial.println("Warning: NTP time not available. Timestamps will be device-relative millis.");
  } else {
    Serial.print("NTP time set: ");
    Serial.println(ctime(&now));
  }
  
  Serial.println("========================================\n");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Sample sensors at defined interval
  if (currentTime - lastSampleTime >= sampleInterval) {
    lastSampleTime = currentTime;
    readSensor();
  }
  
  // When buffer is full, send data
  if (sampleIndex >= NUM_SAMPLES && !sending) {
    sending = true;
    sendData();
  }
}

/**
 * Sampling function - called at 25 Hz (every 40ms)
 * Reads all sensors and buffers the raw values
 */
void readSensor() {
  unsigned long ts = millis();
  uint16_t v6 = analogRead(bigToePin);
  uint16_t v7 = analogRead(pinkyToePin);
  uint16_t v8 = analogRead(metaHeadOutPin);
  uint16_t v9 = analogRead(metaHeadInPin);
  uint16_t v10 = analogRead(heelPin);

  Serial.printf("%lu,%u,%u,%u,%u,%u\n", ts, v6, v7, v8, v9, v10);

  if (sampleIndex < NUM_SAMPLES) {
    timestamps[sampleIndex] = ts;
    s6_buf[sampleIndex] = v6;
    s7_buf[sampleIndex] = v7;
    s8_buf[sampleIndex] = v8;
    s9_buf[sampleIndex] = v9;
    s10_buf[sampleIndex] = v10;
    sampleIndex++;
  }
}

/**
 * Send compact readings JSON to backend
 * Format: device_id + readings[] with {timestamp (epoch seconds), s1..s10}
 */
void sendData() {
  if (sampleIndex < NUM_SAMPLES) {
    sending = false;
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping send");
    sending = false;
    sampleIndex = 0;
    return;
  }

  // Get current epoch and millis to map stored millis -> epoch seconds
  time_t epochNow = time(nullptr);
  unsigned long millisNow = millis();

  StaticJsonDocument<4096> doc;
  doc["device_id"] = deviceID;
  JsonArray readings = doc.createNestedArray("readings");

  for (int i = 0; i < NUM_SAMPLES; i++) {
    JsonObject r = readings.createNestedObject();

    // Compute approximate epoch seconds for each stored sample
    // If NTP unavailable (epochNow < reasonable), fallback to sending millis delta (not epoch)
    long ts_sec;
    if (epochNow >= 1600000000L) {
      long delta_ms = (long)(millisNow - timestamps[i]); // millisNow is >= timestamps[i]
      ts_sec = (long)epochNow - (delta_ms / 1000L);
    } else {
      // Fallback: send device-relative seconds since boot (rounded)
      ts_sec = timestamps[i] / 1000UL;
    }

    r["timestamp"] = ts_sec;
    
    // RIGHT FOOT sensors (s1-s5) - set to 0 since this is LEFT FOOT only
    r["s1"] = 0;
    r["s2"] = 0;
    r["s3"] = 0;
    r["s4"] = 0;
    r["s5"] = 0;
    
    // LEFT FOOT sensors (s6-s10) - raw analog values
    r["s6"] = s6_buf[i];
    r["s7"] = s7_buf[i];
    r["s8"] = s8_buf[i];
    r["s9"] = s9_buf[i];
    r["s10"] = s10_buf[i];
  }

  String payload;
  serializeJson(doc, payload);
  Serial.print("Sending LEFT FOOT data: ");
  Serial.println(payload);

  HTTPClient http;
  
  // Add patient_id as query parameter
  String url = String(serverUrl) + "?patient_id=" + String(patientID);
  http.begin(url); // For HTTPS, underlying client will use TLS
  http.addHeader("Content-Type", "application/json");

  int httpResponseCode = http.POST(payload);
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("Response code: ");
    Serial.println(httpResponseCode);
    Serial.println("Response: " + response);
  } else {
    Serial.print("Error on sending POST: ");
    Serial.println(httpResponseCode);
  }
  http.end();

  // Reset buffer
  sampleIndex = 0;
  sending = false;
}
