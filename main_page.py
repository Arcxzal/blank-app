
# dashboard.py

import time
import requests
import pandas as pd
import streamlit as st

# ---------------------------
# Configuration
# ---------------------------

# Example: URL of your cloud endpoint or storage gateway
CLOUD_DATA_URL = "https://example.com/api/data"  # change this to your real URL

REFRESH_INTERVAL_SECONDS = 30  # how often to auto-refresh the chart


# ---------------------------
# Data loading helpers
# ---------------------------

def load_data_from_api() -> pd.DataFrame:
    """
    Example loader if your data is exposed via a REST API.
    Expected JSON format:
    [
      {"timestamp": "2025-11-26T10:00:00Z", "value": 12.5},
      {"timestamp": "2025-11-26T10:05:00Z", "value": 13.1},
      ...
    ]
    """
    response = requests.get(CLOUD_DATA_URL, timeout=10)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    return df


def load_mock_data() -> pd.DataFrame:
    """
    Fallback / demo loader if you do not have real cloud data yet.
    It simulates a time series.
    """
    import numpy as np

    rng = pd.date_range("2025-11-01", periods=50, freq="H")
    values = np.cumsum(np.random.randn(len(rng))) + 50

    df = pd.DataFrame({"timestamp": rng, "value": values})
    return df


# ---------------------------
# Main Streamlit app
# ---------------------------

def main():
    st.set_page_config(
        page_title="Cloud Data Time Trend Dashboard",
        layout="wide",
    )

    st.title("Cloud Data Time Trend Dashboard")
    st.write("This dashboard shows the trend over time for data values collected via the cloud.")

    # Sidebar configuration
    st.sidebar.header("Settings")

    use_mock = st.sidebar.checkbox(
        "Use mock data (for testing)",
        value=True,
        help="Uncheck this when your real cloud API is ready."
    )

    auto_refresh = st.sidebar.checkbox(
        "Auto-refresh",
        value=True,
        help=f"Refresh data every {REFRESH_INTERVAL_SECONDS} seconds."
    )

    # Time range filter
    time_filter_options = ["All data", "Last 1 hour", "Last 24 hours", "Last 7 days"]
    time_filter = st.sidebar.selectbox("Time range", time_filter_options)

    # ---------------------------
    # Data loading
    # ---------------------------
    try:
        if use_mock:
            df = load_mock_data()
        else:
            df = load_data_from_api()
    except Exception as e:
        st.error(f"Error loading data from cloud: {e}")
        st.stop()

    if df.empty:
        st.warning("No data available.")
        st.stop()

    # ---------------------------
    # Data filtering
    # ---------------------------
    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")

    # Apply time filter
    if time_filter != "All data":
        max_ts = df.index.max()
        if time_filter == "Last 1 hour":
            min_ts = max_ts - pd.Timedelta(hours=1)
        elif time_filter == "Last 24 hours":
            min_ts = max_ts - pd.Timedelta(hours=24)
        elif time_filter == "Last 7 days":
            min_ts = max_ts - pd.Timedelta(days=7)
        df = df[df.index >= min_ts]

    # ---------------------------
    # Main layout
    # ---------------------------
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Trend over time")
        st.line_chart(df["value"])

    with col2:
        st.subheader("Latest value")
        latest_timestamp = df.index.max()
        latest_value = df.loc[latest_timestamp, "value"]

        st.metric(
            label="Most recent data value",
            value=f"{latest_value:.2f}",
            delta=None
        )
        st.caption(f"Timestamp: {latest_timestamp}")

        st.subheader("Summary statistics")
        st.write(
            df["value"].describe()[["count", "mean", "min", "max"]]
            .rename({"count": "N", "mean": "Mean", "min": "Min", "max": "Max"})
        )

    # ---------------------------
    # Auto refresh handling
    # ---------------------------
    if auto_refresh:
        # Simple auto-refresh trick: rerun after N seconds
        st.caption(f"Auto-refreshing every {REFRESH_INTERVAL_SECONDS} seconds.")
        time.sleep(REFRESH_INTERVAL_SECONDS)
        st.rerun()


if __name__ == "__main__":
    main()
