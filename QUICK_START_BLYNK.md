# Quick Reference: Blynk Button Notifications

## TL;DR Setup

### Blynk App (3 Steps)
1. Add **Button** widget → Set PIN to **V10**
2. Add **Text** widget → Set PIN to **V9** → Mark as **read-only**
3. Edit webhook in Blynk Console:
   - Trigger: `V10 = 1`
   - URL: `http://<your-ip>:8000/api/blynk/webhook/button?v10=1&patient_id=3`

### Test It
```bash
curl "http://localhost:8000/api/blynk/webhook/button?v10=1&patient_id=3"
```

Should return:
```json
{"success": true, "message": "Notification sent via V9: Evaluation Report", ...}
```

And notification should appear in V9 Text widget in your Blynk app.

---

## What Changed

**OLD (Broken):**
- Used Blynk's `/notify` endpoint
- Required email config
- Returned HTTP 404 errors
- Unreliable

**NEW (Working):**
- Uses virtual pin V9 (Text widget)
- No config needed
- Works reliably
- Notifications appear instantly in app

---

## Virtual Pins

| Pin | Type | Purpose |
|-----|------|---------|
| V9 | Output (Text) | Notification display |
| V10 | Input (Button) | Trigger button |

---

## Webhook Endpoint

**GET** `/api/blynk/webhook/button`

**Parameters:**
- `v10` = 1 (button press) or 0 (release)
- `patient_id` = patient ID

**Response Example:**
```json
{
  "success": true,
  "message": "Evaluation report sent to Blynk (V9)",
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

---

## Status Meanings

- **GOOD** ✅ - All metrics normal
- **NEEDS_ATTENTION** ⚠️ - Some metrics off  
- **CRITICAL** 🔴 - Multiple issues

---

## Backend File Locations

- API Endpoint: `/workspaces/blank-app/backend/app_main.py`
- Notification Logic: `/workspaces/blank-app/backend/blynk_http_service.py`
- Auth Token: Line 20 in `blynk_http_service.py`

---

## Debug

**Backend running?**
```bash
curl http://localhost:8000/docs
```

**Can reach Blynk?**
```bash
curl https://blynk.cloud
```

**Endpoint working?**
```bash
curl "http://localhost:8000/api/blynk/webhook/button?v10=1&patient_id=3"
```

---

## Files to Review

1. **Setup Guide**: `BLYNK_NOTIFICATION_SETUP.md`
2. **Technical Details**: `BLYNK_SOLUTION_SUMMARY.md`
3. **Backend Code**: `backend/blynk_http_service.py` (lines 246-283)
4. **API Endpoint**: `backend/app_main.py` - search for `/api/blynk/webhook/button`

---

## One-Line Quick Start

```bash
# Test if everything works
curl "http://localhost:8000/api/blynk/webhook/button?v10=1&patient_id=3" && echo "✅ Backend working!"
```

If you see `"success": true` → Backend is ready. Next: Set up webhook in Blynk Console.

---

## Support

- See `BLYNK_NOTIFICATION_SETUP.md` for full setup instructions
- See `BLYNK_SOLUTION_SUMMARY.md` for technical details
- Check backend logs for error messages
- Verify patient exists: Patient ID 3 (Joseph) is available in test database
