# Blynk Integration Setup Guide

This guide explains how to integrate your ESP32 pressure sensor system with Blynk for real-time monitoring of gait metrics and pressure ratings.

## Architecture

```
ESP32 → FastAPI Backend → Processing & Analysis → Blynk Cloud → Mobile App
```

**Flow:**
1. ESP32 sends raw pressure data to FastAPI backend (`/api/pressure`)
2. Backend stores data in database
3. Backend automatically calculates gait metrics and pressure ratings
4. Backend pushes calculated values to Blynk Cloud
5. Blynk mobile app displays real-time data

## Installation

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `blynk-library-python` - Blynk Python SDK
- `numpy`, `scipy`, `pandas` - For signal processing and gait analysis

### 2. Configure Blynk Auth Token

Edit `/workspaces/blank-app/backend/blynk_service.py` and update:

```python
BLYNK_AUTH_TOKEN = "qCSvSCCeRSutZIb7CPt4Ppvp0qyEij_o"  # Replace with your token
```

Get your auth token from the Blynk app settings.

## Virtual Pin Configuration

Configure these virtual pins in your Blynk app:

| Pin | Data | Widget Type | Range/Format |
|-----|------|-------------|--------------|
| **V0** | Big Toe Rating | Label/LED | "Normal", "Weak", "High" |
| **V1** | Pinky Toe Rating | Label/LED | "Normal", "Weak", "High" |
| **V2** | Meta Out Rating | Label/LED | "Normal", "Weak", "High" |
| **V3** | Meta In Rating | Label/LED | "Normal", "Weak", "High" |
| **V4** | Heel Rating | Label/LED | "Normal", "Weak", "High" |
| **V5** | Cadence | Gauge | 0-180 steps/min |
| **V6** | Swing Time | Value Display | 0-2.0 seconds |
| **V7** | Stance Time | Value Display | 0-2.0 seconds |
| **V8** | Step Symmetry | Gauge | 0-100% |

### Recommended Widgets

**For Ratings (V0-V4):**
- Use **LED** widgets with color coding:
  - Green = "Normal"
  - Yellow = "Weak" 
  - Red = "High"
- OR use **Label** widgets to display text

**For Metrics (V5-V8):**
- V5 (Cadence): **Gauge** widget (0-180)
- V6, V7 (Times): **Value Display** with 2 decimal places
- V8 (Symmetry): **Gauge** widget (0-100) or **SuperChart** for history

## API Endpoints

### 1. Get Gait Metrics (Auto-sends to Blynk)

```bash
GET /api/gait-metrics?limit=100
```

**Response:**
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

### 2. Manually Trigger Blynk Update

```bash
POST /api/blynk/update?limit=100
```

**Response:**
```json
{
  "status": "success",
  "data_points_analyzed": 100,
  "ratings": { ... },
  "metrics": { ... },
  "blynk_sent": true
}
```

## Testing

### Test Blynk Connection

Run the test script:

```bash
cd /workspaces/blank-app
python backend/test_blynk.py
```

This will:
1. Test Blynk connection
2. Generate mock pressure data
3. Calculate ratings and metrics
4. Send to Blynk app

Check your Blynk mobile app to verify data appears.

### Test via API

```bash
# Start the backend server
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# In another terminal, test the endpoint
curl http://localhost:8000/api/gait-metrics
```

## Automatic Updates

### Option 1: Call from ESP32

Have your ESP32 trigger the Blynk update after sending data:

```cpp
// In your ESP32 code, after sending pressure data
HTTPClient http;
http.begin("http://your-backend-url:8000/api/blynk/update");
http.POST("");
http.end();
```

### Option 2: Background Task (Coming Soon)

We can add a background task to automatically push to Blynk every N seconds.

### Option 3: Streamlit Integration

Call the endpoint from your Streamlit dashboard:

```python
import requests

# In your Streamlit page
if st.button("Update Blynk"):
    response = requests.post("http://localhost:8000/api/blynk/update")
    if response.status_code == 200:
        st.success("✓ Blynk updated!")
```

## Rating Logic

Pressure ratings are based on these thresholds:

| Sensor | Weak Threshold | High Threshold |
|--------|----------------|----------------|
| Big Toe | < 8 | > 45 |
| Pinky Toe | < 5 | > 40 |
| Meta Out | < 20 | > 50 |
| Meta In | < 20 | > 50 |
| Heel | < 15 | > 55 |

Values between thresholds = "Normal"

## Gait Metrics Calculation

Metrics are calculated using:
- **Savitzky-Golay filtering** for signal smoothing
- **Heel-strike detection** from heel sensor peaks
- **Toe-off detection** from forefoot pressure drops
- **Cadence** from interval between heel strikes
- **Stance time** from heel-strike to toe-off duration
- **Swing time** from toe-off to next heel-strike duration
- **Step symmetry** from total load comparison between feet

See `/workspaces/blank-app/processing.py` for implementation details.

## Troubleshooting

### Connection Failed

- Verify your auth token is correct
- Check internet connectivity
- Ensure Blynk app is properly configured

### No Data in Blynk

- Make sure virtual pins V0-V8 are configured in Blynk app
- Check that widgets are assigned to correct pins
- Verify data type matches (string for ratings, number for metrics)

### Metrics Show Zero

- Ensure you have enough data points (default: 100 readings)
- Check that pressure data is being stored in database
- Verify gait events are being detected (heel strikes, toe-offs)

### API Errors

Check logs:
```bash
# Backend logs
tail -f backend/logs/app.log

# Test specific endpoint
curl -v http://localhost:8000/api/gait-metrics
```

## Security Note

⚠️ **Important:** The Blynk auth token in this code is hardcoded for demonstration. 

For production:
1. Move token to environment variable:
   ```python
   BLYNK_AUTH_TOKEN = os.getenv("BLYNK_AUTH_TOKEN", "default_token")
   ```

2. Create `.env` file:
   ```bash
   BLYNK_AUTH_TOKEN=your_actual_token_here
   ```

3. Add `.env` to `.gitignore`

## Next Steps

1. ✅ Configure virtual pins in Blynk app
2. ✅ Test connection with `backend/test_blynk.py`
3. ✅ Verify data appears in Blynk app
4. 🔄 Set up automatic updates (ESP32 or background task)
5. 📱 Customize Blynk dashboard layout
6. 📊 Add SuperChart widgets for historical data

## Support

For issues or questions:
- Check FastAPI docs: http://localhost:8000/docs
- Review processing logic in `processing.py`
- Test with mock data using `test_blynk.py`
