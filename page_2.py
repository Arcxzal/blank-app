# dashboard.py

import time
import requests
import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.signal import savgol_filter
from patient_utils import load_patient_data, is_demo_patient, get_patient_display_name
import pytz

# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

CLOUD_DATA_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings"  # Replace with real endpoint
REFRESH_INTERVAL_SECONDS = 2  # Increased to reduce flickering
STEP_THRESHOLD = 1   # Trigger step detection on any non-zero reading
FS = 25  # sampling frequency (Hz)


# ---------------------------------------------------
# Data Loading with Persistence
# ---------------------------------------------------

def initialize_session_state():
    """Initialize session state for data persistence across reruns"""
    if 'accumulated_data' not in st.session_state:
        st.session_state.accumulated_data = pd.DataFrame()
    if 'last_api_timestamp' not in st.session_state:
        st.session_state.last_api_timestamp = None


@st.cache_data(ttl=2)
def load_data_from_api(patient_id=None, limit=500) -> pd.DataFrame:
    """Load data from API with optional patient filtering"""
    params = {"limit": limit}
    if patient_id and patient_id != "demo":
        params["patient_id"] = patient_id
    
    response = requests.get(CLOUD_DATA_URL, params=params, timeout=10)
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
    # Keep UTC timezone - matches ESP32 NTP timestamps from backend
    df = df.sort_values("timestamp")
    return df


def merge_new_data_with_history(patient_id=None) -> pd.DataFrame:
    """
    Merge fresh API data with historical data stored in session state.
    Intelligently combines left and right foot readings from two ESP32s by timestamp.
    
    Returns the accumulated dataset with duplicates removed and left/right data merged.
    """
    initialize_session_state()
    
    # Get fresh data from API
    try:
        fresh_data = load_data_from_api(patient_id=patient_id)
    except Exception:
        fresh_data = pd.DataFrame()
    
    # If no fresh data, return accumulated data
    if fresh_data.empty:
        return st.session_state.accumulated_data.copy() if not st.session_state.accumulated_data.empty else pd.DataFrame()
    
    # Combine fresh data with accumulated data
    if st.session_state.accumulated_data.empty:
        combined = fresh_data.copy()
    else:
        combined = pd.concat([st.session_state.accumulated_data, fresh_data], ignore_index=True)
    
    # Remove duplicates based on timestamp (keep first occurrence)
    combined = combined.drop_duplicates(subset=['timestamp'], keep='first')
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    
    # Merge left and right foot data by matching timestamps (within 1 second tolerance)
    # This handles the case where two ESP32s send data at slightly different times
    combined = merge_left_right_foot_data(combined)
    
    # Store back in session state for next rerun
    st.session_state.accumulated_data = combined.copy()
    
    return combined


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
            for other_idx in range(idx + 1, min(idx + 10, len(df))):  # Check next 10 rows
                if other_idx in used_indices:
                    continue
                other_row = df.iloc[other_idx]
                time_diff = abs((other_row['timestamp'] - current_ts).total_seconds())
                
                # If timestamps are within 1 second, merge them
                if time_diff <= 1.0:
                    other_right = (other_row['bigToe'] > 0 or other_row['pinkyToe'] > 0 or 
                                  other_row['metaOut'] > 0 or other_row['metaIn'] > 0 or other_row['heel'] > 0)
                    other_left = (other_row['bigToe_L'] > 0 or other_row['pinkyToe_L'] > 0 or 
                                 other_row['metaOut_L'] > 0 or other_row['metaIn_L'] > 0 or other_row['heel_L'] > 0)
                    
                    # If other row has left data and current has right, merge them
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


def load_mock_data() -> pd.DataFrame:
    from datetime import datetime
    import pytz
    start_date = datetime.now(pytz.UTC) - pd.Timedelta(hours=1)  # Start from 1 hour ago (UTC)
    rng = pd.date_range(start_date, periods=300, freq="10s", tz='UTC')
    
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

