/*
 * ESP32 Code for RIGHT FOOT Pressure Sensors
 * 
 * This code sends RIGHT FOOT pressure readings to your FastAPI backend.
 * Backend processes: stores data → calculates gait metrics → sends to Blynk
 * 
 * DEVICE: RIGHT FOOT (sensors s1-s5)
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
const char* deviceID = "ESP32_RIGHT_FOOT";  // Right foot device identifier

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

// RIGHT FOOT Sensor pins (configure based on your hardware)
#define bigToePin 34        // s1 - Right Big Toe
#define pinkyToePin 35      // s2 - Right Pinky Toe
#define metaHeadOutPin 32   // s3 - Right Meta Out
#define metaHeadInPin 33    // s4 - Right Meta In
#define heelPin 39          // s5 - Right Heel

// Sampling Configuration
#define sampleInterval 40      // ms (25 Hz sampling rate)
#define NUM_SAMPLES 25         // Number of samples to buffer before sending
#define OVERSAMPLES 7          // Number of readings to average per sample (increased for stability)
#define ADC_MAX 4095           // Maximum valid ADC reading (12-bit)
#define ADC_SANITY 3500        // Readings above this are likely noise/floating

// Dual buffering for continuous sampling during sending
unsigned long timestamps[NUM_SAMPLES];
uint16_t s1_buf[NUM_SAMPLES];
uint16_t s2_buf[NUM_SAMPLES];
uint16_t s3_buf[NUM_SAMPLES];
uint16_t s4_buf[NUM_SAMPLES];
uint16_t s5_buf[NUM_SAMPLES];

// Secondary buffer for data to send (swapped when primary is full)
unsigned long timestamps_send[NUM_SAMPLES];
uint16_t s1_send[NUM_SAMPLES];
uint16_t s2_send[NUM_SAMPLES];
uint16_t s3_send[NUM_SAMPLES];
uint16_t s4_send[NUM_SAMPLES];
uint16_t s5_send[NUM_SAMPLES];

uint8_t sampleIndex = 0;
bool sending = false;
HTTPClient http;  // Keep HTTP client persistent to avoid reallocation
bool http_in_use = false;

// Timing variables
unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(115200);
  
  Serial.println("========================================");
  Serial.println("ESP32 RIGHT FOOT Pressure Sensor System");
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
  uint32_t sum1 = 0, sum2 = 0, sum3 = 0, sum4 = 0, sum5 = 0;
  for (int i = 0; i < OVERSAMPLES; i++) {
    sum1 += analogRead(bigToePin);
    sum2 += analogRead(pinkyToePin);
    sum3 += analogRead(metaHeadOutPin);
    sum4 += analogRead(metaHeadInPin);
    sum5 += analogRead(heelPin);
    delayMicroseconds(100);  // Small delay between readings
  }
  
  uint16_t v1 = sum1 / OVERSAMPLES;
  uint16_t v2 = sum2 / OVERSAMPLES;
  uint16_t v3 = sum3 / OVERSAMPLES;
  uint16_t v4 = sum4 / OVERSAMPLES;
  uint16_t v5 = sum5 / OVERSAMPLES;
  
  // Sanity check - if reading is unreasonably high, it's noise (floating pin)
  if (v1 > ADC_SANITY) v1 = 0;
  if (v2 > ADC_SANITY) v2 = 0;
  if (v3 > ADC_SANITY) v3 = 0;
  if (v4 > ADC_SANITY) v4 = 0;
  if (v5 > ADC_SANITY) v5 = 0;

  Serial.printf("%lu,%u,%u,%u,%u,%u\n", ts, v1, v2, v3, v4, v5);

  if (sampleIndex < NUM_SAMPLES) {
    timestamps[sampleIndex] = ts;
    s1_buf[sampleIndex] = v1;
    s2_buf[sampleIndex] = v2;
    s3_buf[sampleIndex] = v3;
    s4_buf[sampleIndex] = v4;
    s5_buf[sampleIndex] = v5;
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
    if (s1_buf[i] > 0 || s2_buf[i] > 0 || s3_buf[i] > 0 || 
        s4_buf[i] > 0 || s5_buf[i] > 0) {
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
  memcpy(s1_send, s1_buf, sizeof(s1_buf));
  memcpy(s2_send, s2_buf, sizeof(s2_buf));
  memcpy(s3_send, s3_buf, sizeof(s3_buf));
  memcpy(s4_send, s4_buf, sizeof(s4_buf));
  memcpy(s5_send, s5_buf, sizeof(s5_buf));

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
    
    // RIGHT FOOT sensors (s1-s5) - raw analog values
    r["s1"] = s1_send[i];
    r["s2"] = s2_send[i];
    r["s3"] = s3_send[i];
    r["s4"] = s4_send[i];
    r["s5"] = s5_send[i];
    
    // LEFT FOOT sensors (s6-s10) - set to 0 since this is RIGHT FOOT only
    r["s6"] = 0;
    r["s7"] = 0;
    r["s8"] = 0;
    r["s9"] = 0;
    r["s10"] = 0;
  }

  String payload;
  serializeJson(doc, payload);
  Serial.print("Sending RIGHT FOOT data: ");
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
