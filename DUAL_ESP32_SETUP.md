# Dual ESP32 Setup Guide: Left & Right Foot Sensors

This guide explains how to set up and deploy **two separate ESP32 devices** for left and right foot pressure monitoring.

## Overview

You now have two separate ESP32 programs:
- **`esp32_right_foot.ino`** - Monitors RIGHT foot (sensors s1-s5)
- **`esp32_left_foot.ino`** - Monitors LEFT foot (sensors s6-s10)

Both devices send data to the same backend, which processes all 10 sensors together for comprehensive gait analysis.

## Hardware Setup

### Required Components (per foot)
- 1x ESP32 Development Board
- 5x Pressure sensors (one for each location)
- Jumper wires
- Power supply (USB or battery)

### Sensor Locations

**RIGHT FOOT (s1-s5):**
- s1: Big Toe
- s2: Pinky Toe
- s3: Meta Out (outside of ball)
- s4: Meta In (inside of ball)
- s5: Heel

**LEFT FOOT (s6-s10):**
- s6: Big Toe
- s7: Pinky Toe
- s8: Meta Out (outside of ball)
- s9: Meta In (inside of ball)
- s10: Heel

### Pin Configuration

**Default pins (you can modify these in the code):**

| Sensor Location | Right Foot Pin | Left Foot Pin |
|----------------|---------------|---------------|
| Big Toe        | GPIO 34       | GPIO 34       |
| Pinky Toe      | GPIO 35       | GPIO 35       |
| Meta Out       | GPIO 32       | GPIO 32       |
| Meta In        | GPIO 33       | GPIO 33       |
| Heel           | GPIO 25       | GPIO 25       |

**Note:** Both ESP32s can use the same pin numbers since they're separate devices.

## Software Configuration

### Step 1: Update WiFi Credentials

In **both** files, update:
```cpp
const char* ssid = "your-wifi-name";
const char* password = "your-wifi-password";
```

### Step 2: Update Backend URL

In **both** files, replace `your-backend-url` with your actual backend address:
```cpp
const char* backendURL = "http://192.168.1.100:8000/api/pressure";
const char* blynkUpdateURL = "http://192.168.1.100:8000/api/blynk/update";
```

**How to find your backend URL:**
- If running locally: Use your computer's local IP (e.g., `192.168.1.100`)
- If using Codespaces: Use your Codespaces forwarded URL
- If deployed: Use your public domain or IP

### Step 3: Set Patient ID

Both devices should use the **same patient ID** for a single patient:
```cpp
const int patientID = 1;  // Use the same ID for both feet
```

### Step 4: Customize Sensor Pins (Optional)

If your hardware uses different pins, update the pin definitions:

**In `esp32_right_foot.ino`:**
```cpp
const int RIGHT_BIGTOE_PIN = 34;     // Change to your pin
const int RIGHT_PINKYTOE_PIN = 35;   // Change to your pin
// ... etc
```

**In `esp32_left_foot.ino`:**
```cpp
const int LEFT_BIGTOE_PIN = 34;      // Change to your pin
const int LEFT_PINKYTOE_PIN = 35;    // Change to your pin
// ... etc
```

## Uploading the Code

### Option 1: Arduino IDE

1. **Install ESP32 Board Support:**
   - File → Preferences
   - Add to "Additional Board Manager URLs": 
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Tools → Board → Boards Manager → Search "ESP32" → Install

2. **Install Required Libraries:**
   - Sketch → Include Library → Manage Libraries
   - Install: `ArduinoJson` (by Benoit Blanchon)

3. **Upload Right Foot Code:**
   - Open `esp32_right_foot.ino`
   - Select: Tools → Board → ESP32 Dev Module
   - Select: Tools → Port → (your ESP32 port)
   - Click Upload

4. **Upload Left Foot Code:**
   - Connect the second ESP32
   - Open `esp32_left_foot.ino`
   - Select the new port
   - Click Upload

### Option 2: PlatformIO

Create `platformio.ini`:
```ini
[env:right_foot]
platform = espressif32
board = esp32dev
framework = arduino
upload_port = /dev/ttyUSB0  ; Adjust for your right foot ESP32
lib_deps = 
    bblanchon/ArduinoJson@^6.21.3

[env:left_foot]
platform = espressif32
board = esp32dev
framework = arduino
upload_port = /dev/ttyUSB1  ; Adjust for your left foot ESP32
lib_deps = 
    bblanchon/ArduinoJson@^6.21.3
```

Upload:
```bash
pio run --target upload --environment right_foot
pio run --target upload --environment left_foot
```

## Testing

### 1. Monitor Right Foot ESP32
```
Open Serial Monitor (115200 baud)

Expected output:
========================================
ESP32 RIGHT FOOT Pressure Sensor System
========================================
Connecting to WiFi...
✓ WiFi Connected
IP Address: 192.168.1.150
Device ID: ESP32_RIGHT_FOOT
Patient ID: 1
========================================

RIGHT FOOT Readings:
  Big Toe: 25.30  Pinky Toe: 15.20  Meta Out: 35.10  Meta In: 28.50  Heel: 42.00
Sending: {"device_id":"ESP32_RIGHT_FOOT","readings":[{"timestamp":1234,"s1":25.3,"s2":15.2,"s3":35.1,"s4":28.5,"s5":42.0,"s6":0.0,"s7":0.0,"s8":0.0,"s9":0.0,"s10":0.0}]}
Response code: 201
✓ Data sent to backend successfully
```

