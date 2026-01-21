# page_3.py - Advanced Gait Analysis

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import requests
from patient_utils import load_patient_data, is_demo_patient, get_patient_display_name

# ---------------------------
# Configuration
# ---------------------------

CLOUD_DATA_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings"
FS = 25  # sampling frequency (Hz)


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
    df = df.sort_values("timestamp")
    return df


def load_mock_data() -> pd.DataFrame:
    start_date = datetime.now() - pd.Timedelta(hours=1)  # Start from 1 hour ago
    rng = pd.date_range(start_date, periods=300, freq="10s")
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


# ---------------------------
# Main App
# ---------------------------

def main():
    # Get selected patient info
    patient_name = get_patient_display_name()
    is_demo = is_demo_patient()
    
    st.set_page_config(
        page_title="Advanced Gait Analysis",
        layout="wide",
    )

    st.title("📈 Advanced Gait Analysis")
    patient_badge = "🎭 Demo Patient" if is_demo else f"📡 {patient_name}"
    st.caption(f"Viewing data for: **{patient_badge}**")
    st.write("Detailed analysis of gait symmetry, load distribution, and pressure patterns.")

    # Sidebar
    st.sidebar.header("Settings")
    foot_selection = st.sidebar.radio("Select Foot", ["Right Foot", "Left Foot", "Both Feet"], index=0)

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
    # Analysis Sections
    # ---------------------------
    
    st.header("🔍 Load Distribution Analysis")
    
    # Calculate load per sensor
    right_sensors = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    left_sensors = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
    
    # Average pressure per point
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Right Foot Load Distribution")
        right_load = {sensor: df[sensor].mean() for sensor in right_sensors if sensor in df.columns}
        
        fig_right = go.Figure(data=[
            go.Bar(x=list(right_load.keys()), y=list(right_load.values()),
                   marker_color='#0072B2')
        ])
        fig_right.update_layout(
            title="Average Pressure by Sensor (Right)",
            xaxis_title="Sensor",
            yaxis_title="Average Pressure",
            height=400
        )
        st.plotly_chart(fig_right)
    
    with col2:
        st.subheader("Left Foot Load Distribution")
        left_load = {sensor.replace('_L', ''): df[sensor].mean() for sensor in left_sensors if sensor in df.columns}
        
        fig_left = go.Figure(data=[
            go.Bar(x=list(left_load.keys()), y=list(left_load.values()),
                   marker_color='#E69F00')
        ])
        fig_left.update_layout(
            title="Average Pressure by Sensor (Left)",
            xaxis_title="Sensor",
            yaxis_title="Average Pressure",
            height=400
        )
        st.plotly_chart(fig_left)

    # ---------------------------
    # Gait Symmetry Analysis
    # ---------------------------
    
    st.header("⚖️ Gait Symmetry Index")
    
    col1, col2, col3 = st.columns(3)
    
    right_total = df[right_sensors].sum(axis=1).mean()
    left_total = df[left_sensors].sum(axis=1).mean()
    
    symmetry_index = 100 - abs(right_total - left_total) / max(right_total, left_total) * 100
    
    with col1:
        st.metric("Right Foot Total Load", f"{right_total:.1f}")
    with col2:
        st.metric("Left Foot Total Load", f"{left_total:.1f}")
    with col3:
        st.metric("Symmetry Index", f"{symmetry_index:.1f}%", 
                 delta="Balanced" if symmetry_index > 85 else "Asymmetrical")

    # ---------------------------
    # Pressure Timeline
    # ---------------------------
    
    st.header("📊 Pressure Timeline Over Time")
    
    time_seconds = (df['timestamp'] - df['timestamp'].iloc[0]).dt.total_seconds()
    
    fig_timeline = go.Figure()
    
    if foot_selection in ["Right Foot", "Both Feet"]:
        fig_timeline.add_trace(go.Scatter(
            x=time_seconds, y=df['bigToe'],
            name='Big Toe (R)', mode='lines', line=dict(color='#0072B2')
        ))
        fig_timeline.add_trace(go.Scatter(
            x=time_seconds, y=df['heel'],
            name='Heel (R)', mode='lines', line=dict(color='#0072B2', dash='dash')
        ))
    
    if foot_selection in ["Left Foot", "Both Feet"]:
        fig_timeline.add_trace(go.Scatter(
            x=time_seconds, y=df['bigToe_L'],
            name='Big Toe (L)', mode='lines', line=dict(color='#E69F00')
        ))
        fig_timeline.add_trace(go.Scatter(
            x=time_seconds, y=df['heel_L'],
            name='Heel (L)', mode='lines', line=dict(color='#E69F00', dash='dash')
        ))
    
    title_text = "Pressure Timeline - " + ("Right Foot" if foot_selection == "Right Foot" else "Left Foot" if foot_selection == "Left Foot" else "Both Feet")
    fig_timeline.update_layout(
        title=title_text,
        xaxis_title="Time (seconds)",
        yaxis_title="Pressure",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig_timeline)

    # ---------------------------
    # Statistics Table
    # ---------------------------
    
    st.header("📋 Statistical Summary")
    
    if foot_selection == "Right Foot":
        stats_data = {
            'Sensor': right_sensors,
            'Mean': [df[s].mean() for s in right_sensors],
            'Std Dev': [df[s].std() for s in right_sensors],
            'Max': [df[s].max() for s in right_sensors],
        }
    elif foot_selection == "Left Foot":
        stats_data = {
            'Sensor': [s.replace('_L', '') for s in left_sensors],
            'Mean': [df[s].mean() for s in left_sensors],
            'Std Dev': [df[s].std() for s in left_sensors],
            'Max': [df[s].max() for s in left_sensors],
        }
    else:  # Both Feet
        stats_data = {
            'Sensor': right_sensors + [s.replace('_L', '') for s in left_sensors],
            'Mean (R)': [df[s].mean() for s in right_sensors] + [None] * len(left_sensors),
            'Std Dev (R)': [df[s].std() for s in right_sensors] + [None] * len(left_sensors),
            'Max (R)': [df[s].max() for s in right_sensors] + [None] * len(left_sensors),
            'Mean (L)': [None] * len(right_sensors) + [df[s].mean() for s in left_sensors],
            'Std Dev (L)': [None] * len(right_sensors) + [df[s].std() for s in left_sensors],
            'Max (L)': [None] * len(right_sensors) + [df[s].max() for s in left_sensors],
        }
    
    stats_df = pd.DataFrame(stats_data)
    st.dataframe(stats_df)
    
    # Auto-refresh to keep data updated
    st.caption(f"Auto-refreshing every 2 seconds.")
    import time as time_module
    time_module.sleep(2)
    st.rerun()


if __name__ == "__main__":
    main()