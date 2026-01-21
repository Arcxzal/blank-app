# dashboard.py

import time
import requests
import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.signal import savgol_filter
from patient_utils import load_patient_data, is_demo_patient, get_patient_display_name

# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

CLOUD_DATA_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings"  # Replace with real endpoint
REFRESH_INTERVAL_SECONDS = 2  # Increased to reduce flickering
STEP_THRESHOLD = 20   # Threshold for single foot pressure to detect step
FS = 25  # sampling frequency (Hz)


# ---------------------------------------------------
# Data Loading
# ---------------------------------------------------

@st.cache_data(ttl=2)
def load_data_from_api() -> pd.DataFrame:
    response = requests.get(CLOUD_DATA_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # Flatten nested JSON structure with individual pressure points
    records = []
    for entry in data:
        timestamp = entry.get("timestamp")
        if not timestamp:
            continue
            
        pressures = entry.get("pressures", {})
        record = {
            "timestamp": timestamp,
            # Right foot
            "bigToe": pressures.get("bigToe", 0),
            "pinkyToe": pressures.get("pinkyToe", 0),
            "metaOut": pressures.get("metaOut", 0),
            "metaIn": pressures.get("metaIn", 0),
            "heel": pressures.get("heel", 0),
            # Left foot
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
    from datetime import datetime
    start_date = datetime.now() - pd.Timedelta(hours=1)  # Start from 1 hour ago
    rng = pd.date_range(start_date, periods=300, freq="10s")
    
    # Generate mock data for all 5 pressure points on both feet
    df = pd.DataFrame({
        "timestamp": rng,
        # Right foot
        "bigToe": np.abs(np.sin(np.linspace(0, 30, len(rng))) * 40 + np.random.randn(len(rng)) * 3),
        "pinkyToe": np.abs(np.sin(np.linspace(0, 25, len(rng))) * 35 + np.random.randn(len(rng)) * 3),
        "metaOut": np.abs(np.sin(np.linspace(0, 28, len(rng))) * 38 + np.random.randn(len(rng)) * 3),
        "metaIn": np.abs(np.sin(np.linspace(0, 26, len(rng))) * 36 + np.random.randn(len(rng)) * 3),
        "heel": np.abs(np.sin(np.linspace(0, 32, len(rng))) * 45 + np.random.randn(len(rng)) * 3),
        # Left foot
        "bigToe_L": np.abs(np.sin(np.linspace(0, 30, len(rng)) + 0.5) * 40 + np.random.randn(len(rng)) * 3),
        "pinkyToe_L": np.abs(np.sin(np.linspace(0, 25, len(rng)) + 0.5) * 35 + np.random.randn(len(rng)) * 3),
        "metaOut_L": np.abs(np.sin(np.linspace(0, 28, len(rng)) + 0.5) * 38 + np.random.randn(len(rng)) * 3),
        "metaIn_L": np.abs(np.sin(np.linspace(0, 26, len(rng)) + 0.5) * 36 + np.random.randn(len(rng)) * 3),
        "heel_L": np.abs(np.sin(np.linspace(0, 32, len(rng)) + 0.5) * 45 + np.random.randn(len(rng)) * 3),
    })
    return df



# ---------------------------------------------------
# Signal Processing
# ---------------------------------------------------

def savgol_filter_signal(signal, fs=FS):
    """
    Apply Savitzky–Golay filter to one sensor channel.
    Window length is ~2.0 s with lower polyorder for very smooth, sine-wave-like curves.
    """
    signal = np.asarray(signal)

    # Return original signal if too short
    if len(signal) < 5:
        return signal

    window_length = int(2.0 * fs)  # ~2.0 s for very smooth curves
    if window_length % 2 == 0:
        window_length += 1

    # Ensure window is smaller than signal
    if window_length >= len(signal):
        window_length = len(signal) - 1
        if window_length % 2 == 0:
            window_length -= 1
        # Minimum valid window
        window_length = max(5, window_length)

    # Use polyorder=2 for smoother curves (lower order = smoother)
    polyorder = min(2, window_length - 1)
    return savgol_filter(signal, window_length=window_length, polyorder=polyorder)


def preprocess_signals(df):
    """
    Apply Savitzky–Golay filter to all pressure sensor signals.
    Returns a new DataFrame with filtered signals.
    Clips negative values to zero (pressure can't be negative).
    """
    filtered = df.copy()

    sensor_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel',
                   'bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
    
    for col in sensor_cols:
        if col in filtered.columns:
            filtered[col] = savgol_filter_signal(filtered[col].values)
            # Clip to non-negative (filter can produce small negative values)
            filtered[col] = np.maximum(filtered[col], 0)

    return filtered


# ---------------------------------------------------
# Plotting
# ---------------------------------------------------

def detect_available_sensors(df):
    """
    Detect which sensors have actual data (non-zero values).
    Returns a dict with available sensors for each foot.
    """
    pressure_points = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    available = {'right': [], 'left': []}
    
    for point in pressure_points:
        # Check right foot
        if point in df.columns and df[point].sum() > 0:
            available['right'].append(point)
        # Check left foot
        col_left = f"{point}_L"
        if col_left in df.columns and df[col_left].sum() > 0:
            available['left'].append(point)
    
    return available


def create_pressure_comparison_chart(df_filtered, pressure_point, has_left_foot=True):
    """
    Create a chart for a specific pressure point.
    Shows both feet if available, otherwise just right foot.
    Works with empty data and displays empty graphs.
    
    Args:
        df_filtered: DataFrame with filtered pressure data (can be empty)
        pressure_point: 'bigToe', 'pinkyToe', 'metaOut', 'metaIn', or 'heel'
        has_left_foot: Whether left foot data is available
    """
    col_right = pressure_point
    col_left = f"{pressure_point}_L"
    
    # Check if right foot column exists
    if col_right not in df_filtered.columns:
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Handle empty data
    if df_filtered.empty:
        # Create empty traces with proper labels
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines',
            name='Right Foot',
            line=dict(color='#0072B2', width=2),
            opacity=0.8
        ))
        
        if has_left_foot and col_left in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=[],
                y=[],
                mode='lines',
                name='Left Foot',
                line=dict(color='#E69F00', width=2),
                opacity=0.8
            ))
            title_suffix = "- Left vs Right Foot"
        else:
            title_suffix = "- Right Foot Only"
        
        fig.update_layout(
            title=f"{pressure_point.upper()} Pressure {title_suffix}",
            xaxis_title="Time (seconds)",
            yaxis_title="Pressure (units)",
            hovermode='x unified',
            height=400,
            showlegend=True,
            legend=dict(x=0.02, y=0.98),
            margin=dict(l=50, r=50, t=50, b=50),
            annotations=[dict(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="#999")
            )]
        )
        return fig
    
    # Ensure timestamp is in the dataframe
    if 'timestamp' not in df_filtered.columns:
        return None
    
    # Convert timestamp to seconds since start for better x-axis
    try:
        time_seconds = (df_filtered['timestamp'] - df_filtered['timestamp'].iloc[0]).dt.total_seconds()
    except Exception:
        return None
    
    # Add right foot trend line
    fig.add_trace(go.Scatter(
        x=time_seconds,
        y=df_filtered[col_right],
        mode='lines',
        name='Right Foot',
        line=dict(color='#0072B2', width=2),  # Blue
        opacity=0.8
    ))
    
    # Add left foot trend line only if available and column exists
    if has_left_foot and col_left in df_filtered.columns:
        fig.add_trace(go.Scatter(
            x=time_seconds,
            y=df_filtered[col_left],
            mode='lines',
            name='Left Foot',
            line=dict(color='#E69F00', width=2),  # Orange
            opacity=0.8
        ))
        title_suffix = "- Left vs Right Foot"
    else:
        title_suffix = "- Right Foot Only"
    
    # Update layout with optimizations
    fig.update_layout(
        title=f"{pressure_point.upper()} Pressure {title_suffix}",
        xaxis_title="Time (seconds)",
        yaxis_title="Pressure (units)",
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(x=0.02, y=0.98),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig
    
    # Add right foot trend line
    fig.add_trace(go.Scatter(
        x=time_seconds,
        y=df_filtered[col_right],
        mode='lines',
        name='Right Foot',
        line=dict(color='#0072B2', width=2),  # Blue
        opacity=0.8
    ))
    
    # Add left foot trend line only if available and column exists
    if has_left_foot and col_left in df_filtered.columns:
        fig.add_trace(go.Scatter(
            x=time_seconds,
            y=df_filtered[col_left],
            mode='lines',
            name='Left Foot',
            line=dict(color='#E69F00', width=2),  # Orange
            opacity=0.8
        ))
        title_suffix = "- Left vs Right Foot"
    else:
        title_suffix = "- Right Foot Only"
    
    # Update layout with optimizations
    fig.update_layout(
        title=f"{pressure_point.upper()} Pressure {title_suffix}",
        xaxis_title="Time (seconds)",
        yaxis_title="Pressure (units)",
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(x=0.02, y=0.98),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig

# ---------------------------------------------------
# Gait Parameter Extraction
# ---------------------------------------------------

def compute_gait_parameters(df: pd.DataFrame) -> dict:
    """Compute basic gait parameters from total pressure"""
    # Compute right foot pressure only for step detection (more accurate)
    right_foot_pressure = (df['bigToe'] + df['pinkyToe'] + df['metaOut'] + 
                          df['metaIn'] + df['heel'])
    
    if right_foot_pressure.empty or right_foot_pressure.max() == 0:
        return {
            "steps": 0,
            "cadence": 0,
            "avg_step_time": None,
            "avg_stride_time": None,
            "gait_symmetry": None,
            "stance_swing_ratio": None
        }

    values = right_foot_pressure.values
    timestamps = df['timestamp'].values
    
    st.write(f"🔍 DEBUG: Right foot pressure - Min: {values.min():.2f}, Max: {values.max():.2f}, Samples: {len(values)}")
    st.write(f"🔍 DEBUG: Threshold: {STEP_THRESHOLD}")

    # Step detection: find peaks with minimum distance
    # At 25 Hz and typical cadence ~120 steps/min (2 Hz), minimum distance should be ~12 samples
    from scipy.signal import find_peaks
    
    # Find peaks in right foot pressure
    # height: minimum peak height (above threshold)
    # distance: minimum samples between peaks (0.5 sec at 25 Hz = 12 samples)
    # prominence: how much peak stands out from surrounding baseline
    peaks, properties = find_peaks(
        values, 
        height=STEP_THRESHOLD,
        distance=10,  # ~0.4 seconds minimum between steps
        prominence=10  # peak must be at least 10 units above surrounding
    )
    
    st.write(f"🔍 DEBUG: Peaks detected: {len(peaks)} (using peak detection with distance=10, prominence=10)")

    st.write(f"🔍 DEBUG: Peaks detected: {len(peaks)} (using peak detection with distance=10, prominence=10)")

    if len(peaks) < 2:
        st.warning(f"⚠️ Not enough steps detected: {len(peaks)} (need at least 2)")
        # Fallback: just count continuous regions above threshold
        step_indices = np.where(values > STEP_THRESHOLD)[0]
        # Calculate total pressure for symmetry
        total_pressure = (df['bigToe'] + df['pinkyToe'] + df['metaOut'] + 
                         df['metaIn'] + df['heel'] + 
                         df['bigToe_L'] + df['pinkyToe_L'] + df['metaOut_L'] + 
                         df['metaIn_L'] + df['heel_L'])
        return {"steps": len(step_indices) if len(step_indices) > 0 else 0, 
                "cadence": None,
                "avg_step_time": None, 
                "avg_stride_time": None,
                "gait_symmetry": max(0, 100 - abs(np.std(total_pressure.values))), 
                "stance_swing_ratio": np.sum(values > STEP_THRESHOLD) / max(1, np.sum(values <= STEP_THRESHOLD))}

    step_times = timestamps[peaks]

    # Convert to pandas Timedelta for proper calculation
    step_times_pd = pd.to_datetime(step_times)
    diffs = np.diff(step_times_pd.values).astype('timedelta64[s]').astype(float)
    avg_step_time = float(np.mean(diffs))

    # Stride time = 2 × step time
    avg_stride_time = avg_step_time * 2

    # Cadence (steps per minute)
    cadence = 60 / avg_step_time if avg_step_time > 0 else 0

    # Gait symmetry metric
    gait_symmetry = max(0, 100 - abs(np.std(values)))

    # Stance vs Swing
    stance = np.sum(values > STEP_THRESHOLD)
    swing = np.sum(values <= STEP_THRESHOLD)
    stance_swing_ratio = stance / max(1, swing)

    return {
        "steps": len(peaks),
        "cadence": cadence,
        "avg_step_time": avg_step_time,
        "avg_stride_time": avg_stride_time,
        "gait_symmetry": gait_symmetry,
        "stance_swing_ratio": stance_swing_ratio
    }


# ---------------------------------------------------
# Main Streamlit App
# ---------------------------------------------------

def main():
    # Get selected patient info
    patient_name = get_patient_display_name()
    is_demo = is_demo_patient()
    patient_id = st.session_state.get('selected_patient_id', 'demo')
    
    st.set_page_config(
        page_title="Pressure Analysis Dashboard",
        layout="wide",
    )

    st.title("📊 Pressure Analysis Dashboard")
    
    st.write(f"🔍 DEBUG: Selected patient ID: `{patient_id}`, Is demo: {is_demo}")
    
    patient_badge = "🎭 Demo Patient" if is_demo else f"📡 {patient_name}"
    st.caption(f"Viewing data for: **{patient_badge}**")
    st.write("This dashboard shows filtered pressure readings with left vs right foot comparison.")

    # Sidebar
    st.sidebar.header("Settings")
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)

    time_filter = st.sidebar.selectbox(
        "Time range",
        ["All data", "Last 1 hour", "Last 24 hours", "Last 7 days"]
    )

    # Load data using helper function
    try:
        df = load_patient_data(num_cycles=20, cadence=115)
        st.write(f"📊 Data loaded: {len(df)} samples")
        if not df.empty:
            st.write(f"📅 Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        # Create empty DataFrame so graphs still show
        df = pd.DataFrame({
            "timestamp": [],
            "bigToe": [], "pinkyToe": [], "metaOut": [], "metaIn": [], "heel": [],
            "bigToe_L": [], "pinkyToe_L": [], "metaOut_L": [], "metaIn_L": [], "heel_L": []
        })

    # Check if data is empty and create placeholder if needed
    has_data = not df.empty
    
    if not has_data:
        st.warning("⚠️ No data available yet. Showing empty graphs. Please check your data source or enable mock data.")
        # Create empty DataFrame with proper structure
        df = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-14", periods=0),
            "bigToe": [], "pinkyToe": [], "metaOut": [], "metaIn": [], "heel": [],
            "bigToe_L": [], "pinkyToe_L": [], "metaOut_L": [], "metaIn_L": [], "heel_L": []
        })

    df = df.sort_values("timestamp")

    # Time filtering
    if not df.empty and time_filter != "All data":
        max_ts = df["timestamp"].max()
        if time_filter == "Last 1 hour":
            df = df[df["timestamp"] >= max_ts - pd.Timedelta(hours=1)]
        elif time_filter == "Last 24 hours":
            df = df[df["timestamp"] >= max_ts - pd.Timedelta(hours=24)]
        elif time_filter == "Last 7 days":
            df = df[df["timestamp"] >= max_ts - pd.Timedelta(days=7)]

    # Only check for empty after filtering if we had data before
    if df.empty and has_data:
        st.warning("No data available in the selected time range.")
        # Still show empty graphs instead of stopping

    # Apply Savitzky-Golay filtering
    df_filtered = preprocess_signals(df)

    # Detect available sensors
    available_sensors = detect_available_sensors(df_filtered)
    # If no data at all, assume both feet are available
    if not df_filtered.empty:
        has_left_foot = len(available_sensors['left']) > 0
    else:
        # For empty data (new patient), show both feet by default
        has_left_foot = True

    # ---------------------------
    # Display Sensor Availability
    # ---------------------------
    with st.expander("📊 Available Sensors", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Right Foot:**")
            if available_sensors['right']:
                for sensor in available_sensors['right']:
                    st.write(f"✓ {sensor.upper()}")
            else:
                st.write("⚠ No sensors detected")
        
        with col2:
            st.write("**Left Foot:**")
            if available_sensors['left']:
                for sensor in available_sensors['left']:
                    st.write(f"✓ {sensor.upper()}")
            else:
                st.write("⚠ No sensors detected (right foot only)")

    # ---------------------------
    # Display 5 Pressure Point Graphs
    # ---------------------------
    st.header("Pressure Point Analysis (Filtered)")
    if has_left_foot:
        st.write("Each graph shows the cleaned pressure readings with Savitzky-Golay filter, comparing left and right foot.")
    else:
        st.write("Each graph shows the cleaned pressure readings with Savitzky-Golay filter for the right foot.")

    pressure_points = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    
    # Create two rows of graphs (3 on top, 2 on bottom)
    for i, pressure_point in enumerate(pressure_points):
        if i % 3 == 0:
            cols = st.columns(3)
        
        with cols[i % 3]:
            try:
                fig = create_pressure_comparison_chart(df_filtered, pressure_point, has_left_foot)
                if fig is not None:
                    st.plotly_chart(fig)
                else:
                    st.warning(f"No data available for {pressure_point}")
            except Exception as e:
                st.error(f"Error creating chart for {pressure_point}: {e}")

    # ---------------------------
    # Statistics Section
    # ---------------------------
    st.header("Summary Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Right Foot")
        for pressure_point in pressure_points:
            col = pressure_point
            if col in df_filtered.columns:
                mean_val = df_filtered[col].mean()
                max_val = df_filtered[col].max()
                st.metric(
                    pressure_point.upper(),
                    f"Mean: {mean_val:.1f} | Max: {max_val:.1f}"
                )
    
    with col2:
        st.subheader("Left Foot")
        for pressure_point in pressure_points:
            col = f"{pressure_point}_L"
            if col in df_filtered.columns:
                mean_val = df_filtered[col].mean()
                max_val = df_filtered[col].max()
                st.metric(
                    pressure_point.upper(),
                    f"Mean: {mean_val:.1f} | Max: {max_val:.1f}"
                )

    # ---------------------------
    # Gait Parameters
    # ---------------------------
    st.header("Gait Parameters")
    gait = compute_gait_parameters(df_filtered)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Steps", gait['steps'])
        st.metric("Cadence", f"{gait['cadence']:.1f} steps/min" if gait['cadence'] else "—")
    
    with col2:
        st.metric("Step Time", f"{gait['avg_step_time']:.2f} sec" if gait['avg_step_time'] else "—")
        st.metric("Stride Time", f"{gait['avg_stride_time']:.2f} sec" if gait['avg_stride_time'] else "—")
    
    with col3:
        st.metric("Gait Symmetry", f"{gait['gait_symmetry']:.1f}%" if gait['gait_symmetry'] else "—")
        st.metric("Stance/Swing Ratio", f"{gait['stance_swing_ratio']:.2f}" if gait['stance_swing_ratio'] else "—")

    # Auto-refresh
    if auto_refresh:
        st.caption(f"Auto-refreshing every {REFRESH_INTERVAL_SECONDS} seconds.")
        time.sleep(REFRESH_INTERVAL_SECONDS)
        st.rerun()


if __name__ == "__main__":
    main()
