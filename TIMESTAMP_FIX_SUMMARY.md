# Timestamp Display Fix - Singapore Standard Time (GMT+8)

## Problem
Website timestamps were displaying in UTC instead of Singapore Standard Time (GMT+8), even after configuring the ESP32 with the correct timezone offset.

## Root Cause
The backend was parsing timestamps from the API as UTC and storing them as UTC DateTime objects. When the frontend displayed these timestamps using `.strftime()`, they were showing in UTC time instead of the user's local Singapore timezone (+8).

**Timeline:**
1. ESP32 sends epoch timestamp (timezone-independent Unix time)
2. Backend receives epoch and Pydantic converts to `datetime` object (interprets as UTC)
3. SQLAlchemy stores as DateTime column (UTC)
4. Frontend retrieves and displays (was showing UTC instead of SGT)

## Solution
Added timezone conversion to all Streamlit pages that display timestamps. All UTC datetimes are now converted to Singapore timezone (`Asia/Singapore`) before display.

## Changes Made

### 1. Added pytz dependency
- **File:** `requirements.txt`
- **Change:** Added `pytz` package for timezone handling

### 2. Updated Streamlit Dashboard Pages
Imported `pytz` and added timezone conversion to timestamp parsing in all data-loading functions:

#### Files Updated:
- `page_2.py` (Dashboard)
- `page_3.py` (Advanced Gait Analysis)
- `page_4.py` (Data Exploration)
- `page_6.py` (Action Plan Generator)
- `patient_utils.py` (Helper utilities)
- `test_api.py` (API testing)

#### Change Pattern:
```python
# Before
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
df = df.dropna(subset=["timestamp"])

# After
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
df = df.dropna(subset=["timestamp"])
# Convert UTC to Singapore timezone (GMT+8)
df["timestamp"] = df["timestamp"].dt.tz_convert('Asia/Singapore')
```

## Verification
All 6 data-loading functions now convert UTC to Singapore timezone:
- ✅ page_2.py load_data_from_api()
- ✅ page_3.py load_data_from_api()
- ✅ page_4.py load_data_from_api()
- ✅ page_6.py load_data_from_api()
- ✅ patient_utils.py load_patient_data()
- ✅ test_api.py fetch_df()

## Testing
1. Run Streamlit dashboard: `streamlit run streamlit_app.py`
2. Navigate to any page that displays timestamps (page_2, page_3, page_4, page_6)
3. Timestamps should now display in SGT (GMT+8) instead of UTC
4. Time should match local Singapore time

## Expected Behavior
- If it's 11:00 AM SGT, the dashboard should display 11:00 AM (not 3:00 AM)
- All timestamps across all pages will show consistent local time in Singapore timezone
- Timestamps retrieved from the database will correctly reflect SGT even though they're stored as UTC

## Additional Notes
- The ESP32 timezone configuration remains unchanged: `TIMEZONE_OFFSET = 28800` (UTC+8)
- The database continues to store epoch timestamps (which are timezone-independent)
- The conversion happens at display time in the frontend, not at storage time
- This approach is clean, maintainable, and doesn't require database migration
