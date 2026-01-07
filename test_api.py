#!/usr/bin/env python3
"""Test script to send mock pressure data to the API"""

import requests
import json
from datetime import datetime, timedelta

# API base URL
BASE_URL = "http://127.0.0.1:8000"

def send_mock_data():
    """Send mock pressure readings to the API"""
    
    # Create mock data with timestamps spread across the last hour
    samples = []
    now = datetime.now()
    
    for i in range(10):
        timestamp = now - timedelta(minutes=10-i)
        sample = {
            "timestamp": timestamp.isoformat(),
            "pressures": {
                "bigToe": 50.0 + i * 2,
                "pinkyToe": 40.0 + i * 1.5,
                "metaOut": 60.0 + i * 2.5,
                "metaIn": 55.0 + i * 2,
                "heel": 70.0 + i * 3
            }
        }
        samples.append(sample)
    
    payload = {
        "device_id": "ESP32_001",
        "sample_count": len(samples),
        "samples": samples
    }
    
    print("Sending mock data to POST /api/pressure...")
    print(json.dumps(payload, indent=2, default=str)[:500] + "...\n")
    
    try:
        response = requests.post(f"{BASE_URL}/api/pressure", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}\n")
    except Exception as e:
        print(f"Error sending data: {e}\n")

def retrieve_readings():
    """Retrieve the readings from the API"""
    
    print("Retrieving readings from GET /api/readings?limit=20...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/readings", params={"limit": 20})
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Retrieved {len(data)} readings")
        print(json.dumps(data, indent=2, default=str)[:500] + "...\n")
        return data
    except Exception as e:
        print(f"Error retrieving readings: {e}\n")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("API Test Script")
    print("=" * 60 + "\n")
    
    # Send mock data
    send_mock_data()
    
    # Retrieve and display readings
    readings = retrieve_readings()
    
    if readings:
        print("✓ API is working! You can now display this data in Streamlit")
    else:
        print("✗ Failed to retrieve data. Make sure the API is running:")
        print("  python -m uvicorn backend.app_main:app --reload")