def compute_existing_gait_metrics(df: pd.DataFrame, step_count_total: int, step_count_left: int, step_count_right: int) -> dict:
    """
    Compute gait metrics (cadence, timing, symmetry) from the dataframe
    using the provided step count (instead of recalculating steps).
    """
    if df.empty:
        return {
            "steps_total": step_count_total,
            "steps_left": step_count_left,
            "steps_right": step_count_right,
            "cadence": 0,
            "avg_step_time": None,
            "avg_stride_time": None,
            "gait_symmetry": None,
            "stance_swing_ratio": None
        }
    
    # Calculate timing metrics using ALL data
    total_pressure = (df['bigToe'] + df['pinkyToe'] + df['metaOut'] + 
                     df['metaIn'] + df['heel'] +
                     df['bigToe_L'] + df['pinkyToe_L'] + df['metaOut_L'] +
                     df['metaIn_L'] + df['heel_L'])
    
    if total_pressure.max() == 0:
        return {
            "steps_total": step_count_total,
            "steps_left": step_count_left,
            "steps_right": step_count_right,
            "cadence": 0,
            "avg_step_time": None,
            "avg_stride_time": None,
            "gait_symmetry": None,
            "stance_swing_ratio": None
        }
    
    values = total_pressure.values
    timestamps = df['timestamp'].values
    
    # Estimate cadence from total time and step count
    if len(timestamps) > 1 and step_count_total > 0:
        # Convert numpy.timedelta64 to seconds
        delta = timestamps[-1] - timestamps[0]
        duration_sec = pd.Timedelta(delta).total_seconds()
        if duration_sec > 0:
            cadence = (step_count_total / duration_sec) * 60
        else:
            cadence = 0
    else:
        cadence = 0
    
    # Estimate average step/stride times
    if step_count_total > 1 and len(timestamps) > 1:
        # Convert numpy.timedelta64 to seconds
        delta = timestamps[-1] - timestamps[0]
        total_time = pd.Timedelta(delta).total_seconds()
        avg_step_time = total_time / step_count_total
        avg_stride_time = avg_step_time * 2
    else:
        avg_step_time = None
        avg_stride_time = None
    
    # Calculate symmetry and stance/swing ratio
    total_pressure = (df['bigToe'] + df['pinkyToe'] + df['metaOut'] + 
                     df['metaIn'] + df['heel'] + 
                     df['bigToe_L'] + df['pinkyToe_L'] + df['metaOut_L'] + 
                     df['metaIn_L'] + df['heel_L'])
    
    gait_symmetry = max(0, 100 - abs(np.std(total_pressure.values)))
    stance_swing_ratio = np.sum(values > STEP_THRESHOLD) / max(1, np.sum(values <= STEP_THRESHOLD))
    
    return {
        "steps_total": step_count_total,
        "steps_left": step_count_left,
        "steps_right": step_count_right,
        "cadence": cadence,
        "avg_step_time": avg_step_time,
        "avg_stride_time": avg_stride_time,
        "gait_symmetry": gait_symmetry,
        "stance_swing_ratio": stance_swing_ratio
    }


