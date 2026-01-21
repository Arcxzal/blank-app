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

// Blynk Configuration (optional - left in but not required)
#define BLYNK_TEMPLATE_ID "TMPL6-ZsV0hu_"
#define BLYNK_TEMPLATE_NAME "readRight"
#define BLYNK_AUTH_TOKEN "qCSvSCCeRSutZIb7CPt4Ppvp0qyEij_o"

// Required Libraries
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <BlynkSimpleEsp32.h>
#include <BlynkApiArduino.h>

// WiFi Credentials
char auth[] = BLYNK_AUTH_TOKEN; // optional for Blynk
char ssid[] = "se";
char pass[] = "44448888";

// Backend API Configuration
const char* serverUrl = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/pressure";

// Device Configuration
const char* deviceID = "ESP32_RIGHT_FOOT";  // Right foot device identifier

// Patient Configuration (append as query parameter)
// IMPORTANT: Set this to the patient ID from your Streamlit app
// - Use "1" for the demo patient (John Doe Demo)
// - Or create a new patient in the app and use that ID
const int patientID = 1;  // Change this to match your patient

// RIGHT FOOT Sensor pins (configure based on your hardware)
#define bigToePin 34        // s1 - Right Big Toe
#define pinkyToePin 35      // s2 - Right Pinky Toe
#define metaHeadOutPin 32   // s3 - Right Meta Out
#define metaHeadInPin 33    // s4 - Right Meta In
#define heelPin 39          // s5 - Right Heel

// Sampling Configuration
#define sampleInterval 40      // ms (25 Hz sampling rate)
#define NUM_SAMPLES 25         // Number of samples to buffer before sending
unsigned long timestamps[NUM_SAMPLES];
uint16_t s1_buf[NUM_SAMPLES];
uint16_t s2_buf[NUM_SAMPLES];
uint16_t s3_buf[NUM_SAMPLES];
uint16_t s4_buf[NUM_SAMPLES];
uint16_t s5_buf[NUM_SAMPLES];
uint8_t sampleIndex = 0;
bool sending = false;

// Timer (BlynkTimer is same as SimpleTimer)
BlynkTimer timer;

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
  
  // Schedule sampling at 25 Hz
  timer.setInterval(sampleInterval, readSensor);
}

void loop() {
  timer.run();
  
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
  uint16_t v1 = analogRead(bigToePin);
  uint16_t v2 = analogRead(pinkyToePin);
  uint16_t v3 = analogRead(metaHeadOutPin);
  uint16_t v4 = analogRead(metaHeadInPin);
  uint16_t v5 = analogRead(heelPin);

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
    
    // RIGHT FOOT sensors (s1-s5) - raw analog values
    r["s1"] = s1_buf[i];
    r["s2"] = s2_buf[i];
    r["s3"] = s3_buf[i];
    r["s4"] = s4_buf[i];
    r["s5"] = s5_buf[i];
    
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
