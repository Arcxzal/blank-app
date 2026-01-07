import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Pressure Readings Dashboard", layout="wide")

st.title("🦶 Foot Pressure Readings Dashboard")

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"

# Sidebar controls
st.sidebar.header("Controls")
limit = st.sidebar.slider("Number of readings to display", 10, 500, 50)
auto_refresh = st.sidebar.checkbox("Auto-refresh every 5 seconds", value=False)

# Fetch data
@st.cache_data(ttl=5)
def fetch_readings(limit_val):
    try:
        response = requests.get(f"{API_BASE_URL}/api/readings", params={"limit": limit_val})
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# Fetch and display
readings = fetch_readings(limit)

if readings:
    st.success(f"✓ Connected to API - {len(readings)} readings loaded")
    
    # Convert to DataFrame for easier analysis
    data = []
    for reading in readings:
        pressures = reading["pressures"]
        data.append({
            "Timestamp": pd.to_datetime(reading["timestamp"]),
            "Big Toe": pressures["bigToe"],
            "Pinky Toe": pressures["pinkyToe"],
            "Meta Out": pressures["metaOut"],
            "Meta In": pressures["metaIn"],
            "Heel": pressures["heel"],
        })
    
    df = pd.DataFrame(data)
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Avg Big Toe", f"{df['Big Toe'].mean():.1f}")
    with col2:
        st.metric("Avg Pinky Toe", f"{df['Pinky Toe'].mean():.1f}")
    with col3:
        st.metric("Avg Meta Out", f"{df['Meta Out'].mean():.1f}")
    with col4:
        st.metric("Avg Meta In", f"{df['Meta In'].mean():.1f}")
    with col5:
        st.metric("Avg Heel", f"{df['Heel'].mean():.1f}")
    
    # Line chart
    st.subheader("Pressure Over Time")
    pressure_cols = ["Big Toe", "Pinky Toe", "Meta Out", "Meta In", "Heel"]
    fig = px.line(df, x="Timestamp", y=pressure_cols, 
                  title="All Pressure Sensors",
                  labels={"value": "Pressure (units)", "variable": "Sensor"})
    st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.subheader("Raw Data")
    st.dataframe(df, use_container_width=True)
    
    if auto_refresh:
        st.info("Auto-refresh enabled - Page will refresh every 5 seconds")
        import time
        time.sleep(5)
        st.rerun()
else:
    st.error("Could not connect to API. Make sure it's running on http://127.0.0.1:8000")
    st.info("Start the API with: `python -m uvicorn backend.app_main:app --reload`")