def compute_gait_parameters(df: pd.DataFrame) -> dict:
    """
    Compute basic gait parameters from total pressure with INCREMENTAL step counting.
    
    Key Fix: Steps are counted ONCE and never recalculated. Uses Streamlit session state
    to track which data has already been analyzed, preventing step count from going backward.
    """
    # Initialize session state for persistent step counter
    if 'last_processed_index' not in st.session_state:
        st.session_state.last_processed_index = -1
    if 'cumulative_steps_left' not in st.session_state:
        st.session_state.cumulative_steps_left = 0
    if 'cumulative_steps_right' not in st.session_state:
        st.session_state.cumulative_steps_right = 0
    if 'last_detected_peaks' not in st.session_state:
        st.session_state.last_detected_peaks = []
    
    # Compute pressure per foot for step detection
    right_foot_pressure = (df['bigToe'] + df['pinkyToe'] + df['metaOut'] + 
                          df['metaIn'] + df['heel'])
    left_foot_pressure = (df['bigToe_L'] + df['pinkyToe_L'] + df['metaOut_L'] + 
                         df['metaIn_L'] + df['heel_L'])
    
    total_pressure = right_foot_pressure + left_foot_pressure
    
    if total_pressure.empty or total_pressure.max() == 0:
        return {
            "steps_total": st.session_state.cumulative_steps_left + st.session_state.cumulative_steps_right,
            "steps_left": st.session_state.cumulative_steps_left,
            "steps_right": st.session_state.cumulative_steps_right,
            "cadence": 0,
            "avg_step_time": None,
            "avg_stride_time": None,
            "gait_symmetry": None,
            "stance_swing_ratio": None
        }

    right_values = right_foot_pressure.values
    left_values = left_foot_pressure.values
    timestamps = df['timestamp'].values
    
    show_debug = st.session_state.get("show_debug", False)
    if show_debug:
        st.write(f"🔍 DEBUG: Right foot pressure - Min: {right_values.min():.2f}, Max: {right_values.max():.2f}, Samples: {len(right_values)}")
        st.write(f"🔍 DEBUG: Left foot pressure - Min: {left_values.min():.2f}, Max: {left_values.max():.2f}, Samples: {len(left_values)}")
        st.write(f"🔍 DEBUG: Threshold: {STEP_THRESHOLD}")
        st.write(
            f"🔍 DEBUG: Last processed index: {st.session_state.last_processed_index}, "
            f"Left steps: {st.session_state.cumulative_steps_left}, Right steps: {st.session_state.cumulative_steps_right}"
        )

    # Step detection: find peaks with minimum distance
    # At 25 Hz and typical cadence ~120 steps/min (2 Hz), minimum distance should be ~12 samples
    from scipy.signal import find_peaks
    
    # INCREMENTAL: Only analyze NEW data since last processing
    start_idx = st.session_state.last_processed_index + 1
    
    if start_idx >= len(right_values):
        # No new data to process, return cumulative count
        if show_debug:
            st.write(f"🔍 DEBUG: No new data (start_idx={start_idx} >= len={len(right_values)})")
        return compute_existing_gait_metrics(
            df,
            st.session_state.cumulative_steps_left + st.session_state.cumulative_steps_right,
            st.session_state.cumulative_steps_left,
            st.session_state.cumulative_steps_right
        )
    
    # Analyze only NEW data, but include some overlap for peak detection to work correctly
    # Use last 50% of old data + all new data for better edge detection
    overlap_idx = max(0, st.session_state.last_processed_index - int(len(right_values) * 0.25))
    analysis_right_values = right_values[overlap_idx:]
    analysis_left_values = left_values[overlap_idx:]
    analysis_timestamps = timestamps[overlap_idx:]
    
    if show_debug:
        st.write(f"🔍 DEBUG: Analyzing from index {overlap_idx} to {len(right_values)-1} ({len(analysis_right_values)} new samples)")
    
    # Find peaks in the NEW portion of right foot pressure
    # ADJUSTED: More sensitive parameters for better step detection
    peaks_right, _ = find_peaks(
        analysis_right_values, 
        height=STEP_THRESHOLD,
        distance=6,  # ~0.24 seconds minimum between steps (more sensitive)
        prominence=5  # Lower prominence for gentler steps (was 10)
    )
    peaks_left, _ = find_peaks(
        analysis_left_values,
        height=STEP_THRESHOLD,
        distance=6,
        prominence=5
    )
    
    # Convert back to original indices
    peaks_right_idx = peaks_right + overlap_idx
    peaks_left_idx = peaks_left + overlap_idx
    
    # Filter: Only count peaks that are AFTER the last processed index
    new_right_peaks = peaks_right_idx[peaks_right_idx > st.session_state.last_processed_index]
    new_left_peaks = peaks_left_idx[peaks_left_idx > st.session_state.last_processed_index]
    
    if show_debug:
        st.write(
            f"🔍 DEBUG: New peaks detected - Right: {len(new_right_peaks)} (all: {len(peaks_right)}), "
            f"Left: {len(new_left_peaks)} (all: {len(peaks_left)})"
        )
    
    # UPDATE CUMULATIVE STEP COUNTER WITH NEW PEAKS
    st.session_state.cumulative_steps_right += len(new_right_peaks)
    st.session_state.cumulative_steps_left += len(new_left_peaks)
    st.session_state.last_processed_index = len(right_values) - 1  # Mark all data as processed
    
    if show_debug:
        st.write(
            f"🔍 DEBUG: Updated cumulative steps - Right: {st.session_state.cumulative_steps_right}, "
            f"Left: {st.session_state.cumulative_steps_left}"
        )
    
    # If no peaks detected in new data, just return existing metrics
    if len(new_right_peaks) == 0 and len(new_left_peaks) == 0:
        return compute_existing_gait_metrics(
            df,
            st.session_state.cumulative_steps_left + st.session_state.cumulative_steps_right,
            st.session_state.cumulative_steps_left,
            st.session_state.cumulative_steps_right
        )
    
    # Compute timing metrics using the new peaks
    total_steps = st.session_state.cumulative_steps_left + st.session_state.cumulative_steps_right
    
    # For overall cadence calculation, use ALL peaks ever detected (not just new ones)
    # Estimate from total time and cumulative steps
    if len(timestamps) > 1 and total_steps > 0:
        # Convert numpy.timedelta64 to seconds
        delta = timestamps[-1] - timestamps[0]
        duration_sec = pd.Timedelta(delta).total_seconds()
        if duration_sec > 0:
            cadence = (total_steps / duration_sec) * 60
        else:
            cadence = 0
    else:
        cadence = 0
    
    # Estimate average step time from new peaks
    if total_steps > 1 and len(timestamps) > 1:
        delta = timestamps[-1] - timestamps[0]
        total_time = pd.Timedelta(delta).total_seconds()
        avg_step_time = total_time / total_steps
        avg_stride_time = avg_step_time * 2
    else:
        avg_step_time = None
        avg_stride_time = None
    
    # Gait symmetry metric (compute from entire dataset)
    gait_symmetry = max(0, 100 - abs(np.std(total_pressure.values)))

    # Stance vs Swing
    stance = np.sum(total_pressure.values > STEP_THRESHOLD)
    swing = np.sum(total_pressure.values <= STEP_THRESHOLD)
    stance_swing_ratio = stance / max(1, swing)

    return {
        "steps_total": total_steps,
        "steps_left": st.session_state.cumulative_steps_left,
        "steps_right": st.session_state.cumulative_steps_right,
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
    st.session_state.show_debug = st.sidebar.checkbox("Show debug info", value=False)
    
    # Add reset button for step counter
    if st.sidebar.button("🔄 Reset Step Counter"):
        st.session_state.last_processed_index = -1
        st.session_state.cumulative_steps_left = 0
        st.session_state.cumulative_steps_right = 0
        st.session_state.accumulated_data = pd.DataFrame()
        st.success("✅ Step counter reset!")
        st.rerun()

    time_filter = st.sidebar.selectbox(
        "Time range",
        ["All data", "Last 1 hour", "Last 24 hours", "Last 7 days"]
    )

    # Load data using helper function
    try:
        # Get current patient ID from session state
        patient_id = st.session_state.get('selected_patient_id', 1)
        
        # Use patient data loading which includes API calls with data merging
        df = merge_new_data_with_history(patient_id=patient_id)
        st.write(f"📊 Data loaded: {len(df)} samples (accumulated)")
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
        st.metric("Total Steps", gait['steps_total'])
        st.metric("Left Steps", gait['steps_left'])
        st.metric("Right Steps", gait['steps_right'])
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
