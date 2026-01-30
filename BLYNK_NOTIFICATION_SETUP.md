# Blynk Button Notification Setup Guide

This guide explains how to set up the Blynk button to send gait evaluation notifications through your backend.

## ✅ SOLUTION: Using Virtual Pin V9 Instead of /notify

**The Issue:** Blynk's `/notify` endpoint requires email configuration and returns 404 errors.

**The Solution:** We now use **virtual pin V9** to display notifications directly in your Blynk app with a Text widget.

---

## Current Implementation

The backend webhook endpoint `/api/blynk/webhook/button` receives button press/release events from Blynk and automatically:

1. **Detects button press** (v10 = 1)
2. **Fetches latest patient gait metrics** from database
3. **Calculates automatic evaluation status** (GOOD/NEEDS_ATTENTION/CRITICAL)
4. **Sends formatted evaluation report** to Blynk via virtual pin V9
5. **Displays notification** in Blynk app Text widget

---

## Blynk App Setup

### Step 1: Create Button Widget

1. Open your Blynk app
2. Tap pencil icon to edit your project
3. Tap **+** to add a new widget
4. Select **Button**
5. Configure:
   - **PIN**: V10
   - **Name**: "Send Evaluation"
   - **Mode**: Push

### Step 2: Create Text Widget for Notifications

1. Tap **+** to add another widget
2. Select **Text**
3. Configure:
   - **PIN**: V9
   - **Name**: "Evaluation Status"
   - **Read-only**: Yes (important!)

### Step 3: Set Up Webhook

Log into https://blynk.cloud and create a webhook:

1. Go to **Webhooks** section
2. Create new webhook:
   - **Trigger**: V10 = 1
   - **URL**: http://<your-ip>:8000/api/blynk/webhook/button
   - **Method**: GET
   - **Parameters**: v10=1&patient_id=3

---

## How It Works

```
Button pressed in Blynk app (V10)
           ↓
Webhook triggers backend endpoint
           ↓
Backend fetches gait metrics for patient
           ↓
Backend calculates status automatically
           ↓
Backend updates V9 Text widget with evaluation
           ↓
Notification appears in Blynk app
```

---

## Testing

### Test 1: Manual Test with curl

```bash
curl "http://localhost:8000/api/blynk/webhook/button?v10=1&patient_id=3"
```

Expected response:
```json
{
  "success": true,
  "message": "Notification sent via V9: Evaluation Report",
  "button_state": 1,
  "patient_id": 3,
  "evaluation": {
    "status": "GOOD",
    "cadence": 95.5,
    "step_symmetry": 92.3,
    "stance_time": 0.65
  }
}
```

### Test 2: Verify in Blynk App

1. Open Blynk app
2. Press "Send Evaluation" button
3. Check V9 Text widget for notification

---

## Status Values

The backend automatically calculates:

- **GOOD** ✅ - All metrics normal
- **NEEDS_ATTENTION** ⚠️ - Some metrics off
- **CRITICAL** 🔴 - Multiple problems or missing data

---

## API Reference

### Endpoint

**GET /api/blynk/webhook/button**

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| v10 | int | Yes | Button state (1=press, 0=release) |
| patient_id | int | No | Patient ID (default: 1) |

### Response

```json
{
  "success": boolean,
  "message": "string",
  "button_state": 0 or 1,
  "patient_id": integer,
  "evaluation": {
    "status": "GOOD|NEEDS_ATTENTION|CRITICAL",
    "cadence": float,
    "step_symmetry": float,
    "stance_time": float
  }
}
```

---

## Troubleshooting

### Nothing happens when I press the button

**Solution 1:** Verify webhook is configured
- Log into blynk.cloud
- Check Webhooks section
- Confirm URL is correct

**Solution 2:** Test backend manually
```bash
curl "http://localhost:8000/api/blynk/webhook/button?v10=1&patient_id=3"
```

**Solution 3:** Check Text widget exists
- In Blynk app, verify V9 has a Text widget
- Make sure it's set to read-only

### Backend returns error

**404 error:** Patient doesn't exist in database
- Check patient_id is correct
- Verify database has patient data

**Timeout error:** Backend not running
```bash
# Check status
curl http://localhost:8000/docs

# Restart if needed
pkill -f uvicorn
cd /workspaces/blank-app/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

---

## Virtual Pins

| Pin | Purpose | Widget |
|-----|---------|--------|
| V9 | Notification Display | Text (Read-only) |
| V10 | Button (Trigger) | Button |

---

## Next Steps

1. Add Button widget to V10 in Blynk app
2. Add Text widget to V9 in Blynk app
3. Set up webhook in Blynk Console
4. Test with curl command
5. Press button in app and verify notification appears

For more: https://blynk.io/
