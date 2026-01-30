#!/usr/bin/env python3
"""
Test script to send simulated gait data to backend and trigger Blynk gait balance graph.
Simulates alternating left/right foot steps to create a sine-wave pattern in V9.
"""

import requests
import time
import math
from datetime import datetime

# Backend API URL
API_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev"

def generate_gait_cycle(t, foot='right'):
    """
    Generate pressure values for a walking gait cycle.
    t: time parameter (0 to 2π for one complete cycle)
    foot: 'right' or 'left'
    
    Returns dict of sensor pressures
    """
    # Simulate heel strike, stance, toe-off pattern
    heel = max(0, 50 + 30 * math.sin(t))
    meta_in = max(0, 40 + 20 * math.sin(t + math.pi/4))
    meta_out = max(0, 35 + 20 * math.sin(t + math.pi/4))
    big_toe = max(0, 30 + 25 * math.sin(t + math.pi/2))
    pinky_toe = max(0, 25 + 20 * math.sin(t + math.pi/2))
    
    return {
        'bigToe': round(big_toe, 1),
        'pinkyToe': round(pinky_toe, 1),
        'metaOut': round(meta_out, 1),
        'metaIn': round(meta_in, 1),
        'heel': round(heel, 1)
    }

def send_test_batch(cycle_offset=0):
    """
    Send a batch of 25 samples showing alternating foot dominance.
    This simulates walking with alternating steps.
    """
    readings = []
    timestamp = int(time.time())
    
    for i in range(25):
        t = (cycle_offset + i) * 0.25  # Progress through gait cycle
        
        # Alternate between right and left foot dominance
        # Create a sine wave pattern where feet alternate
        phase = t
        
        # Right foot: peaks when sin is positive
        right_multiplier = max(0.3, (math.sin(phase) + 1) / 2)
        # Left foot: peaks when sin is negative (opposite phase)
        left_multiplier = max(0.3, (-math.sin(phase) + 1) / 2)
        
        # Generate base pressure patterns
        right_base = generate_gait_cycle(t, 'right')
        left_base = generate_gait_cycle(t + math.pi, 'left')  # Opposite phase
        
        # Apply dominance multipliers
        reading = {
            'timestamp': timestamp + i,
            # Right foot with multiplier (s1-s5)
            's1': round(right_base['bigToe'] * right_multiplier, 1),
            's2': round(right_base['pinkyToe'] * right_multiplier, 1),
            's3': round(right_base['metaOut'] * right_multiplier, 1),
            's4': round(right_base['metaIn'] * right_multiplier, 1),
            's5': round(right_base['heel'] * right_multiplier, 1),
            # Left foot with multiplier (s6-s10)
            's6': round(left_base['bigToe'] * left_multiplier, 1),
            's7': round(left_base['pinkyToe'] * left_multiplier, 1),
            's8': round(left_base['metaOut'] * left_multiplier, 1),
            's9': round(left_base['metaIn'] * left_multiplier, 1),
            's10': round(left_base['heel'] * left_multiplier, 1)
        }
        readings.append(reading)
    
    # Send batch to backend
    payload = {
        "device_id": "TEST_GAIT_BALANCE",
        "readings": readings
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/pressure?patient_id=1",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            print(f"✓ Sent batch (cycle {cycle_offset//25 + 1}) - {len(readings)} samples")
            return True
        else:
            print(f"✗ Failed to send batch: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error sending data: {e}")
        return False

def main():
    print("=" * 60)
    print("GAIT BALANCE TEST - Sine Wave Pattern Generator")
    print("=" * 60)
    print("\nThis will send simulated walking data to create a")
    print("biphasic sine-wave pattern in your Blynk V9 graph.")
    print("\nPattern: Left foot (positive) ↔ Right foot (negative)")
    print("=" * 60)
    print()
    
    # Send 5 batches to create nice wave pattern
    print("Sending test data batches...")
    for i in range(5):
        success = send_test_batch(cycle_offset=i * 25)
        if success:
            time.sleep(2.5)  # Match ESP32 timing
        else:
            print("Failed to send batch, stopping...")
            break
    
    print("\n" + "=" * 60)
    print("✓ Test complete!")
    print("=" * 60)
    print("\nCheck your Blynk app - V9 SuperChart should show:")
    print("  • Oscillating wave pattern (sine wave)")
    print("  • Positive peaks = Left foot stepping")
    print("  • Negative dips = Right foot stepping")
    print("  • Range: approximately -50 to +50")
    print("\nIf graph is flat, make sure both ESP32s are sending data.")
    print("=" * 60)

if __name__ == "__main__":
    main()
