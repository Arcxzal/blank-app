# ESP32 → Python → Blynk Integration

Complete system for real-time gait analysis with Blynk monitoring.

## System Architecture

```
┌─────────┐         ┌─────────────┐         ┌──────────────────┐         ┌────────────┐
│  ESP32  │ ──────▶ │   FastAPI   │ ──────▶ │  Gait Analysis   │ ──────▶ │   Blynk    │
│ Sensors │  HTTP   │   Backend   │  Calc   │  (processing.py) │  Push   │   Cloud    │
└─────────┘         └─────────────┘         └──────────────────┘         └────────────┘
                           │                                                      │
                           ▼                                                      ▼
                    ┌─────────────┐                                      ┌────────────┐
                    │  PostgreSQL │                                      │ Blynk App  │
                    │   Database  │                                      │  (Mobile)  │
                    └─────────────┘                                      └────────────┘
```

## What Gets Sent to Blynk

### 1. Pressure Ratings (V0-V4)
- **Big Toe** (V0): "Normal", "Weak", or "High"
- **Pinky Toe** (V1): "Normal", "Weak", or "High"
- **Meta Out** (V2): "Normal", "Weak", or "High"
- **Meta In** (V3): "Normal", "Weak", or "High"
- **Heel** (V4): "Normal", "Weak", or "High"

### 2. Gait Metrics (V5-V8)
- **Cadence** (V5): Steps per minute (e.g., 112.5)
- **Swing Time** (V6): Seconds (e.g., 0.45)
- **Stance Time** (V7): Seconds (e.g., 0.68)
- **Step Symmetry** (V8): Percentage 0-100% (e.g., 94.3%)

## Setup Instructions

### Step 1: Configure Blynk App

1. **Create a new project** in Blynk app
2. **Copy your Auth Token** from project settings
3. **Add widgets:**

| Widget | Virtual Pin | Range | Purpose |
|--------|-------------|-------|---------|
| LED or Label | V0 | - | Big Toe Rating |
| LED or Label | V1 | - | Pinky Toe Rating |
| LED or Label | V2 | - | Meta Out Rating |
| LED or Label | V3 | - | Meta In Rating |
| LED or Label | V4 | - | Heel Rating |
| Gauge | V5 | 0-180 | Cadence |
| Value Display | V6 | 0-2 | Swing Time |
| Value Display | V7 | 0-2 | Stance Time |
| Gauge | V8 | 0-100 | Step Symmetry |

4. **Configure LED colors** (for V0-V4):
   - Green: "Normal"
   - Yellow: "Weak"
   - Red: "High"

### Step 2: Update Backend Configuration

Edit `backend/blynk_service.py`:

```python
BLYNK_AUTH_TOKEN = "YOUR_BLYNK_AUTH_TOKEN_HERE"
```

### Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Start Backend Server

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 5: Test Blynk Connection

```bash
python backend/test_blynk.py
```

Expected output:
```
============================================================
Blynk Integration Test
============================================================

1. Initializing Blynk service...
2. Testing Blynk connection...
   ✓ Connection successful!

3. Generating test pressure data...
   ✓ Generated 1500 data points

4. Calculating pressure ratings...
   Ratings:
     - bigToe: Normal
     - pinkyToe: Normal
     - metaOut: Normal
     - metaIn: Normal
     - heel: Normal

5. Calculating gait metrics...
   Metrics:
     - Cadence: 112.5 steps/min
     - Swing Time: 0.45 seconds
     - Stance Time: 0.68 seconds
     - Step Symmetry: 94.3%

6. Sending data to Blynk...
   ✓ Data sent successfully!

Check your Blynk app to see the updated values!
```

### Step 6: Configure ESP32

1. Open `esp32_python_blynk_integration.ino`
2. Update configuration:

```cpp
// WiFi Credentials
const char* ssid = "your_wifi_ssid";
const char* password = "your_wifi_password";

// Backend API URL (replace with your actual URL)
const char* backendURL = "http://192.168.1.100:8000/api/pressure";
const char* blynkUpdateURL = "http://192.168.1.100:8000/api/blynk/update";
```

3. Upload to ESP32
4. Open Serial Monitor to verify data transmission

## How It Works

### 1. ESP32 Sends Raw Data

ESP32 reads pressure sensors and sends JSON to backend:

```json
{
  "device_id": "ESP32_01",
  "readings": [{
    "timestamp": 1234567890,
    "s1": 42.5,  // Big Toe
    "s2": 35.2,  // Pinky Toe
    "s3": 38.1,  // Meta Out
    "s4": 36.4,  // Meta In
    "s5": 45.8,  // Heel
    "s6": 40.0,  // Left Big Toe (optional)
    "s7": 34.0,  // Left Pinky Toe (optional)
    "s8": 37.0,  // Left Meta Out (optional)
    "s9": 35.0,  // Left Meta In (optional)
    "s10": 44.0  // Left Heel (optional)
  }]
}
```

