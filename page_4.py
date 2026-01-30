# page_4.py - Data Exploration and Metrics

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime
from patient_utils import load_patient_data, is_demo_patient, get_patient_display_name
from mock_data_generator import generate_mock_data
import pytz

# ---------------------------
# Configuration
# ---------------------------

CLOUD_DATA_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings"


# ---------------------------
# Data Loading
# ---------------------------

@st.cache_data(ttl=2)
def load_data_from_api() -> pd.DataFrame:
    response = requests.get(CLOUD_DATA_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    
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
    # Keep UTC timezone - matches ESP32 NTP timestamps from backend
    df = df.sort_values("timestamp")
    return df


def load_mock_data() -> pd.DataFrame:
    import pytz
    start_date = datetime.now(pytz.UTC) - pd.Timedelta(hours=1)  # Start from 1 hour ago (UTC)
    rng = pd.date_range(start_date, periods=300, freq="10s", tz='UTC')
    df = pd.DataFrame({
        "timestamp": rng,
        "bigToe": np.abs(np.sin(np.linspace(0, 30, len(rng))) * 40 + np.random.randn(len(rng)) * 3),
        "pinkyToe": np.abs(np.sin(np.linspace(0, 25, len(rng))) * 35 + np.random.randn(len(rng)) * 3),
        "metaOut": np.abs(np.sin(np.linspace(0, 28, len(rng))) * 38 + np.random.randn(len(rng)) * 3),
        "metaIn": np.abs(np.sin(np.linspace(0, 26, len(rng))) * 36 + np.random.randn(len(rng)) * 3),
        "heel": np.abs(np.sin(np.linspace(0, 32, len(rng))) * 45 + np.random.randn(len(rng)) * 3),
        "bigToe_L": np.abs(np.sin(np.linspace(0, 30, len(rng)) + 0.5) * 40 + np.random.randn(len(rng)) * 3),
        "pinkyToe_L": np.abs(np.sin(np.linspace(0, 25, len(rng)) + 0.5) * 35 + np.random.randn(len(rng)) * 3),
        "metaOut_L": np.abs(np.sin(np.linspace(0, 28, len(rng)) + 0.5) * 38 + np.random.randn(len(rng)) * 3),
        "metaIn_L": np.abs(np.sin(np.linspace(0, 26, len(rng)) + 0.5) * 36 + np.random.randn(len(rng)) * 3),
        "heel_L": np.abs(np.sin(np.linspace(0, 32, len(rng)) + 0.5) * 45 + np.random.randn(len(rng)) * 3),
    })
    return df


def merge_left_right_foot_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intelligently merge left and right foot readings from separate ESP32s.
    Matches timestamps within 1 second and combines data into single rows.
    """
    if df.empty:
        return df
    
    # Create a working copy
    result_rows = []
    used_indices = set()
    
    for idx, row in df.iterrows():
        if idx in used_indices:
            continue
        
        current_row = row.copy()
        current_ts = row['timestamp']
        
        # Check if this row has data for only one foot
        right_has_data = (row['bigToe'] > 0 or row['pinkyToe'] > 0 or 
                         row['metaOut'] > 0 or row['metaIn'] > 0 or row['heel'] > 0)
        left_has_data = (row['bigToe_L'] > 0 or row['pinkyToe_L'] > 0 or 
                        row['metaOut_L'] > 0 or row['metaIn_L'] > 0 or row['heel_L'] > 0)
        
        # If this row has only right foot data, look for matching left foot data
        if right_has_data and not left_has_data:
            for other_idx in range(idx + 1, min(idx + 10, len(df))):
                if other_idx in used_indices:
                    continue
                other_row = df.iloc[other_idx]
                time_diff = abs((other_row['timestamp'] - current_ts).total_seconds())
                
                if time_diff <= 1.0:
                    other_right = (other_row['bigToe'] > 0 or other_row['pinkyToe'] > 0 or 
                                  other_row['metaOut'] > 0 or other_row['metaIn'] > 0 or other_row['heel'] > 0)
                    other_left = (other_row['bigToe_L'] > 0 or other_row['pinkyToe_L'] > 0 or 
                                 other_row['metaOut_L'] > 0 or other_row['metaIn_L'] > 0 or other_row['heel_L'] > 0)
                    
                    if other_left and not other_right:
                        current_row['bigToe_L'] = other_row['bigToe_L']
                        current_row['pinkyToe_L'] = other_row['pinkyToe_L']
                        current_row['metaOut_L'] = other_row['metaOut_L']
                        current_row['metaIn_L'] = other_row['metaIn_L']
                        current_row['heel_L'] = other_row['heel_L']
                        used_indices.add(other_idx)
                        break
        
        # If this row has only left foot data, look for matching right foot data
        elif left_has_data and not right_has_data:
            for other_idx in range(idx + 1, min(idx + 10, len(df))):
                if other_idx in used_indices:
                    continue
                other_row = df.iloc[other_idx]
                time_diff = abs((other_row['timestamp'] - current_ts).total_seconds())
                
                if time_diff <= 1.0:
                    other_right = (other_row['bigToe'] > 0 or other_row['pinkyToe'] > 0 or 
                                  other_row['metaOut'] > 0 or other_row['metaIn'] > 0 or other_row['heel'] > 0)
                    other_left = (other_row['bigToe_L'] > 0 or other_row['pinkyToe_L'] > 0 or 
                                 other_row['metaOut_L'] > 0 or other_row['metaIn_L'] > 0 or other_row['heel_L'] > 0)
                    
                    if other_right and not other_left:
                        current_row['bigToe'] = other_row['bigToe']
                        current_row['pinkyToe'] = other_row['pinkyToe']
                        current_row['metaOut'] = other_row['metaOut']
                        current_row['metaIn'] = other_row['metaIn']
                        current_row['heel'] = other_row['heel']
                        used_indices.add(other_idx)
                        break
        
        result_rows.append(current_row)
        used_indices.add(idx)
    
    return pd.DataFrame(result_rows) if result_rows else df


# ---------------------------
# Main App
# ---------------------------

def main():
    # Get selected patient info
    patient_name = get_patient_display_name()
    is_demo = is_demo_patient()
    
    st.set_page_config(
        page_title="Data Exploration & Metrics",
        layout="wide",
    )

    st.title("📋 Data Exploration & Metrics")
    patient_badge = "🎭 Demo Patient" if is_demo else f"📡 {patient_name}"
    st.caption(f"Viewing data for: **{patient_badge}**")
    st.write("Explore raw data and view comprehensive metrics and statistics.")

    # Sidebar
    st.sidebar.header("Settings")
    rows_to_display = st.sidebar.slider("Rows to display", min_value=10, max_value=500, value=50)

    # Load data using helper function
    try:
        df = load_patient_data(num_cycles=20, cadence=115)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        df = pd.DataFrame()

    if df.empty:
        st.warning("⚠️ No data available. Please enable mock data or check your connection.")
        return

    # ---------------------------
    # Data Overview
    # ---------------------------
    
    st.header("📊 Data Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Records", len(df))
    with col2:
        st.metric("Time Span", f"{(df['timestamp'].max() - df['timestamp'].min()).total_seconds():.0f}s")
    with col3:
        st.metric("Start Time", df['timestamp'].min().strftime("%H:%M:%S"))
    with col4:
        st.metric("End Time", df['timestamp'].max().strftime("%H:%M:%S"))
    with col5:
        st.metric("Columns", len(df.columns))

    # ---------------------------
    # Raw Data Table
    # ---------------------------
    
    st.header("📑 Raw Data")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Pressure Readings Table")
    with col2:
        if st.button("📥 Export CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"pressure_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    st.dataframe(df.head(rows_to_display), height=400)

    # ---------------------------
    # Descriptive Statistics
    # ---------------------------
    
    st.header("📈 Descriptive Statistics")
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    stats = df[numeric_cols].describe().T
    st.dataframe(stats)


    # ---------------------------
    # Summary Metrics
    # ---------------------------
    
    st.header("🎯 Summary Metrics")
    
    right_total = df[['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']].sum(axis=1)
    left_total = df[['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']].sum(axis=1)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Right Foot Avg", f"{right_total.mean():.1f}")
    with col2:
        st.metric("Left Foot Avg", f"{left_total.mean():.1f}")
    with col3:
        st.metric("Right Foot Max", f"{right_total.max():.1f}")
    with col4:
        st.metric("Left Foot Max", f"{left_total.max():.1f}")
    
    # Auto-refresh to keep data updated
    st.caption(f"Auto-refreshing every 2 seconds.")
    import time as time_module
    time_module.sleep(2)
    st.rerun()


if __name__ == "__main__":
    main()
