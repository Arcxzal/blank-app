# streamlit_app.py
import os
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# -----------------------
# Configuration / Defaults
# -----------------------
DEFAULT_API = os.getenv("API_URL", "http://localhost:8000/api")
SENSOR_COUNT_PER_FOOT = 5
# Map sensor index (0..4) to a small grid coordinate (row, col) for heatmap
# Customize this mapping to match your physical sensor layout.
SENSOR_TO_GRID = {
    0: (0, 1),  # toe / fore
    1: (0, 2),
    2: (1, 1),  # center
    3: (1, 2),
    4: (2, 1),  # heel
}
GRID_SHAPE = (3, 4)  # rows x cols for plotting (some empty cells allowed)

# -----------------------
# Utilities
# -----------------------
def fetch_readings(api_url: str, limit: int = 1000) -> pd.DataFrame:
    """
    MOCK DATA VERSION.
    Generates synthetic sensor data for two devices:
    - esp32_left
    - esp32_right

    Sensors: 0..4 for each device
    Time range: last 60 seconds sampled at ~20 Hz
    Step events: simulated pulses in certain sensors
    """
    now = pd.Timestamp.utcnow()
    sample_rate = 20  # Hz ≈ 20 samples per second
    total_samples = min(limit, sample_rate * 60)  # 60 seconds of data

    timestamps = [now - pd.Timedelta(seconds=(total_samples - i) / sample_rate)
                  for i in range(total_samples)]

    devices = ["esp32_left", "esp32_right"]
    rows = []

    for device in devices:
        # base signal pattern differs left/right slightly
        base_offset = 20 if device == "esp32_left" else 25

        # create pseudo walking signal
        step_period = 0.6 if device == "esp32_left" else 0.7
        step_wave = np.sin(np.linspace(0, total_samples * (1 / step_period), total_samples))
        step_wave = np.maximum(step_wave, 0)  # only rising part = pressure

        for sensor in range(5):
            # each sensor has slightly different scale
            sensor_gain = 8 + sensor * 3
            signal = base_offset + sensor_gain * step_wave + np.random.normal(0, 1, total_samples)

            for i in range(total_samples):
                rows.append({
                    "created_at": timestamps[i],
                    "device_id": device,
                    "sensor": sensor,
                    "voltage": float(max(0, signal[i]))
                })

    df = pd.DataFrame(rows)
    return df.sort_values("created_at")


    # If we get here, return empty
    return pd.DataFrame(columns=["created_at", "device_id", "sensor", "voltage"])