### 2. Backend Processes Data

Python backend:
- Stores data in database
- Applies Savitzky-Golay filtering
- Detects heel strikes and toe-offs
- Calculates gait metrics
- Determines pressure ratings

### 3. Backend Pushes to Blynk

Automatically sends:
- Pressure ratings → V0-V4
- Gait metrics → V5-V8

### 4. Blynk Displays Data

Your mobile app shows real-time:
- Color-coded pressure status
- Live cadence gauge
- Gait timing metrics
- Symmetry percentage

## API Endpoints

### Get Metrics (with automatic Blynk push)

```bash
GET http://localhost:8000/api/gait-metrics?limit=100
```

Response:
```json
{
  "ratings": {
    "bigToe": "Normal",
    "pinkyToe": "Normal",
    "metaOut": "Normal",
    "metaIn": "Normal",
    "heel": "Normal"
  },
  "metrics": {
    "cadence": 112.5,
    "swing_time": 0.45,
    "stance_time": 0.68,
    "step_symmetry": 94.3
  },
  "blynk_sent": true
}
```

### Manually Trigger Blynk Update

```bash
POST http://localhost:8000/api/blynk/update?limit=100
```

## Update Frequency Options

### Option 1: Automatic (On Data Receipt)

Backend automatically calculates and sends to Blynk whenever `/api/gait-metrics` is called.

### Option 2: ESP32 Triggered

ESP32 calls `/api/blynk/update` after sending data:

```cpp
void loop() {
  // Send pressure data
  sendToBackend(...);
  
  // Trigger Blynk update every 50 readings
  if (readingCount % 50 == 0) {
    triggerBlynkUpdate();
  }
}
```

### Option 3: Scheduled (Python)

Add background task to update every N seconds:

```python
# In backend/app_main.py
from fastapi_utils.tasks import repeat_every

@app.on_event("startup")
@repeat_every(seconds=5)
async def update_blynk_periodically():
    """Update Blynk every 5 seconds"""
    blynk_service = get_blynk_service()
    # Fetch latest data and send
    ...
```

## Rating Thresholds

Customize in `backend/blynk_service.py`:

```python
thresholds = {
    'bigToe': {'weak': 8, 'high': 45},
    'pinkyToe': {'weak': 5, 'high': 40},
    'metaOut': {'weak': 20, 'high': 50},
    'metaIn': {'weak': 20, 'high': 50},
    'heel': {'weak': 15, 'high': 55}
}
```

## Troubleshooting

### ESP32 can't connect to backend

- Check IP address is correct
- Ensure backend is running on port 8000
- Verify ESP32 and backend are on same network
- Check firewall settings

### Blynk not receiving data

1. Verify auth token is correct
2. Check Blynk app has all virtual pins configured
3. Test with `python backend/test_blynk.py`
4. Check backend logs for errors

### Metrics show zero

- Need at least 100 data points for accurate calculation
- Ensure pressure values are non-zero
- Check that sampling frequency is set correctly (25 Hz)

### Connection timeouts

- Blynk free tier has rate limits
- Don't update more than once per second
- Consider batching updates

## Advanced Configuration

### Multi-Device Support

Track multiple ESP32 devices:

```python
# Different auth tokens per device
device_tokens = {
    "ESP32_01": "token_1",
    "ESP32_02": "token_2"
}
```

### Custom Virtual Pins

Add more metrics by extending `blynk_service.py`:

```python
PIN_STRIDE_LENGTH = 9  # V9
PIN_GROUND_CONTACT_TIME = 10  # V10

# In send_to_blynk():
self.blynk.virtual_write(9, stride_length)
self.blynk.virtual_write(10, ground_contact_time)
```

### Historical Data

Use SuperChart widget in Blynk to visualize trends over time.

## Files Overview

| File | Purpose |
|------|---------|
| `backend/blynk_service.py` | Blynk integration logic |
| `backend/app_main.py` | FastAPI endpoints |
| `backend/test_blynk.py` | Test script |
| `processing.py` | Gait analysis algorithms |
| `esp32_python_blynk_integration.ino` | ESP32 firmware |
| `BLYNK_SETUP.md` | Detailed setup guide |

## Next Steps

1. ✅ Test Blynk connection
2. ✅ Upload ESP32 code
3. ✅ Verify data flow
4. 📱 Customize Blynk dashboard
5. 🔧 Adjust thresholds for your use case
6. 📊 Add historical tracking
7. 🚀 Deploy to production

## Support

- FastAPI docs: `http://localhost:8000/docs`
- Test endpoint: `http://localhost:8000/api/gait-metrics`
- Blynk docs: https://docs.blynk.io/

## License

See LICENSE file for details.
