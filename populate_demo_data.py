#!/usr/bin/env python3
"""
Populate Demo Patient with Synthetic Data

This script generates and stores realistic synthetic pressure data
for the demo patient in the database.
"""

import requests
from datetime import datetime, timedelta
from mock_data_generator import generate_mock_data
import time

# API Configuration
API_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev"
DEMO_PATIENT_ID = 1

def populate_demo_data(num_cycles=100, cadence=115, batch_size=50):
    """
    Populate demo patient with synthetic gait data
    
    Args:
        num_cycles: Number of gait cycles to generate (default: 100 = ~1 minute of walking)
        cadence: Steps per minute (default: 115)
        batch_size: Number of readings to send per API call
    """
    print("=" * 60)
    print("Demo Patient Data Population")
    print("=" * 60)
    print(f"\nGenerating {num_cycles} gait cycles at {cadence} steps/min...")
    print(f"This simulates ~{num_cycles/cadence:.1f} minutes of walking data\n")
    
    # Generate synthetic data
    df = generate_mock_data(num_cycles=num_cycles, cadence=cadence, sampling_rate=25)
    
    print(f"✓ Generated {len(df)} samples")
    print(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds():.1f} seconds")
    
    # Convert DataFrame to API format
    readings = []
    for _, row in df.iterrows():
        readings.append({
            "timestamp": int(row['timestamp'].timestamp()),
            "s1": float(row['bigtoepressure']),
            "s2": float(row['pinkytoepressure']),
            "s3": float(row['metaoutpressure']),
            "s4": float(row['metainpressure']),
            "s5": float(row['heelpressure']),
            "s6": float(row['bigtoepressure_l']),
            "s7": float(row['pinkytoepressure_l']),
            "s8": float(row['metaoutpressure_l']),
            "s9": float(row['metainpressure_l']),
            "s10": float(row['heelpressure_l']),
        })
    
    # Send data in batches
    print(f"\n📤 Sending data to API in batches of {batch_size}...")
    total_sent = 0
    
    for i in range(0, len(readings), batch_size):
        batch = readings[i:i+batch_size]
        
        payload = {
            "device_id": "DEMO_DEVICE",
            "readings": batch
        }
        
        try:
            response = requests.post(
                f"{API_URL}/api/pressure?patient_id={DEMO_PATIENT_ID}",
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                total_sent += len(batch)
                progress = (total_sent / len(readings)) * 100
                print(f"  ✓ Batch {i//batch_size + 1}: Sent {len(batch)} readings ({progress:.1f}% complete)")
            else:
                print(f"  ✗ Batch {i//batch_size + 1} failed: {response.status_code}")
                print(f"    Response: {response.text}")
        
        except Exception as e:
            print(f"  ✗ Error sending batch: {e}")
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.1)
    
    print(f"\n✅ Successfully sent {total_sent}/{len(readings)} readings to demo patient")
    
    # Trigger Blynk update with the new data
    print("\n🔄 Triggering Blynk update with new metrics...")
    try:
        response = requests.post(
            f"{API_URL}/api/blynk/update?patient_id={DEMO_PATIENT_ID}&limit=100",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ Blynk updated successfully")
            print(f"    - Data points analyzed: {result.get('data_points_analyzed', 0)}")
            print(f"    - Metrics calculated: {list(result.get('metrics', {}).keys())}")
        else:
            print(f"  ✗ Blynk update failed: {response.status_code}")
    
    except Exception as e:
        print(f"  ✗ Error updating Blynk: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Demo data population complete!")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. View data in Streamlit dashboard")
    print("  2. Check Blynk app for updated metrics")
    print("  3. Generate more data by running this script again")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    num_cycles = 100  # Default: ~1 minute of walking
    cadence = 115     # Default cadence
    
    if len(sys.argv) > 1:
        try:
            num_cycles = int(sys.argv[1])
        except ValueError:
            print("Usage: python3 populate_demo_data.py [num_cycles] [cadence]")
            print("  num_cycles: Number of gait cycles (default: 100)")
            print("  cadence: Steps per minute (default: 115)")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            cadence = int(sys.argv[2])
        except ValueError:
            print("Invalid cadence value")
            sys.exit(1)
    
    populate_demo_data(num_cycles=num_cycles, cadence=cadence)
