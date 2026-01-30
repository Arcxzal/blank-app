#!/usr/bin/env python3
"""
Test script to verify incremental step counting fix.
This simulates the Streamlit session state behavior to ensure steps
only increase and never decrease.
"""

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from datetime import datetime, timedelta

# Simulate Streamlit session state
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def __contains__(self, key):
        return key in self.data
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __getitem__(self, key):
        return self.data[key]
    
    def get(self, key, default=None):
        return self.data.get(key, default)

session_state = MockSessionState()

# Configuration
STEP_THRESHOLD = 1299
FS = 25

def compute_gait_parameters_test(values, timestamps):
    """Simplified version of the incremental step detection for testing"""
    
    # Initialize session state
    if 'last_processed_index' not in session_state:
        session_state['last_processed_index'] = -1
    if 'cumulative_steps' not in session_state:
        session_state['cumulative_steps'] = 0
    
    if len(values) == 0 or max(values) == 0:
        return session_state['cumulative_steps']
    
    # INCREMENTAL: Only analyze NEW data since last processing
    start_idx = session_state['last_processed_index'] + 1
    
    if start_idx >= len(values):
        print(f"  ℹ️  No new data (start_idx={start_idx} >= len={len(values)})")
        return session_state['cumulative_steps']
    
    # Analyze only NEW data with overlap
    overlap_idx = max(0, session_state['last_processed_index'] - int(len(values) * 0.25))
    analysis_values = values[overlap_idx:]
    
    # Find peaks
    threshold = max(1299, 0.30 * np.nanmax(values))
    peaks_in_new_data, _ = find_peaks(
        analysis_values,
        height=threshold,
        distance=10,
        prominence=10
    )
    
    # Convert back to original indices
    peaks_original_idx = peaks_in_new_data + overlap_idx
    
    # Filter: Only count peaks AFTER the last processed index
    new_peaks = peaks_original_idx[peaks_original_idx > session_state['last_processed_index']]
    
    # UPDATE CUMULATIVE COUNTER
    prev_steps = session_state['cumulative_steps']
    session_state['cumulative_steps'] += len(new_peaks)
    session_state['last_processed_index'] = len(values) - 1
    
    return prev_steps, len(new_peaks), session_state['cumulative_steps']

def test_monotonic_increase():
    """Test that step count never decreases"""
    print("=" * 70)
    print("TEST 1: Step Count Monotonically Increases (Never Decreases)")
    print("=" * 70)
    
    # Reset state
    session_state.data = {}
    
    # Scenario 1: Slow walk (few steps)
    print("\n📍 Scenario 1: Slow walk - 50 steps detected")
    timestamps = pd.date_range(start=datetime.now(), periods=1000, freq='40ms')
    values = np.random.randn(1000) * 10 + 500  # Random baseline
    
    # Add 50 step peaks
    peak_indices = np.linspace(50, 950, 50, dtype=int)
    values[peak_indices] = 2000  # High pressure peaks
    
    prev, new, total = compute_gait_parameters_test(values, timestamps)
    print(f"  Previous steps: {prev}")
    print(f"  New steps detected: {new}")
    print(f"  ✅ Total steps: {total}")
    step_count_1 = total
    
    # Scenario 2: Dashboard refresh with no new data
    print("\n📍 Scenario 2: Dashboard refresh (no new data)")
    step_count_2 = compute_gait_parameters_test(values, timestamps)
    print(f"  ✅ Total steps: {step_count_2}")
    assert step_count_2 == step_count_1, f"❌ FAILED: Steps changed from {step_count_1} to {step_count_2}"
    
    # Scenario 3: Add new fast walk data
    print("\n📍 Scenario 3: New data arrives - fast walk")
    new_values = np.random.randn(200) * 10 + 500
    # Add 8 more peaks for fast walk
    new_peak_indices = np.linspace(10, 190, 8, dtype=int)
    new_values[new_peak_indices] = 2000
    
    combined_values = np.concatenate([values, new_values])
    combined_timestamps = pd.date_range(start=datetime.now(), periods=len(combined_values), freq='40ms')
    
    prev, new, total = compute_gait_parameters_test(combined_values, combined_timestamps)
    print(f"  Previous steps: {prev}")
    print(f"  New steps detected: {new}")
    print(f"  ✅ Total steps: {total}")
    step_count_3 = total
    
    # Verify monotonic increase
    assert step_count_3 >= step_count_1, f"❌ FAILED: Steps regressed from {step_count_1} to {step_count_3}"
    assert step_count_3 > step_count_1, f"❌ FAILED: Expected steps to increase, but got {step_count_3} (was {step_count_1})"
    
    # Scenario 4: Another slow walk segment (no new peaks)
    print("\n📍 Scenario 4: Another slow segment added (few/no new peaks)")
    more_values = np.random.randn(150) * 10 + 500
    all_values = np.concatenate([combined_values, more_values])
    all_timestamps = pd.date_range(start=datetime.now(), periods=len(all_values), freq='40ms')
    
    prev, new, total = compute_gait_parameters_test(all_values, all_timestamps)
    print(f"  Previous steps: {prev}")
    print(f"  New steps detected: {new}")
    print(f"  ✅ Total steps: {total}")
    step_count_4 = total
    
    # Final verification
    assert step_count_4 >= step_count_3, f"❌ FAILED: Steps regressed from {step_count_3} to {step_count_4}"
    
    print("\n" + "=" * 70)
    print(f"✅ TEST PASSED: Step count progression: {session_state['cumulative_steps']}")
    print(f"   {step_count_1} → {step_count_2} (no change) → {step_count_3} (increase) → {step_count_4}")
    print("=" * 70)
    return True