### 2. Monitor Left Foot ESP32
```
Open Serial Monitor (115200 baud)

Expected output:
========================================
ESP32 LEFT FOOT Pressure Sensor System
========================================
Connecting to WiFi...
✓ WiFi Connected
IP Address: 192.168.1.151
Device ID: ESP32_LEFT_FOOT
Patient ID: 1
========================================

LEFT FOOT Readings:
  Big Toe: 28.10  Pinky Toe: 18.50  Meta Out: 32.40  Meta In: 30.20  Heel: 45.30
Sending: {"device_id":"ESP32_LEFT_FOOT","readings":[{"timestamp":1234,"s1":0.0,"s2":0.0,"s3":0.0,"s4":0.0,"s5":0.0,"s6":28.1,"s7":18.5,"s8":32.4,"s9":30.2,"s10":45.3}]}
Response code: 201
✓ Data sent to backend successfully
```

### 3. Verify Backend Receives Both

Check your backend logs or database:
```bash
# Check recent pressure data
curl http://your-backend-url:8000/api/pressure/recent?patient_id=1&limit=10
```

You should see readings from both `ESP32_RIGHT_FOOT` and `ESP32_LEFT_FOOT`.

## Data Flow

```
┌─────────────────┐         ┌──────────────────┐         ┌────────────┐
│  Right Foot     │         │                  │         │            │
│  ESP32          │ ───────▶│                  │         │            │
│  (s1-s5)        │         │   FastAPI        │ ──────▶ │  Blynk     │
└─────────────────┘         │   Backend        │         │  App       │
                            │                  │         │            │
┌─────────────────┐         │   - Stores data  │         │  Displays: │
│  Left Foot      │         │   - Calculates   │         │  - Ratings │
│  ESP32          │ ───────▶│     metrics      │         │  - Metrics │
│  (s6-s10)       │         │   - Updates      │         │            │
└─────────────────┘         │     Blynk        │         │            │
                            └──────────────────┘         └────────────┘
```

## Troubleshooting

### WiFi Connection Issues
- Check SSID and password are correct
- Ensure WiFi network is 2.4GHz (ESP32 doesn't support 5GHz)
- Verify WiFi signal strength at sensor location

### Backend Connection Issues
- Verify backend is running: `curl http://your-backend-url:8000/health`
- Check firewall isn't blocking port 8000
- Ensure ESP32 can reach backend (same network or public access)
- Test with backend IP instead of hostname

### Sensor Reading Issues
- Check sensor connections and power
- Verify pin numbers match your hardware
- Add Serial.println() debugging in readPressureSensor()
- Test with known voltage on analog pins

### Different IP Addresses
Both ESP32s will get different IP addresses. This is normal and expected:
- Right Foot: e.g., 192.168.1.150
- Left Foot: e.g., 192.168.1.151

### Data Not Syncing
- Verify both devices use the **same patient ID**
- Check backend logs for errors
- Ensure timestamps are reasonable
- Verify JSON format is correct

## Advanced Configuration

### Adjust Sensor Calibration
In `readPressureSensor()` function, modify the mapping:
```cpp
// Current: 0-4095 → 0-100
float pressure = map(rawValue, 0, 4095, 0, 100);

// Custom range example: 0-4095 → 0-500 kPa
float pressure = (rawValue / 4095.0) * 500.0;
```

### Change Send Interval
```cpp
const unsigned long sendInterval = 2000; // Change to 1000 for 1 second, etc.
```

### Enable Automatic Blynk Updates
Uncomment in the `loop()` function:
```cpp
if (success) {
    Serial.println("✓ Data sent to backend successfully\n");
    triggerBlynkUpdate();  // Uncomment this line
}
```

### Add Sensor Smoothing
```cpp
float readPressureSensor(int pin) {
  const int numReadings = 10;
  float sum = 0;
  
  for (int i = 0; i < numReadings; i++) {
    int rawValue = analogRead(pin);
    sum += map(rawValue, 0, 4095, 0, 100);
    delay(10);
  }
  
  return sum / numReadings;  // Return average
}
```

## Next Steps

1. ✅ Upload code to both ESP32 devices
2. ✅ Verify WiFi connections
3. ✅ Test sensor readings in Serial Monitor
4. ✅ Confirm backend receives data from both devices
5. ✅ Check Blynk app shows combined metrics
6. ✅ Start walking to generate real gait data!

## Support

For issues or questions:
- Check backend logs: `docker logs <backend-container>`
- Review Streamlit dashboard for data visualization
- Test API endpoints with curl or Postman
- Monitor Serial output for debugging messages
