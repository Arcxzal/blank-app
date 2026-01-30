"""
Helper functions for patient data management in Streamlit pages
"""
import streamlit as st
import requests
import pandas as pd
from mock_data_generator import generate_mock_data
import pytz

# Backend API URL
API_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev"

def get_current_patient_id():
    """Get the currently selected patient ID from session state"""
    return st.session_state.get('selected_patient_id', 'demo')

def is_demo_patient():
    """Check if demo patient is selected"""
    return get_current_patient_id() == "demo"

def load_patient_data(num_cycles=20, cadence=115):
    """
    Load data for currently selected patient.
    Returns DataFrame with pressure data.
    
    Args:
        num_cycles: Number of gait cycles for demo data
        cadence: Cadence for demo data generation
    """
    patient_id = get_current_patient_id()
    
    if patient_id == "demo":
        # Generate mock data
        df = generate_mock_data(num_cycles=num_cycles, cadence=cadence)
        # Rename columns to match expected format
        df = df.rename(columns={
            'bigtoepressure': 'bigToe',
            'pinkytoepressure': 'pinkyToe',
            'metaoutpressure': 'metaOut',
            'metainpressure': 'metaIn',
            'heelpressure': 'heel',
            'bigtoepressure_l': 'bigToe_L',
            'pinkytoepressure_l': 'pinkyToe_L',
            'metaoutpressure_l': 'metaOut_L',
            'metainpressure_l': 'metaIn_L',
            'heelpressure_l': 'heel_L',
        })
        return df
    else:
        # Load real patient data from API
        try:
            response = requests.get(
                f"{API_URL}/api/readings",
                params={"patient_id": patient_id, "limit": 500},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Convert API response to DataFrame
            records = []
            for entry in data:
                timestamp = entry.get("timestamp")
                if not timestamp:
                    continue
                pressures = entry.get("pressures", {})
                record = {
                    "timestamp": timestamp,
                    "bigToe": pressures.get("bigToe", 0),
                    "pinkyToe": pressures.get("pinkyToe", 0),
                    "metaOut": pressures.get("metaOut", 0),
                    "metaIn": pressures.get("metaIn", 0),
                    "heel": pressures.get("heel", 0),
                    "bigToe_L": pressures.get("bigToe_L", 0),
                    "pinkyToe_L": pressures.get("pinkyToe_L", 0),
                    "metaOut_L": pressures.get("metaOut_L", 0),
                    "metaIn_L": pressures.get("metaIn_L", 0),
                    "heel_L": pressures.get("heel_L", 0),
                }
                records.append(record)
            
            if not records:
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df.dropna(subset=["timestamp"])
            # Convert UTC to Singapore timezone (GMT+8)
            df["timestamp"] = df["timestamp"].dt.tz_convert('Asia/Singapore')
            df = df.sort_values("timestamp")
            return df
            
        except Exception as e:
            st.error(f"Error loading patient data: {e}")
            return pd.DataFrame()

def get_patient_display_name():
    """Get display name for current patient"""
    return st.session_state.get('selected_patient_name', 'Unknown Patient')
