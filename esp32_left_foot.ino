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

// Timezone Configuration (seconds offset from UTC)
// Common timezones:
//   UTC:  0           PST/PDT: -28800 or -25200
//   EST/EDT: -18000 or -14400
//   CST/CDT: -21600 or -19800
//   MST/MDT: -25200 or -21600
//   GMT+8 (Singapore): +28800
const long TIMEZONE_OFFSET = 28800;   // Singapore Standard Time (UTC+8)
const int DST_OFFSET = 0;             // Singapore does not observe DST

// LEFT FOOT Sensor pins (configure based on your hardware)
#define bigToePin 34        // s6 - Left Big Toe
#define pinkyToePin 35      // s7 - Left Pinky Toe
#define metaHeadOutPin 32   // s8 - Left Meta Out
#define metaHeadInPin 33    // s9 - Left Meta In
#define heelPin 39          // s10 - Left Heel

// Sampling Configuration
#define sampleInterval 40      // ms (25 Hz sampling rate)
#define NUM_SAMPLES 25         // Number of samples to buffer before sending
#define OVERSAMPLES 7          // Number of readings to average per sample (increased for stability)
#define ADC_MAX 4095           // Maximum valid ADC reading (12-bit)
#define ADC_SANITY 3500        // Readings above this are likely noise/floating

// Dual buffering for continuous sampling during sending
unsigned long timestamps[NUM_SAMPLES];
uint16_t s6_buf[NUM_SAMPLES];
uint16_t s7_buf[NUM_SAMPLES];
uint16_t s8_buf[NUM_SAMPLES];
uint16_t s9_buf[NUM_SAMPLES];
uint16_t s10_buf[NUM_SAMPLES];

// Secondary buffer for data to send (swapped when primary is full)
unsigned long timestamps_send[NUM_SAMPLES];
uint16_t s6_send[NUM_SAMPLES];
uint16_t s7_send[NUM_SAMPLES];
uint16_t s8_send[NUM_SAMPLES];
uint16_t s9_send[NUM_SAMPLES];
uint16_t s10_send[NUM_SAMPLES];

uint8_t sampleIndex = 0;
bool sending = false;
HTTPClient http;  // Keep HTTP client persistent to avoid reallocation
bool http_in_use = false;

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
  // configTime(timezone_offset, dst_offset, server1, server2)
  configTime(TIMEZONE_OFFSET, DST_OFFSET, "pool.ntp.org", "time.google.com");
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
  
  // Sample sensors at defined interval (ALWAYS do this, never skip)
  if (currentTime - lastSampleTime >= sampleInterval) {
    lastSampleTime = currentTime;
    readSensor();
  }
  
  // When buffer is full, initiate async send (doesn't block sampling)
  if (sampleIndex >= NUM_SAMPLES && !sending) {
    sending = true;
    initiateAsyncSend();
  }
  
  // Check if async send is complete and send next batch
  if (sending && !http_in_use) {
    sending = false;
  }
}

/**
 * Sampling function - called at 25 Hz (every 40ms)
 * Reads all sensors with averaging and spike rejection
 */
void readSensor() {
  unsigned long ts = millis();
  
  // Oversample each sensor and average to reduce noise
  uint32_t sum6 = 0, sum7 = 0, sum8 = 0, sum9 = 0, sum10 = 0;
  for (int i = 0; i < OVERSAMPLES; i++) {
    sum6 += analogRead(bigToePin);
    sum7 += analogRead(pinkyToePin);
    sum8 += analogRead(metaHeadOutPin);
    sum9 += analogRead(metaHeadInPin);
    sum10 += analogRead(heelPin);
    delayMicroseconds(100);  // Small delay between readings
  }
  
  uint16_t v6 = sum6 / OVERSAMPLES;
  uint16_t v7 = sum7 / OVERSAMPLES;
  uint16_t v8 = sum8 / OVERSAMPLES;
  uint16_t v9 = sum9 / OVERSAMPLES;
  uint16_t v10 = sum10 / OVERSAMPLES;
  
  // Sanity check - if reading is unreasonably high, it's noise (floating pin)
  if (v6 > ADC_SANITY) v6 = 0;
  if (v7 > ADC_SANITY) v7 = 0;
  if (v8 > ADC_SANITY) v8 = 0;
  if (v9 > ADC_SANITY) v9 = 0;
  if (v10 > ADC_SANITY) v10 = 0;

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
 * Initiate async send - copies buffer and starts non-blocking send
 * This allows sampling to continue while HTTP request is in flight
 * Also filters out all-zero readings to reduce noise
 */
void initiateAsyncSend() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping send");
    sampleIndex = 0;  // Still reset buffer to prevent zeros
    return;
  }

  // Check if buffer contains meaningful data (not all zeros)
  // This prevents sending useless "standing still" data
  bool hasData = false;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    if (s6_buf[i] > 0 || s7_buf[i] > 0 || s8_buf[i] > 0 || 
        s9_buf[i] > 0 || s10_buf[i] > 0) {
      hasData = true;
      break;
    }
  }

  // If all zeros, discard this batch silently
  if (!hasData) {
    Serial.println("Buffer contains only zeros - skipping send (standing still)");
    sampleIndex = 0;
    return;
  }

  // Copy current buffer to send buffer (fast operation)
  memcpy(timestamps_send, timestamps, sizeof(timestamps));
  memcpy(s6_send, s6_buf, sizeof(s6_buf));
  memcpy(s7_send, s7_buf, sizeof(s7_buf));
  memcpy(s8_send, s8_buf, sizeof(s8_buf));
  memcpy(s9_send, s9_buf, sizeof(s9_buf));
  memcpy(s10_send, s10_buf, sizeof(s10_buf));

  // Reset collection buffer immediately so sampling continues
  sampleIndex = 0;

  // Now send (this will block, but buffer is already reset)
  sendDataBlocking();
}

/**
 * Send compact readings JSON to backend
 * Format: device_id + readings[] with {timestamp (epoch seconds), s1..s10}
 */
void sendDataBlocking() {
  http_in_use = true;
  
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
      long delta_ms = (long)(millisNow - timestamps_send[i]); // millisNow is >= timestamps_send[i]
      ts_sec = (long)epochNow - (delta_ms / 1000L);
    } else {
      // Fallback: send device-relative seconds since boot (rounded)
      ts_sec = timestamps_send[i] / 1000UL;
    }

    r["timestamp"] = ts_sec;
    
    // RIGHT FOOT sensors (s1-s5) - set to 0 since this is LEFT FOOT only
    r["s1"] = 0;
    r["s2"] = 0;
    r["s3"] = 0;
    r["s4"] = 0;
    r["s5"] = 0;
    
    // LEFT FOOT sensors (s6-s10) - raw analog values
    r["s6"] = s6_send[i];
    r["s7"] = s7_send[i];
    r["s8"] = s8_send[i];
    r["s9"] = s9_send[i];
    r["s10"] = s10_send[i];
  }

  String payload;
  serializeJson(doc, payload);
  Serial.print("Sending LEFT FOOT data: ");
  Serial.println(payload);
  
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

  http_in_use = false;
}
