# Zero Data & Data Persistence Fix

## Overview
This document describes two critical fixes applied to resolve issues with excessive zero data being sent and old data being replaced on the dashboard when standing still.

---

## Issue 1: Excessive Zero Data Being Sent

### Problem
When the patient stops walking and stands still:
- ESP32 sensors read 0 (no pressure)
- These all-zero samples were being packaged and sent to the backend
- Backend stores this useless data, cluttering the database
- Dashboard metrics get skewed by zero readings

### Root Cause
The dual-buffer architecture was working well to prevent data loss during sending, but it was sending **every** buffer, including batches with all zeros.

### Solution: Zero-Data Filter on ESP32

Added logic to both `esp32_left_foot.ino` and `esp32_right_foot.ino` in the `initiateAsyncSend()` function:

```cpp
// Check if buffer contains meaningful data (not all zeros)
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
```

### Benefits
✅ **Reduced network traffic** - Only meaningful data is sent  
✅ **Cleaner database** - No useless all-zero readings stored  
✅ **Better metrics** - Action plan generation works with real data only  
✅ **Silent degradation** - System gracefully handles idle periods  

### Serial Output
When standing still:
```
Buffer contains only zeros - skipping send (standing still)
```

---

## Issue 2: Data Replacement When Standing Still

### Problem
When the patient stands still or takes a break:
- Dashboard cache refreshes every 2 seconds with `@st.cache_data(ttl=2)`
- If no new data comes in (because of zero-filter), only old data gets cached
- On rerun, old data is shown but nothing new accumulates
- Steps and action plans can't be generated from incomplete data
- When patient resumes walking, old data might be missing

### Root Cause
Streamlit's `@st.cache_data(ttl=2)` returns empty if the API returns only zeros or old data. Without session state persistence, there's no memory of historical data across reruns.

### Solution: Session State-Based Data Accumulation

Added three new functions to `page_2.py`:

#### 1. Initialize Session State
```python
def initialize_session_state():
    """Initialize session state for data persistence across reruns"""
    if 'accumulated_data' not in st.session_state:
        st.session_state.accumulated_data = pd.DataFrame()
    if 'last_api_timestamp' not in st.session_state:
        st.session_state.last_api_timestamp = None
```

#### 2. Merge New Data with History
```python
def merge_new_data_with_history() -> pd.DataFrame:
    """
    Merge fresh API data with historical data stored in session state.
    This prevents old data from being replaced when the patient is standing still.
    
    Returns the accumulated dataset with duplicates removed.
    """
    initialize_session_state()
    
    # Get fresh data from API
    try:
        fresh_data = load_data_from_api()
    except Exception:
        fresh_data = pd.DataFrame()
    
    # If no fresh data, return accumulated data
    if fresh_data.empty:
        return st.session_state.accumulated_data.copy() if not st.session_state.accumulated_data.empty else pd.DataFrame()
    
    # Combine fresh data with accumulated data
    if st.session_state.accumulated_data.empty:
        combined = fresh_data.copy()
    else:
        combined = pd.concat([st.session_state.accumulated_data, fresh_data], ignore_index=True)
    
    # Remove duplicates based on timestamp (keep first occurrence)
    combined = combined.drop_duplicates(subset=['timestamp'], keep='first')
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    
    # Store back in session state for next rerun
    st.session_state.accumulated_data = combined.copy()
    
    return combined
```

#### 3. Updated Main Data Loading
Changed the main page's data loading to use `merge_new_data_with_history()` instead of `load_patient_data()`:

```python
try:
    # Use patient data loading which includes API calls with data merging
    df = merge_new_data_with_history()
    st.write(f"📊 Data loaded: {len(df)} samples (accumulated)")
    if not df.empty:
        st.write(f"📅 Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
except Exception as e:
    st.error(f"Error loading data: {e}")
```

### How It Works
1. **On first load:** Fresh API data is stored in session state
2. **During idle period:** Session state preserves old data (no loss)
3. **When new data arrives:** New data is merged with accumulated history
4. **Duplicates removed:** Same timestamp entries are deduplicated
5. **Persistent memory:** Each rerun grows the dataset, never shrinks

### Benefits
✅ **No data loss during idle periods** - Historical data preserved  
✅ **Continuous accumulation** - Data grows as patient moves  
✅ **Accurate action plans** - All past walking sessions are included  
✅ **Real-time updates** - New data merged immediately when available  
✅ **Graceful degradation** - Works with or without fresh API data  

### Session State Lifecycle
```
Dashboard Open → Initialize Session State
                      ↓
Patient Walking → Fresh data merged with history
                      ↓
Standing Still → Session state preserves old data
                      ↓
Resume Walking → New data merged with accumulated history
                      ↓
Dashboard Close → Session state discarded (fresh start next time)
```

---

## Testing Recommendations

### Test Zero-Filter (ESP32)
1. Upload firmware to ESP32
2. Walk and collect data (should send normally)
3. Stop and stand still for 10+ seconds
4. Watch serial output:
   ```
   ✓ Normal walking data sent
   "Buffer contains only zeros - skipping send (standing still)"
   ✓ Resume walking data sent
   ```

### Test Data Persistence (Dashboard)
1. Open dashboard and walk for 30 seconds (collect data)
2. Stop and stand still for 1 minute
3. Watch metrics: ✅ Should NOT reset
4. Check data displayed: ✅ Should show all walking data
5. Resume walking: ✅ New data added to existing history
6. Refresh browser: ⚠️ Session state resets (expected behavior)

---

## Configuration

### Zero-Filter Threshold
To adjust sensitivity (e.g., filter out readings < 10):
```cpp
// In ESP32 code, modify the check:
if (s1_buf[i] > 10 || s2_buf[i] > 10 || ...)  // Now filters out noise too
```

### Data Accumulation Window
To clear session data after idle period:
```python
# In page_2.py, add time-based clearing:
import time
if time.time() - st.session_state.last_update > 3600:  # 1 hour
    st.session_state.accumulated_data = pd.DataFrame()
```

---

## Files Modified

### ESP32 Files
- `/workspaces/blank-app/esp32_left_foot.ino` - Added zero-filter logic
- `/workspaces/blank-app/esp32_right_foot.ino` - Added zero-filter logic

### Dashboard Files
- `/workspaces/blank-app/page_2.py` - Added data persistence with session state

---

## Summary

| Issue | Solution | Result |
|-------|----------|--------|
| Excessive 0s sent | ESP32 filters all-zero buffers | ✅ Cleaner data storage |
| Old data replaced | Session state accumulates history | ✅ Persistent data across reruns |
| Skewed metrics | Zero-filter on ESP32 | ✅ Accurate gait analysis |
| Lost action plans | Data accumulation | ✅ Complete walking history |

Both fixes work together to provide a robust, persistent gait analysis system that handles idle periods gracefully.
