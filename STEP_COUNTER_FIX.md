# Step Counter Regression Fix

## Problem
Step count was **regressing** (going DOWN) instead of monotonically increasing. This happened when:
1. Walking at varying speeds (fast/slow)
2. Streamlit dashboard rerunning due to auto-refresh
3. New sensor data arriving

## Root Cause
The step detection algorithm was being called on the **entire dataset** each time the page reran. Since peak detection can have slight variations due to:
- Data window shifts (new data at edges)
- Signal changes (edge effects from filtering)
- Different peak detection results with 0.3s minimum distance + unfiltered noise

This caused the **total step count to be recalculated from scratch**, which could return a different (lower) value than the previous run.

**Example of the bug:**
```
Walk slow: steps = 45
Walk fast: steps = 52 (jumped up - detected more peaks)
Walk slow again: steps = 48 (went DOWN - detected fewer peaks - ERROR!)
```

## Solution: Incremental Step Counting

Implemented **persistent step counter** using Streamlit's `session_state`:

### Key Changes to `page_2.py`:

1. **Initialize session state variables** at start of `compute_gait_parameters()`:
   ```python
   if 'last_processed_index' not in st.session_state:
       st.session_state.last_processed_index = -1
   if 'cumulative_steps' not in st.session_state:
       st.session_state.cumulative_steps = 0
   ```

2. **Only analyze NEW data since last processing**:
   ```python
   start_idx = st.session_state.last_processed_index + 1
   
   if start_idx >= len(values):
       # No new data, return previous count
       return compute_existing_gait_metrics(df, st.session_state.cumulative_steps)
   ```

3. **Only count peaks AFTER the last processed index**:
   ```python
   new_peaks = peaks_original_idx[peaks_original_idx > st.session_state.last_processed_index]
   ```

4. **Increment (never recalculate) the step counter**:
   ```python
   st.session_state.cumulative_steps += len(new_peaks)
   st.session_state.last_processed_index = len(values) - 1
   ```

5. **Always return cumulative count**:
   ```python
   return {
       "steps": st.session_state.cumulative_steps,  # Never decreases
       ...
   }
   ```

### New Helper Function: `compute_existing_gait_metrics()`

Computes timing metrics (cadence, stride time, etc.) from the dataframe without recalculating steps:
- Estimates cadence from total duration and cumulative step count
- Calculates average step/stride times from total data
- Preserves step counter integrity

## Result

✅ **Step count is now monotonically increasing** - It only goes UP or stays the same, never goes DOWN.

### How It Works:

1. **Session 1:** User walks 50 steps
   - `cumulative_steps = 50`
   - `last_processed_index = 500` (all data processed)
   
2. **Dashboard refresh** with new data (501-525 samples):
   - Only analyzes samples 501-525
   - Detects 3 new peaks
   - `cumulative_steps = 50 + 3 = 53`
   
3. **Another refresh** (no new data):
   - `start_idx = 526 > len(data)` 
   - Returns existing metrics with `cumulative_steps = 53`
   - No recalculation, no regression

4. **Fast walk adds new data** (526-600):
   - Analyzes new samples only
   - Detects 8 new peaks
   - `cumulative_steps = 53 + 8 = 61`
   - ✅ Still only increased, never went down

## Testing

To verify the fix works:

1. **Walk slowly** - note step count (e.g., 45 steps)
2. **Walk faster** - step count increases (e.g., 52 steps)
3. **Walk slowly again** - step count continues to increase (e.g., 60 steps minimum)
4. **Key check:** Step count **never decreases**, even after speed changes

## Technical Details

- **Session State Scope:** Per-browser, persists across Streamlit reruns
- **Processing Overlap:** Uses 25% overlap from previous data for better peak detection at boundaries
- **Threshold:** 30% of max total load (~1299 ADC)
- **Minimum Distance:** 0.3s (10 samples at 25 Hz) - allows up to 200 bpm cadence
- **Sampling Frequency:** 25 Hz
- **Timezone:** GMT+8 (Singapore)

## Files Modified

- `/workspaces/blank-app/page_2.py`
  - Added `compute_existing_gait_metrics()` function (lines 326-390)
  - Refactored `compute_gait_parameters()` to use incremental counting (lines 393-510)
  - Session state initialization and cumulative step tracking
  - Debug output to monitor step detection

## Backwards Compatibility

✅ This fix is backwards compatible:
- Existing code still calls `compute_gait_parameters()` the same way
- Return dictionary format unchanged
- No changes to API endpoints or data structures
- Session state is initialized automatically on first run
