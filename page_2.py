# dashboard.py

import time
import requests
import pandas as pd
import streamlit as st
import numpy as np

# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

CLOUD_DATA_URL = "https://example.com/api/data"  # Replace with real endpoint
REFRESH_INTERVAL_SECONDS = 30
STEP_THRESHOLD = 20   # adjust for ESP32 pressure range


# ---------------------------------------------------
# Data Loading
# ---------------------------------------------------

def load_data_from_api() -> pd.DataFrame:
    response = requests.get(CLOUD_DATA_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    return df


def load_mock_data() -> pd.DataFrame:
    rng = pd.date_range("2025-11-01", periods=300, freq="10S")
    vals = np.abs(np.sin(np.linspace(0, 30, len(rng))) * 40 + np.random.randn(len(rng)) * 3)

    df = pd.DataFrame({
        "timestamp": rng,
        "value": vals
    })
    return df


# ---------------------------------------------------
# Gait Parameter Extraction
# ---------------------------------------------------

def compute_gait_parameters(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "steps": 0,
            "cadence": 0,
            "avg_step_time": None,
            "avg_stride_time": None,
            "gait_symmetry": None,
            "stance_swing_ratio": None
        }

    values = df["value"].values
    timestamps = df.index

    # Step detection: threshold crossing (simple but effective)
    step_indices = np.where(values > STEP_THRESHOLD)[0]

    if len(step_indices) < 2:
        return {"steps": 0, "cadence": 0,
                "avg_step_time": None, "avg_stride_time": None,
                "gait_symmetry": None, "stance_swing_ratio": None}

    step_times = timestamps[step_indices]

    # Step time
    diffs = np.diff(step_times) / np.timedelta64(1, "s")
    avg_step_time = float(np.mean(diffs))

    # Stride time = 2 × step time
    avg_stride_time = avg_step_time * 2

    # Cadence (steps per minute)
    cadence = 60 / avg_step_time if avg_step_time > 0 else 0

    # Fake symmetry metric (example; real system uses separate left/right)
    gait_symmetry = max(0, 100 - abs(np.std(values)))

    # Stance vs Swing (pressure-based estimate)
    stance = np.sum(values > STEP_THRESHOLD)
    swing = np.sum(values <= STEP_THRESHOLD)
    stance_swing_ratio = stance / max(1, swing)

    return {
        "steps": len(step_indices),
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
    st.set_page_config(
        page_title="Cloud Data Time Trend Dashboard",
        layout="wide",
    )

    st.title("Cloud Data Time Trend Dashboard")
    st.write("This dashboard shows the trend over time for data values collected via the cloud.")

    # Sidebar
    st.sidebar.header("Settings")
    use_mock = st.sidebar.checkbox("Use mock data (testing)", value=True)
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)

    time_filter = st.sidebar.selectbox(
        "Time range",
        ["All data", "Last 1 hour", "Last 24 hours", "Last 7 days"]
    )

    # Load data
    try:
        df = load_mock_data() if use_mock else load_data_from_api()
    except Exception as e:
        st.error(f"Error loading data from cloud: {e}")
        st.stop()

    if df.empty:
        st.warning("No data available.")
        st.stop()

    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")

    # Time filtering
    if time_filter != "All data":
        max_ts = df.index.max()
        if time_filter == "Last 1 hour":
            df = df[df.index >= max_ts - pd.Timedelta(hours=1)]
        elif time_filter == "Last 24 hours":
            df = df[df.index >= max_ts - pd.Timedelta(hours=24)]
        elif time_filter == "Last 7 days":
            df = df[df.index >= max_ts - pd.Timedelta(days=7)]

    # ---------------------------
    # Layout
    # ---------------------------
    col1, col2 = st.columns([3, 1])

    # ----- Time-Trend Chart -----
    with col1:
        st.subheader("Trend over time")
        st.line_chart(df["value"])

    # ----- Latest + Stats -----
    with col2:
        st.subheader("Latest value")
        latest_ts = df.index.max()
        latest_val = df.loc[latest_ts, "value"]
        st.metric("Most recent data value", f"{latest_val:.2f}")
        st.caption(f"Timestamp: {latest_ts}")

        st.subheader("Summary Statistics")
        st.write(df["value"].describe()[["count", "mean", "min", "max"]])

        # --------- Gait Parameters ----------
        st.subheader("Real-Time Gait Parameters")
        gait = compute_gait_parameters(df)

        st.write(f"**Steps:** {gait['steps']}")
        st.write(f"**Cadence:** {gait['cadence']:.1f} steps/min" if gait['cadence'] else "Cadence: —")
        st.write(f"**Step Time:** {gait['avg_step_time']:.2f} sec" if gait['avg_step_time'] else "Step Time: —")
        st.write(f"**Stride Time:** {gait['avg_stride_time']:.2f} sec" if gait['avg_stride_time'] else "Stride Time: —")
        st.write(f"**Gait Symmetry Index:** {gait['gait_symmetry']:.1f}%" if gait['gait_symmetry'] else "Gait Symmetry: —")
        st.write(f"**Stance/Swing Ratio:** {gait['stance_swing_ratio']:.2f}" if gait['stance_swing_ratio'] else "Stance/Swing Ratio: —")

    # Auto-refresh
    if auto_refresh:
        st.caption(f"Auto-refreshing every {REFRESH_INTERVAL_SECONDS} seconds.")
        time.sleep(REFRESH_INTERVAL_SECONDS)
        st.rerun()


if __name__ == "__main__":
    main()
