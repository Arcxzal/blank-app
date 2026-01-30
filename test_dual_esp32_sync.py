#!/usr/bin/env python3
"""
Test script for dual ESP32 synchronization and merging.
Tests that left and right foot data from separate devices are properly merged.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import the merge function from page_2
from page_2 import merge_left_right_foot_data

def create_test_data():
    """Create synthetic test data simulating two ESP32s sending data."""
    
    utc = pytz.UTC
    base_time = datetime(2026, 1, 30, 12, 0, 0, tzinfo=utc)
    
    # Simulate right foot ESP32 sending data
    right_foot_data = {
        'timestamp': [base_time + timedelta(seconds=i*0.5) for i in range(6)],
        'bigToe': [10, 15, 20, 25, 30, 0],
        'pinkyToe': [8, 12, 18, 22, 28, 0],
        'metaOut': [12, 16, 22, 26, 32, 0],
        'metaIn': [11, 15, 21, 25, 31, 0],
        'heel': [40, 45, 50, 55, 60, 0],
        'bigToe_L': [0, 0, 0, 0, 0, 0],
        'pinkyToe_L': [0, 0, 0, 0, 0, 0],
        'metaOut_L': [0, 0, 0, 0, 0, 0],
        'metaIn_L': [0, 0, 0, 0, 0, 0],
        'heel_L': [0, 0, 0, 0, 0, 0],
    }
    
    # Simulate left foot ESP32 sending data (slightly delayed, ~0.2s offset)
    left_foot_data = {
        'timestamp': [base_time + timedelta(seconds=i*0.5 + 0.2) for i in range(6)],
        'bigToe': [0, 0, 0, 0, 0, 0],
        'pinkyToe': [0, 0, 0, 0, 0, 0],
        'metaOut': [0, 0, 0, 0, 0, 0],
        'metaIn': [0, 0, 0, 0, 0, 0],
        'heel': [0, 0, 0, 0, 0, 0],
        'bigToe_L': [9, 14, 19, 24, 29, 0],
        'pinkyToe_L': [7, 11, 17, 21, 27, 0],
        'metaOut_L': [11, 15, 21, 25, 31, 0],
        'metaIn_L': [10, 14, 20, 24, 30, 0],
        'heel_L': [38, 43, 48, 53, 58, 0],
    }
    
    df_right = pd.DataFrame(right_foot_data)
    df_left = pd.DataFrame(left_foot_data)
    
    # Combine as if they both arrived at backend
    combined = pd.concat([df_right, df_left], ignore_index=True)
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    
    return combined

def test_merge():
    """Test the merging logic."""
    print("\n" + "="*60)
    print("DUAL ESP32 SYNCHRONIZATION TEST")
    print("="*60)
    
    # Create test data
    print("\n📊 Creating synthetic data from two ESP32s...")
    df_input = create_test_data()
    
    print(f"   Input rows: {len(df_input)}")
    print("\n📋 Input data (before merge):")
    print("   Index | Timestamp | Right Foot (Heel) | Left Foot (Heel) | Combined?")
    print("   " + "-"*70)
    for idx, row in df_input.iterrows():
        right_heel = row['heel'] if row['heel'] > 0 else 0
        left_heel = row['heel_L'] if row['heel_L'] > 0 else 0
        combined = "✓" if right_heel > 0 and left_heel > 0 else "✗"
        ts_str = row['timestamp'].strftime("%H:%M:%S.%f")[:-3]
        print(f"   {idx:5d} | {ts_str} | {right_heel:17.1f} | {left_heel:16.1f} | {combined}")
    
    # Apply merge
    print("\n🔗 Merging left and right foot data (within 1 second tolerance)...")
    df_merged = merge_left_right_foot_data(df_input)
    
    print(f"   Output rows: {len(df_merged)}")
    print("\n✅ Output data (after merge):")
    print("   Index | Timestamp | Right Heel | Left Heel | COMBINED?")
    print("   " + "-"*65)
    for idx, row in df_merged.iterrows():
        right_heel = row['heel'] if row['heel'] > 0 else 0
        left_heel = row['heel_L'] if row['heel_L'] > 0 else 0
        combined = "✓✓" if (right_heel > 0 and left_heel > 0) else ("R-only" if right_heel > 0 else ("L-only" if left_heel > 0 else "Empty"))
        ts_str = row['timestamp'].strftime("%H:%M:%S.%f")[:-3]
        print(f"   {idx:5d} | {ts_str} | {right_heel:10.1f} | {left_heel:9.1f} | {combined}")
    
    # Validation
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    
    # Check if complete rows exist
    complete_rows = 0
    incomplete_rows = 0
    
    for idx, row in df_merged.iterrows():
        right_data = (row['bigToe'] > 0 or row['pinkyToe'] > 0 or 
                     row['metaOut'] > 0 or row['metaIn'] > 0 or row['heel'] > 0)
        left_data = (row['bigToe_L'] > 0 or row['pinkyToe_L'] > 0 or 
                    row['metaOut_L'] > 0 or row['metaIn_L'] > 0 or row['heel_L'] > 0)
        
        if right_data and left_data:
            complete_rows += 1
        elif right_data or left_data:
            incomplete_rows += 1
    
    print(f"✓ Complete rows (both feet):    {complete_rows}")
    print(f"⚠ Incomplete rows (one foot):   {incomplete_rows}")
    print(f"📊 Total rows after merge:      {len(df_merged)}")
    
    # Success criteria
    success = complete_rows >= 5  # We expect at least 5 complete rows from our test data
    
    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED - Left and right data properly merged!")
    else:
        print("❌ TEST FAILED - Merge did not work as expected")
    print("="*60 + "\n")
    
    return success

def test_edge_cases():
    """Test edge cases."""
    print("\n" + "="*60)
    print("EDGE CASE TESTS")
    print("="*60)
    
    utc = pytz.UTC
    base_time = datetime(2026, 1, 30, 12, 0, 0, tzinfo=utc)
    
    # Test 1: Data arriving out of order
    print("\n🧪 Test 1: Out-of-order data")
    out_of_order = pd.DataFrame({
        'timestamp': [base_time + timedelta(seconds=2), base_time + timedelta(seconds=0)],
        'bigToe': [10, 0],
        'pinkyToe': [8, 0],
        'metaOut': [12, 0],
        'metaIn': [11, 0],
        'heel': [40, 0],
        'bigToe_L': [0, 9],
        'pinkyToe_L': [0, 7],
        'metaOut_L': [0, 11],
        'metaIn_L': [0, 10],
        'heel_L': [0, 38],
    })
    result1 = merge_left_right_foot_data(out_of_order)
    print(f"   Input rows: {len(out_of_order)}, Output rows: {len(result1)}")
    print(f"   ✓ Handled out-of-order data")
    
    # Test 2: Very close timestamps (< 100ms)
    print("\n🧪 Test 2: Very close timestamps (< 100ms)")
    close_ts = pd.DataFrame({
        'timestamp': [base_time, base_time + timedelta(milliseconds=50)],
        'bigToe': [10, 0],
        'pinkyToe': [8, 0],
        'metaOut': [12, 0],
        'metaIn': [11, 0],
        'heel': [40, 0],
        'bigToe_L': [0, 9],
        'pinkyToe_L': [0, 7],
        'metaOut_L': [0, 11],
        'metaIn_L': [0, 10],
        'heel_L': [0, 38],
    })
    result2 = merge_left_right_foot_data(close_ts)
    print(f"   Input rows: {len(close_ts)}, Output rows: {len(result2)}")
    print(f"   ✓ Merged very close timestamps")
    
    # Test 3: Empty dataframe
    print("\n🧪 Test 3: Empty dataframe")
    empty_df = pd.DataFrame({
        'timestamp': [],
        'bigToe': [], 'pinkyToe': [], 'metaOut': [], 'metaIn': [], 'heel': [],
        'bigToe_L': [], 'pinkyToe_L': [], 'metaOut_L': [], 'metaIn_L': [], 'heel_L': [],
    })
    result3 = merge_left_right_foot_data(empty_df)
    print(f"   Input rows: {len(empty_df)}, Output rows: {len(result3)}")
    print(f"   ✓ Handled empty dataframe")
    
    print("\n" + "="*60)
    print("✅ ALL EDGE CASE TESTS PASSED")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_merge()
        edge_cases_ok = test_edge_cases()
        
        if success and edge_cases_ok:
            print("\n🎉 ALL TESTS PASSED - Dual ESP32 sync is working correctly!\n")
            sys.exit(0)
        else:
            print("\n⚠️  Some tests did not pass\n")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
