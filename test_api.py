import requests
import pandas as pd
import pytz

# Backend API URL
API_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev"


def fetch_patients():
    """Fetch all patients from the API."""
    response = requests.get(f"{API_URL}/api/patients", timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_df(patient_id: int = None, api_url: str = API_URL) -> pd.DataFrame:
    """
    Fetch readings from the API and return a flattened DataFrame.
    
    Args:
        patient_id: Filter by patient ID (optional)
        api_url: Base API URL
    
    Returns:
        DataFrame with pressure readings
    """
    params = {"patient_id": patient_id} if patient_id else {}
    response = requests.get(f"{api_url}/api/readings", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    records = []
    for entry in data:
        pressures = entry.get("pressures", {})
        records.append({
            "timestamp": entry.get("timestamp"),
            "patient_id": entry.get("patient_id"),
            "bigToe": pressures.get("bigToe"),
            "pinkyToe": pressures.get("pinkyToe"),
            "metaOut": pressures.get("metaOut"),
            "metaIn": pressures.get("metaIn"),
            "heel": pressures.get("heel"),
        })

    df = pd.DataFrame(records)

    # Force proper datetime dtype and drop invalid rows
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    # Convert UTC to Singapore timezone (GMT+8)
    df["timestamp"] = df["timestamp"].dt.tz_convert('Asia/Singapore')

    return df


def send_test_data(patient_id: int = 1):
    """
    Send test pressure data to the API.
    
    Args:
        patient_id: Patient ID to associate with the data
    """
    url = f"{API_URL}/api/pressure?patient_id={patient_id}"
    
    payload = {
        "device_id": "TEST_DEVICE",
        "readings": [
            {
                "timestamp": 1234567890,
                "s1": 45.5,  # bigToe
                "s2": 30.2,  # pinkyToe
                "s3": 55.8,  # metaOut
                "s4": 40.1,  # metaIn
                "s5": 60.3,  # heel
                "s6": 42.0,  # left bigToe
                "s7": 28.5,  # left pinkyToe
                "s8": 52.1,  # left metaOut
                "s9": 38.9,  # left metaIn
                "s10": 58.7  # left heel
            }
        ]
    }
    
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    
    print(f"✓ Test data sent successfully for patient {patient_id}")
    print(f"Response: {response.json()}")
    return response.json()


# Convenience: allow importing a ready DataFrame without executing Streamlit
try:
    df = fetch_df()
except Exception:
    df = pd.DataFrame()


if __name__ == "__main__":
    print("=== Testing Multi-Patient API ===\n")
    
    # Test 1: Fetch all patients
    print("1. Fetching all patients...")
    patients = fetch_patients()
    print(f"   Found {len(patients)} patients:")
    for p in patients:
        print(f"   - ID={p['id']}: {p['name']} (Age: {p['age']})")
    
    # Test 2: Send test data for patient 1
    print("\n2. Sending test data for patient 1...")
    send_test_data(patient_id=1)
    
    # Test 3: Fetch data for specific patient
    print("\n3. Fetching readings for patient 1...")
    df = fetch_df(patient_id=1)
    print(f"   Retrieved {len(df)} readings")
    if not df.empty:
        print(f"   Latest reading: {df.iloc[0].to_dict()}")
    
    print("\n✓ All tests completed!")

