#!/usr/bin/env python3
"""
Test script for Blynk integration
Run this to verify the Blynk connection and data transmission
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.blynk_service import BlynkService

def generate_test_data():
    """Generate mock pressure data for testing"""
    start_time = datetime.now() - timedelta(seconds=60)
    timestamps = [start_time + timedelta(seconds=i*0.04) for i in range(1500)]  # 60 seconds at 25Hz
    
    data = {
        'timestamp': timestamps,
        'bigToe': np.abs(np.sin(np.linspace(0, 30, len(timestamps))) * 40 + np.random.randn(len(timestamps)) * 3),
        'pinkyToe': np.abs(np.sin(np.linspace(0, 25, len(timestamps))) * 35 + np.random.randn(len(timestamps)) * 3),
        'metaOut': np.abs(np.sin(np.linspace(0, 28, len(timestamps))) * 38 + np.random.randn(len(timestamps)) * 3),
        'metaIn': np.abs(np.sin(np.linspace(0, 26, len(timestamps))) * 36 + np.random.randn(len(timestamps)) * 3),
        'heel': np.abs(np.sin(np.linspace(0, 32, len(timestamps))) * 45 + np.random.randn(len(timestamps)) * 3),
        'bigToe_L': np.abs(np.sin(np.linspace(0, 30, len(timestamps)) + 0.5) * 40 + np.random.randn(len(timestamps)) * 3),
        'pinkyToe_L': np.abs(np.sin(np.linspace(0, 25, len(timestamps)) + 0.5) * 35 + np.random.randn(len(timestamps)) * 3),
        'metaOut_L': np.abs(np.sin(np.linspace(0, 28, len(timestamps)) + 0.5) * 38 + np.random.randn(len(timestamps)) * 3),
        'metaIn_L': np.abs(np.sin(np.linspace(0, 26, len(timestamps)) + 0.5) * 36 + np.random.randn(len(timestamps)) * 3),
        'heel_L': np.abs(np.sin(np.linspace(0, 32, len(timestamps)) + 0.5) * 45 + np.random.randn(len(timestamps)) * 3),
    }
    
    return pd.DataFrame(data)

def main():
    print("=" * 60)
    print("Blynk Integration Test")
    print("=" * 60)
    print()
    
    # Initialize Blynk service
    print("1. Initializing Blynk service...")
    blynk = BlynkService()
    
    # Test connection
    print("2. Testing Blynk connection...")
    if blynk.connect():
        print("   ✓ Connection successful!")
    else:
        print("   ✗ Connection failed!")
        print("   Make sure your Blynk auth token is correct")
        return
    
    print()
    
    # Generate test data
    print("3. Generating test pressure data...")
    df = generate_test_data()
    print(f"   ✓ Generated {len(df)} data points")
    print()
    
    # Calculate ratings
    print("4. Calculating pressure ratings...")
    ratings = blynk.calculate_pressure_ratings(df)
    print("   Ratings:")
    for sensor, rating in ratings.items():
        print(f"     - {sensor}: {rating}")
    print()
    
    # Calculate gait metrics
    print("5. Calculating gait metrics...")
    metrics = blynk.calculate_gait_metrics(df)
    print("   Metrics:")
    print(f"     - Cadence: {metrics['cadence']:.1f} steps/min")
    print(f"     - Swing Time: {metrics['swing_time']:.2f} seconds")
    print(f"     - Stance Time: {metrics['stance_time']:.2f} seconds")
    print(f"     - Step Symmetry: {metrics['step_symmetry']:.1f}%")
    print()
    
    # Send to Blynk
    print("6. Sending data to Blynk...")
    success = blynk.send_to_blynk(ratings, metrics)
    if success:
        print("   ✓ Data sent successfully!")
        print()
        print("=" * 60)
        print("Check your Blynk app to see the updated values:")
        print("  V0: Big Toe Rating")
        print("  V1: Pinky Toe Rating")
        print("  V2: Meta Out Rating")
        print("  V3: Meta In Rating")
        print("  V4: Heel Rating")
        print("  V5: Cadence")
        print("  V6: Swing Time")
        print("  V7: Stance Time")
        print("  V8: Step Symmetry")
        print("=" * 60)
    else:
        print("   ✗ Failed to send data!")
    
    print()

if __name__ == "__main__":
    main()
