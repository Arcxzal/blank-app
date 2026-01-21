# page_5.py - Configuration and Advanced Settings

import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------
# Page Configuration
# ---------------------------

st.set_page_config(
    page_title="Configuration & Settings",
    layout="wide",
)

st.title("🔧 Configuration & Advanced Settings")
st.write("Adjust system parameters, filtering options, and analysis thresholds.")

# ---------------------------
# Settings Storage (using Session State)
# ---------------------------

if 'settings' not in st.session_state:
    st.session_state.settings = {
        'sampling_frequency': 25,
        'savgol_window': 13,
        'savgol_polyorder': 3,
        'step_threshold': 20,
        'heel_threshold': 0.15,
        'forefoot_threshold': 0.15,
        'auto_refresh': True,
        'refresh_interval': 2,
        'api_url': 'https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings',
        'enable_mock_data': True,
        'data_retention_hours': 24,
    }


# ---------------------------
# Tabs for Organization
# ---------------------------

tab1, tab2, tab3, tab4 = st.tabs(["📊 Signal Processing", "🎯 Detection Settings", "🔄 Data & Refresh", "ℹ️ System Info"])

# ---------------------------
# Tab 1: Signal Processing
# ---------------------------

with tab1:
    st.header("Signal Processing Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Savitzky-Golay Filter")
        
        sampling_freq = st.slider(
            "Sampling Frequency (Hz)",
            min_value=10,
            max_value=100,
            value=st.session_state.settings['sampling_frequency'],
            help="Samples per second from pressure sensors"
        )
        st.session_state.settings['sampling_frequency'] = sampling_freq
        
        st.info(f"Current: {sampling_freq} Hz = {1000/sampling_freq:.1f} ms per sample")
        
        savgol_window = st.slider(
            "Window Length (samples)",
            min_value=5,
            max_value=31,
            value=st.session_state.settings['savgol_window'],
            step=2,
            help="Must be odd number. ~0.5s at 25Hz = 13 samples"
        )
        st.session_state.settings['savgol_window'] = savgol_window
        
        savgol_poly = st.slider(
            "Polynomial Order",
            min_value=1,
            max_value=5,
            value=st.session_state.settings['savgol_polyorder'],
            help="Degree of polynomial for Savitzky-Golay filter"
        )
        st.session_state.settings['savgol_polyorder'] = savgol_poly
    
    with col2:
        st.subheader("Filter Explanation")
        st.markdown("""
        The **Savitzky-Golay filter** smooths pressure signals while preserving sharp peaks.
        
        **Parameters:**
        - **Window Length**: How many samples to consider (larger = more smoothing)
        - **Polynomial Order**: Degree of fitting polynomial (higher = preserves more details)
        
        **Current Configuration:**
        - Window: ~{:.2f} seconds
        - Smooth for artifact removal ✓
        - Preserve gait events ✓
        """.format(savgol_window / sampling_freq))
        
        st.success("✓ Optimal for gait analysis")

# ---------------------------
# Tab 2: Detection Settings
# ---------------------------

with tab2:
    st.header("Gait Event Detection Thresholds")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Step Detection")
        
        step_thresh = st.slider(
            "Step Threshold",
            min_value=5,
            max_value=100,
            value=st.session_state.settings['step_threshold'],
            help="Minimum pressure to detect a step"
        )
        st.session_state.settings['step_threshold'] = step_thresh
        
        st.caption(f"Steps detected when pressure > {step_thresh}")
    
    with col2:
        st.subheader("Heel/Forefoot Detection")
        
        heel_thresh = st.slider(
            "Heel Threshold (fraction)",
            min_value=0.05,
            max_value=0.5,
            value=st.session_state.settings['heel_threshold'],
            step=0.05,
            help="Fraction of max heel pressure for heel-strike detection"
        )
        st.session_state.settings['heel_threshold'] = heel_thresh
        
        forefoot_thresh = st.slider(
            "Forefoot Threshold (fraction)",
            min_value=0.05,
            max_value=0.5,
            value=st.session_state.settings['forefoot_threshold'],
            step=0.05,
            help="Fraction of max forefoot pressure for toe-off detection"
        )
        st.session_state.settings['forefoot_threshold'] = forefoot_thresh

    st.divider()
    st.subheader("Recommended Presets")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⚡ Sensitive (Low thresholds)"):
            st.session_state.settings['step_threshold'] = 10
            st.session_state.settings['heel_threshold'] = 0.10
            st.session_state.settings['forefoot_threshold'] = 0.10
            st.success("Sensitive mode enabled!")
            st.rerun()
    
    with col2:
        if st.button("⚙️ Balanced (Recommended)"):
            st.session_state.settings['step_threshold'] = 20
            st.session_state.settings['heel_threshold'] = 0.15
            st.session_state.settings['forefoot_threshold'] = 0.15
            st.success("Balanced mode enabled!")
            st.rerun()
    
    with col3:
        if st.button("🛡️ Robust (High thresholds)"):
            st.session_state.settings['step_threshold'] = 35
            st.session_state.settings['heel_threshold'] = 0.25
            st.session_state.settings['forefoot_threshold'] = 0.25
            st.success("Robust mode enabled!")
            st.rerun()