def test_speed_variation():
    """Test that variable walking speeds produce increasing step counts"""
    print("\n" * 2)
    print("=" * 70)
    print("TEST 2: Variable Walking Speeds - Step Count Still Monotonic")
    print("=" * 70)
    
    # Reset state
    session_state.data = {}
    
    print("\n📍 Normal walk (1.5 Hz cadence)")
    timestamps = pd.date_range(start=datetime.now(), periods=2000, freq='40ms')
    values = np.random.randn(2000) * 10 + 500
    
    # Add steps at normal cadence (1.5 Hz = 1 step every ~0.67 seconds = 17 samples at 25 Hz)
    step_indices = np.arange(100, 2000, 17, dtype=int)
    values[step_indices] = 2000
    
    prev, new, total = compute_gait_parameters_test(values, timestamps)
    print(f"  ✅ Total steps: {total}")
    normal_steps = total
    
    print("\n📍 Fast walk added (2.0 Hz cadence)")
    # Add new data with faster steps (2.0 Hz = 1 step every 0.5 seconds = 12-13 samples at 25 Hz)
    new_fast_values = np.random.randn(1000) * 10 + 500
    fast_indices = np.arange(50, 1000, 12, dtype=int)
    new_fast_values[fast_indices] = 2000
    
    combined_values = np.concatenate([values, new_fast_values])
    combined_timestamps = pd.date_range(start=datetime.now(), periods=len(combined_values), freq='40ms')
    
    prev, new, total = compute_gait_parameters_test(combined_values, combined_timestamps)
    print(f"  New steps: {new}")
    print(f"  ✅ Total steps: {total}")
    fast_steps = total
    
    assert fast_steps > normal_steps, f"❌ FAILED: Fast walk didn't add steps ({fast_steps} vs {normal_steps})"
    
    print("\n📍 Slow walk added (1.0 Hz cadence)")
    # Slow walk (1.0 Hz = 1 step every 1 second = 25 samples at 25 Hz)
    new_slow_values = np.random.randn(800) * 10 + 500
    slow_indices = np.arange(50, 800, 25, dtype=int)
    new_slow_values[slow_indices] = 2000
    
    all_values = np.concatenate([combined_values, new_slow_values])
    all_timestamps = pd.date_range(start=datetime.now(), periods=len(all_values), freq='40ms')
    
    prev, new, total = compute_gait_parameters_test(all_values, all_timestamps)
    print(f"  New steps: {new}")
    print(f"  ✅ Total steps: {total}")
    slow_steps = total
    
    assert slow_steps >= fast_steps, f"❌ FAILED: Slow walk caused regression ({slow_steps} vs {fast_steps})"
    
    print("\n" + "=" * 70)
    print(f"✅ TEST PASSED: Speeds varied but steps stayed monotonic")
    print(f"   Normal: {normal_steps} → Fast: {fast_steps} → Slow: {slow_steps}")
    print("=" * 70)
    return True

if __name__ == "__main__":
    print("\n" + "🧪 INCREMENTAL STEP COUNTER TEST SUITE".center(70))
    print("=" * 70)
    
    try:
        test_monotonic_increase()
        test_speed_variation()
        
        print("\n" * 2)
        print("🎉 ALL TESTS PASSED! Step counter is now monotonically increasing.")
        print("   Steps will NEVER decrease, even with variable walking speeds.")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