def pivot_sensors(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot a sensor-level DataFrame into a time-indexed DataFrame where each sensor is a column.
       df: columns [created_at, device_id, sensor, voltage]
       Returns a dict of dataframes keyed by device_id
    """
    if df.empty:
        return {}

    # ensure proper types
    df = df.copy()
    df["sensor"] = df["sensor"].astype(int)
    df["voltage"] = df["voltage"].astype(float)
    devices = {}
    for device, g in df.groupby("device_id"):
        # pivot: index created_at, columns sensor
        try:
            p = g.pivot_table(index="created_at", columns="sensor", values="voltage", aggfunc="mean")
            # sort columns
            p = p.reindex(columns=sorted(p.columns), fill_value=np.nan)
            devices[device] = p
        except Exception:
            # fallback: build from scratch
            devices[device] = pd.DataFrame()
    return devices


def detect_steps_from_series(series: pd.Series,
                              threshold: float,
                              min_interval_s: float = 0.3) -> List[pd.Timestamp]:
    """Detect step events from a single time series (summed pressure per foot).
       Returns list of timestamps where step event occurs (simple rising-edge detection).
       min_interval_s prevents multiple detections very close together.
    """
    if series.dropna().empty:
        return []

    # Ensure series sorted by time and no duplicate index
    s = series.sort_index().interpolate().ffill().bfill()
    times = s.index.to_numpy()
    vals = s.values

    # Detect rising edges: value crosses above threshold and previous is below.
    above = vals > threshold
    # rising edges indices
    rising_idx = np.where(np.logical_and(above, np.concatenate(([False], ~above[:-1]))))[0]

    if rising_idx.size == 0:
        return []

    # Filter by minimum interval
    filtered = []
    last_t = None
    for idx in rising_idx:
        t = times[idx]
        if last_t is None or (t - last_t).astype("timedelta64[ms]") / 1000.0 >= min_interval_s:
            filtered.append(pd.Timestamp(t))
            last_t = pd.Timestamp(t)
    return filtered


def compute_gait_metrics_for_foot(ts_df: pd.DataFrame,
                                  threshold: float) -> Dict:
    """Given a pivoted DataFrame (index=timestamp, columns=sensor_i),
       compute gait metrics for that foot."""
    if ts_df is None or ts_df.empty:
        return {"steps": 0, "cadence": None, "avg_step_time": None,
                "avg_stride_time": None, "stance_swing_ratio": None, "peak_pressure": None}

    # Create a summed pressure signal across sensors as a simple foot-level signal
    summed = ts_df.sum(axis=1)
    # Detect step events
    events = detect_steps_from_series(summed, threshold=threshold, min_interval_s=0.3)
    steps = len(events)

    # Compute step intervals
    if steps < 2:
        avg_step_time = None
        cadence = None
        avg_stride_time = None
    else:
        diffs = np.diff(pd.to_datetime(events).astype(np.int64) / 1e9)  # seconds
        avg_step_time = float(np.mean(diffs))
        cadence = 60.0 / avg_step_time if avg_step_time > 0 else None
        avg_stride_time = avg_step_time * 2

    # stance vs swing: simple occupancy estimate: proportion of samples above threshold
    stance = (summed > threshold).sum()
    swing = (summed <= threshold).sum()
    stance_swing_ratio = float(stance) / float(swing) if swing > 0 else None

    peak_pressure = float(summed.max())

    return {
        "steps": steps,
        "cadence": cadence,
        "avg_step_time": avg_step_time,
        "avg_stride_time": avg_stride_time,
        "stance_swing_ratio": stance_swing_ratio,
        "peak_pressure": peak_pressure,
        "events": events,
        "summed_signal": summed
    }


def build_heatmap_grid(latest_sensor_values: Dict[int, float]) -> np.ndarray:
    """Given mapping sensor_index->value, produce a GRID_SHAPE numpy array for plotting.
       Empty cells will be np.nan so Plotly shows them as blank/low."""
    grid = np.full(GRID_SHAPE, np.nan, dtype=float)
    for sensor_idx, val in latest_sensor_values.items():
        if sensor_idx in SENSOR_TO_GRID:
            r, c = SENSOR_TO_GRID[sensor_idx]
            # guard bounds
            if 0 <= r < GRID_SHAPE[0] and 0 <= c < GRID_SHAPE[1]:
                grid[r, c] = float(val)
    return grid


# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Gait Pressure Dashboard", layout="wide")
st.title("Gait Pressure Dashboard (Left / Right)")

# Sidebar controls
with st.sidebar:
    api_url = st.text_input("API base URL", value=DEFAULT_API)
    limit = st.number_input("Max readings to fetch", min_value=50, max_value=20000, value=2000, step=50)
    time_window_s = st.number_input("Window (seconds) for metrics", min_value=5, max_value=3600, value=60)
    threshold = st.number_input("Step detection threshold", min_value=0.0, value=10.0, step=1.0)
    refresh_button = st.button("Refresh data now")
    st.markdown("---")
    st.write("Notes:")
    st.write("- Threshold depends on your sensor range (calibrate).")
    st.write("- Sensor -> grid mapping in code: SENSOR_TO_GRID.")

# Fetch data
try:
    df_raw = fetch_readings(api_url, limit=int(limit))
except Exception as e:
    st.error(f"Error fetching data from {api_url}: {e}")
    st.stop()

if df_raw.empty:
    st.info("No sensor data available yet.")
    st.stop()

# Pivot to per-device sensor time series
devices_ts = pivot_sensors(df_raw)

# Only consider recent time window for real-time metrics
now = pd.Timestamp.utcnow()
start_time = now - pd.Timedelta(seconds=int(time_window_s))

# Prepare UI layout
left_col, right_col = st.columns((2, 1))

# Determine device ids for left and right (assume naming convention)
device_left = "esp32_left"
device_right = "esp32_right"

# If those exact ids don't exist, pick first two devices found
device_ids = list(devices_ts.keys())
if device_left not in device_ids and device_ids:
    device_left = device_ids[0]
if device_right not in device_ids:
    device_right = device_ids[1] if len(device_ids) > 1 else device_left

# Compute metrics for both feet
metrics = {}
for dev, name in [(device_left, "Left"), (device_right, "Right")]:
    ts_df = devices_ts.get(dev, pd.DataFrame()).copy()
    if not ts_df.empty:
        # trim to window
        ts_recent = ts_df[(ts_df.index >= start_time) & (ts_df.index <= now)]
    else:
        ts_recent = pd.DataFrame()
    metrics[dev] = compute_gait_metrics_for_foot(ts_recent, threshold=threshold)

# -- Left / Right Metrics cards and heatmaps --
with left_col:
    st.header(f"Left foot ({device_left}) metrics")
    left_metrics = metrics.get(device_left, {})
    st.metric("Steps (window)", left_metrics.get("steps", 0))
    st.metric("Cadence (spm)", f"{left_metrics.get('cadence'):.1f}" if left_metrics.get("cadence") else "—")
    st.write(f"Avg step time: {left_metrics.get('avg_step_time'):.2f} s" if left_metrics.get("avg_step_time") else "Avg step time: —")
    st.write(f"Stride time: {left_metrics.get('avg_stride_time'):.2f} s" if left_metrics.get("avg_stride_time") else "Stride time: —")
    st.write(f"Stance/Swing ratio: {left_metrics.get('stance_swing_ratio'):.2f}" if left_metrics.get("stance_swing_ratio") else "Stance/Swing ratio: —")
    st.write(f"Peak pressure: {left_metrics.get('peak_pressure'):.2f}" if left_metrics.get("peak_pressure") else "Peak pressure: —")

    # heatmap: use latest timestamp's sensor values for this device
    left_ts_full = devices_ts.get(device_left, pd.DataFrame())
    if not left_ts_full.empty:
        latest_row = left_ts_full.iloc[-1]
        latest_vals = {int(col): float(latest_row[col]) for col in latest_row.index if not pd.isna(latest_row[col])}
        grid = build_heatmap_grid(latest_vals)
        fig = go.Figure(data=go.Heatmap(
            z=grid,
            x=list(range(grid.shape[1])),
            y=list(range(grid.shape[0])),
            colorbar=dict(title="Pressure"),s
            zmin=np.nanmin(grid) if np.isfinite(np.nanmin(grid)) else 0,
            zmax=np.nanmax(grid) if np.isfinite(np.nanmax(grid)) else 1,
            hovertemplate="row=%{y}, col=%{x}, value=%{z}<extra></extra>"
        ))
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), yaxis_autorange='reversed')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No left-foot sensor data yet.")

with right_col:
    st.header(f"Right foot ({device_right}) metrics")
    right_metrics = metrics.get(device_right, {})
    st.metric("Steps (window)", right_metrics.get("steps", 0))
    st.metric("Cadence (spm)", f"{right_metrics.get('cadence'):.1f}" if right_metrics.get("cadence") else "—")
    st.write(f"Avg step time: {right_metrics.get('avg_step_time'):.2f} s" if right_metrics.get("avg_step_time") else "Avg step time: —")
    st.write(f"Stride time: {right_metrics.get('avg_stride_time'):.2f} s" if right_metrics.get("avg_stride_time") else "Stride time: —")
    st.write(f"Stance/Swing ratio: {right_metrics.get('stance_swing_ratio'):.2f}" if right_metrics.get("stance_swing_ratio") else "Stance/Swing ratio: —")
    st.write(f"Peak pressure: {right_metrics.get('peak_pressure'):.2f}" if right_metrics.get("peak_pressure") else "Peak pressure: —")

    # right heatmap
    right_ts_full = devices_ts.get(device_right, pd.DataFrame())
    if not right_ts_full.empty:
        latest_row = right_ts_full.iloc[-1]
        latest_vals = {int(col): float(latest_row[col]) for col in latest_row.index if not pd.isna(latest_row[col])}
        grid = build_heatmap_grid(latest_vals)
        fig2 = go.Figure(data=go.Heatmap(
            z=grid,
            x=list(range(grid.shape[1])),
            y=list(range(grid.shape[0])),
            colorbar=dict(title="Pressure"),
            zmin=np.nanmin(grid) if np.isfinite(np.nanmin(grid)) else 0,
            zmax=np.nanmax(grid) if np.isfinite(np.nanmax(grid)) else 1,
            hovertemplate="row=%{y}, col=%{x}, value=%{z}<extra></extra>"
        ))
        fig2.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), yaxis_autorange='reversed')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("No right-foot sensor data yet.")

# -- Step event timeline (combined)
st.subheader("Step event timeline (last window)")

# gather events
timeline_rows = []
for dev in [device_left, device_right]:
    evs = metrics.get(dev, {}).get("events", [])
    summed = metrics.get(dev, {}).get("summed_signal", pd.Series(dtype=float))
    for t in evs:
        timeline_rows.append({"t": t, "device": dev, "pressure": float(summed.get(t, np.nan)) if not summed.empty and t in summed.index else np.nan})

if timeline_rows:
    tdf = pd.DataFrame(timeline_rows)
    tdf = tdf.sort_values("t")
    fig_t = go.Figure()
    # show summed signals as background lines (if available)
    for dev in [device_left, device_right]:
        summed = metrics.get(dev, {}).get("summed_signal", pd.Series(dtype=float))
        if not summed.empty:
            fig_t.add_trace(go.Scatter(x=summed.index, y=summed.values, mode="lines", name=f"{dev} summed", opacity=0.3))
    # add event markers
    colors = {device_left: "blue", device_right: "red"}
    for dev in tdf["device"].unique():
        sub = tdf[tdf["device"] == dev]
        fig_t.add_trace(go.Scatter(x=sub["t"], y=sub["pressure"], mode="markers", name=f"{dev} steps",
                                   marker=dict(size=8, color=colors.get(dev, "black"))))
    fig_t.update_layout(xaxis_title="Time", yaxis_title="Pressure", height=300, margin=dict(t=10, b=30))
    st.plotly_chart(fig_t, use_container_width=True)
else:
    st.write("No step events detected in the selected window.")

# -- Raw recent data table (optional)
st.subheader("Recent raw sensor samples (per-device)")
for dev in [device_left, device_right]:
    st.write(f"Device: {dev}")
    df_dev = devices_ts.get(dev, pd.DataFrame()).sort_index(ascending=False)
    if df_dev.empty:
        st.write("No data")
    else:
        st.dataframe(df_dev.head(50))

# Refresh behavior: simple button-driven refresh (user clicks Refresh)
if refresh_button:
    st.experimental_rerun()