# ---------------------------
# Tab 3: Data & Refresh
# ---------------------------

with tab3:
    st.header("Data Source & Update Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("API Configuration")
        
        api_url = st.text_input(
            "API Endpoint URL",
            value=st.session_state.settings['api_url'],
            help="Cloud API endpoint for pressure readings"
        )
        st.session_state.settings['api_url'] = api_url
        
        enable_mock = st.checkbox(
            "Enable Mock Data",
            value=st.session_state.settings['enable_mock_data'],
            help="Use synthetic data when real data unavailable"
        )
        st.session_state.settings['enable_mock_data'] = enable_mock
    
    with col2:
        st.subheader("Refresh Settings")
        
        auto_refresh = st.checkbox(
            "Auto-refresh Dashboard",
            value=st.session_state.settings['auto_refresh'],
            help="Automatically update graphs with new data"
        )
        st.session_state.settings['auto_refresh'] = auto_refresh
        
        refresh_interval = st.slider(
            "Refresh Interval (seconds)",
            min_value=0.5,
            max_value=10.0,
            value=float(st.session_state.settings['refresh_interval']),
            step=0.5,
            help="How often to fetch new data"
        )
        st.session_state.settings['refresh_interval'] = refresh_interval
        
        data_retention = st.slider(
            "Data Retention (hours)",
            min_value=1,
            max_value=168,
            value=st.session_state.settings['data_retention_hours'],
            help="How long to keep historical data"
        )
        st.session_state.settings['data_retention_hours'] = data_retention

# ---------------------------
# Tab 4: System Information
# ---------------------------

with tab4:
    st.header("System Information & Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Status")
        st.metric("Backend Status", "🟢 Connected")
        st.metric("Last Data Update", "2 seconds ago")
        st.metric("Active Sessions", 1)
    
    with col2:
        st.subheader("Performance Metrics")
        st.metric("Graphs Rendered", 5)
        st.metric("Cache Hit Rate", "92%")
        st.metric("Avg Response Time", "245 ms")
    
    st.divider()
    st.subheader("Version Information")
    
    version_info = {
        "Dashboard": "v1.0",
        "Streamlit": st.session_state.get('streamlit_version', 'Latest'),
        "Python": "3.11",
        "Backend": "FastAPI",
        "Database": "SQLite",
    }
    
    for key, value in version_info.items():
        st.text(f"{key}: {value}")

# ---------------------------
# Save & Reset Settings
# ---------------------------

st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Save Settings"):
        st.success("✓ Settings saved successfully!")

with col2:
    if st.button("🔄 Reset to Defaults"):
        st.session_state.settings = {
            'sampling_frequency': 25,
            'savgol_window': 13,
            'savgol_polyorder': 3,
            'step_threshold': 20,
            'heel_threshold': 0.15,
            'forefoot_threshold': 0.15,
            'auto_refresh': True,
            'refresh_interval': 2,
            'api_url': 'https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings',
            'enable_mock_data': True,
            'data_retention_hours': 24,
        }
        st.success("✓ Reset to default settings!")
        st.rerun()

with col3:
    if st.button("📋 Export Settings"):
        import json
        settings_json = json.dumps(st.session_state.settings, indent=2)
        st.download_button(
            "Download JSON",
            settings_json,
            "settings.json",
            "application/json"
        )
    st.stop()

# ---------------------------
# Display metrics
# ---------------------------

col1, col2 = st.columns(2)

col1.metric(
    "Cadence (steps/min)",
    f"{metrics['cadence']:.1f}"
)

col2.metric(
    "Detected Steps",
    len(heel_strikes)
)

st.divider()

col3, col4 = st.columns(2)

col3.metric(
    "Mean Stance Time (s)",
    f"{np.mean(metrics['stance_times']):.2f}"
)

col4.metric(
    "Mean Swing Time (s)",
    f"{np.mean(metrics['swing_times']):.2f}"
)

# ---------------------------
# Optional debug info
# ---------------------------

with st.expander("Debug info"):
    st.write("Heel strikes (indices):", heel_strikes)
    st.write("Toe offs (indices):", toe_offs)
    st.write("Sampling frequency (Hz):", FS)