# 🏥 Multi-Patient System Setup Guide

## System Status ✅

Your multi-patient pressure monitoring system is fully operational! Here's what's ready:

### ✅ Completed Setup
1. **Database** - Patient table with relationships to pressure data
2. **Backend API** - Patient management endpoints (create, list, delete)
3. **Frontend UI** - Patient selector and add patient form
4. **Demo Patient** - Pre-configured for testing (ID=1, "John Doe Demo")
5. **Blynk Integration** - Configured for real-time monitoring
6. **ESP32 Code** - Updated to support patient_id parameter

---

## 📱 Quick Start: Using the App

### 1. Access the Dashboard
Open your Streamlit app at: **http://localhost:8501**

### 2. Patient Selection
- In the **sidebar**, you'll see a dropdown with available patients
- **Demo Patient** uses synthetic test data
- **Real patients** show actual ESP32 data

### 3. Add a New Patient
1. Click **"➕ Add New Patient"** in the sidebar
2. Fill in:
   - Patient Name (e.g., "Jane Smith")
   - Age (e.g., 28)
   - Notes (e.g., "Post-surgery rehabilitation")
3. Click **"Add Patient"**
4. The new patient will appear in the dropdown

---

## 🔧 ESP32 Configuration

### Update Your ESP32 Code

1. **Open** `esp32_python_blynk_integration.ino`

2. **Update WiFi credentials** (lines 16-17):
   ```cpp
   const char* ssid = "YOUR_WIFI_NAME";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

3. **Update backend URL** (line 20):
   ```cpp
   const char* backendURL = "http://YOUR_BACKEND_IP:8000/api/pressure";
   ```
   
   💡 **Find your backend IP:**
   - If running locally: Use your computer's IP address
   - If in Docker/cloud: Use the container/server IP
   - Example: `http://192.168.1.100:8000/api/pressure`

4. **Set patient ID** (line 28):
   ```cpp
   const int patientID = 1;  // Change this to match your patient
   ```
   
   🎯 **How to find patient IDs:**
   - Open Streamlit app → Sidebar → View patient list
   - Demo patient is always ID=1
   - Newly created patients get sequential IDs (2, 3, 4...)

5. **Upload to ESP32** and monitor Serial output

---

## 🧪 Testing the System

### Test 1: Verify Patient API
```bash
# List all patients
curl http://localhost:8000/api/patients

# Get specific patient
curl http://localhost:8000/api/patients/1
```

### Test 2: Send Test Data
```bash
# Run the test script
python3 test_api.py
```

This will:
- List all patients
- Send test data for patient 1
- Fetch and display the readings

### Test 3: Create a Patient via API
```bash
curl -X POST http://localhost:8000/api/patients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Patient",
    "age": 30,
    "notes": "Created via API"
  }'
```

### Test 4: ESP32 Data Flow
1. Upload ESP32 code with correct patient_id
2. Open Serial Monitor to see data being sent
3. Check Streamlit app → Select that patient
4. Verify data appears in real-time

---

## 📊 How Data Flows

```
┌─────────────┐
│   ESP32     │ ──┐
│ patient_id=1│   │
└─────────────┘   │
                  │  POST /api/pressure?patient_id=1
┌─────────────┐   │  {"readings": [...]}
│   ESP32     │ ──┤
│ patient_id=2│   │
└─────────────┘   │
                  ▼
           ┌──────────────┐
           │   FastAPI    │
           │   Backend    │
           └──────┬───────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
  ┌──────────┐      ┌─────────────┐
  │ Database │      │   Blynk     │
  │ patient_id=1    │ Real-time   │
  │ patient_id=2    │ Monitoring  │
  └──────────┘      └─────────────┘
        │
        │ GET /api/readings?patient_id=1
        ▼
  ┌──────────────┐
  │  Streamlit   │
  │  Dashboard   │
  └──────────────┘
```

---

## 🔐 Patient Data Isolation

Each patient's data is **completely isolated**:

✅ **ESP32 sends with patient_id** → Data tagged to specific patient  
✅ **Database filters by patient_id** → Each query returns only that patient's data  
✅ **Frontend selector** → Switch between patients instantly  
✅ **Blynk updates** → Can scope metrics per patient

---

## 🎯 Common Use Cases

