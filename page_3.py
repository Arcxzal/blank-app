import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from test_api import df
from streamlit_app import cadence, stance_times, swing_times, df_filtered, heel_strikes, df_norm, toe_offs
from processing import (
    FS,
    savgol_filter_signal,
    preprocess_signals,
    normalize_to_percent_load,
    detect_steps,
    detect_heel_strike_toe_off,
    compute_gait_metrics,
)


time_sec = (df_filtered.index.values) / FS


st.title("Gait Analysis Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Cadence (steps/min)", f"{cadence:.1f}")
col2.metric("Mean Stance Time (s)", f"{np.mean(stance_times):.2f}")
col3.metric("Mean Swing Time (s)", f"{np.mean(swing_times):.2f}")
col4.metric("Detected Steps", len(heel_strikes))

sensor_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
total_load = df_filtered[sensor_cols].sum(axis=1)


st.subheader("Total Plantar Load with Gait Events")

fig, ax = plt.subplots(figsize=(10, 4))

ax.plot(time_sec, total_load, label="Total Load")

# Heel strikes
for hs in heel_strikes:
    ax.axvline(hs / FS, linestyle='-', linewidth=1)

# Toe offs
for to in toe_offs:
    ax.axvline(to / FS, linestyle='--', linewidth=1)

ax.set_xlabel("Time (s)")
ax.set_ylabel("Load (a.u.)")
ax.set_title("Heel Strike (solid) and Toe Off (dashed)")
ax.legend()

st.pyplot(fig)


st.subheader("Normalized Sensor Load Distribution")

fig2, ax2 = plt.subplots(figsize=(10, 4))

for col in sensor_cols:
    ax2.plot(time_sec, df_norm[col], label=col)

ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Load Contribution (%)")
ax2.set_ylim(0, 100)
ax2.legend(ncol=3)

st.pyplot(fig2)


step_table = pd.DataFrame({
    "Step": np.arange(1, len(stance_times) + 1),
    "Heel Strike (s)": np.array(heel_strikes[:len(stance_times)]) / FS,
    "Toe Off (s)": np.array(toe_offs[:len(stance_times)]) / FS,
    "Stance Time (s)": stance_times,
    "Swing Time (s)": swing_times
})


st.subheader("Step-Level Temporal Metrics")
st.dataframe(step_table, use_container_width=True)