### Use Case 1: Single Patient (Real Data)
1. Create patient in app: "John Smith"
2. Set ESP32 `patientID = 2` (use the ID from the app)
3. Upload and start collecting data
4. Select "John Smith" in app to view

### Use Case 2: Multiple Patients (Real Data)
1. Create multiple patients in app
2. Use separate ESP32 devices, each with different `patientID`
3. Or reuse same ESP32, just update `patientID` and re-upload for each patient
4. Switch between patients in the app dropdown

### Use Case 3: Testing with Demo Patient
1. Select "John Doe (Demo)" in app
2. View synthetic test data
3. No ESP32 needed - perfect for development

### Use Case 4: Clinical Trials
1. Create patient with notes: "Trial Group A - Control"
2. Create another: "Trial Group B - Experimental"
3. Compare metrics across groups
4. Export data per patient for analysis

---

## 🚨 Troubleshooting

### Problem: "No patients found"
**Solution:**
```bash
# Initialize demo patient
python3 init_demo_patient.py

# Or restart backend
pkill -f uvicorn
cd /workspaces/blank-app
python3 -m uvicorn backend.app_main:app --host 0.0.0.0 --port 8000 &
```

### Problem: "ESP32 data not appearing"
**Checklist:**
1. ✅ ESP32 `patientID` matches patient in app
2. ✅ Backend URL is correct and reachable
3. ✅ Backend is running (`curl http://localhost:8000/api/patients`)
4. ✅ Selected correct patient in Streamlit dropdown
5. ✅ Check ESP32 Serial Monitor for errors

### Problem: "Wrong patient data showing"
**Solution:**
- Ensure correct patient is selected in sidebar dropdown
- Patient ID in ESP32 must match patient ID in app
- Check backend logs: `curl http://localhost:8000/api/readings?patient_id=1`

### Problem: "Blynk not updating"
**Solution:**
- Verify Blynk token in `backend/.env`
- Check virtual pin configuration (V0-V8)
- Test manual update: `curl -X POST http://localhost:8000/api/blynk/update?patient_id=1`

---

## 📋 Next Steps

### ✅ You've Completed:
1. Blynk datastream configuration
2. Code updates for multi-patient support

### 🔄 Remaining Tasks:
1. **Update ESP32** with correct WiFi and backend URL
2. **Set patient_id** in ESP32 code
3. **Upload to ESP32** and test
4. **Create real patients** in the app
5. **Start collecting data!**

---

## 📚 API Reference

### Patient Endpoints

#### List All Patients
```bash
GET /api/patients
Response: [
  {
    "id": 1,
    "name": "John Doe (Demo)",
    "age": 45,
    "notes": "Demo patient",
    "created_at": "2026-01-16T06:23:15"
  }
]
```

#### Create Patient
```bash
POST /api/patients
Body: {
  "name": "Jane Smith",
  "age": 28,
  "notes": "Optional notes"
}
Response: {"id": 2, ...}
```

#### Get Patient
```bash
GET /api/patients/{patient_id}
Response: {"id": 1, "name": "...", ...}
```

#### Delete Patient
```bash
DELETE /api/patients/{patient_id}
Response: {"message": "Patient and all associated data deleted"}
```

### Data Endpoints

#### Send Pressure Data
```bash
POST /api/pressure?patient_id=1
Body: {
  "device_id": "ESP32_01",
  "readings": [
    {
      "timestamp": 1234567890,
      "s1": 45.5, "s2": 30.2, ... "s10": 58.7
    }
  ]
}
```

#### Get Readings
```bash
GET /api/readings?patient_id=1&limit=100
Response: [
  {
    "timestamp": "2026-01-16T06:30:00",
    "patient_id": 1,
    "pressures": {
      "bigToe": 45.5,
      "pinkyToe": 30.2,
      ...
    }
  }
]
```

#### Update Blynk
```bash
POST /api/blynk/update?patient_id=1
Response: {"message": "Blynk updated successfully"}
```

---

## 🎉 You're All Set!

Your multi-patient pressure monitoring system is ready for production use. Each patient's data is isolated, and you can easily switch between patients in the dashboard.

**Questions?** Check the logs:
- Backend: Watch uvicorn output
- Frontend: Check Streamlit terminal
- ESP32: Monitor Serial output

Happy monitoring! 🚀
