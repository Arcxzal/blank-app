# dashboard.py

import streamlit as st
import numpy as np

# ---------------------------
# Import test data + processing
# ---------------------------

from test_api import df
from processing import (
    FS,
    preprocess_signals,
    normalize_to_percent_load,
    detect_steps,
    detect_heel_strike_toe_off,
    compute_gait_metrics,
)

# ---------------------------
# Data processing pipeline
# ---------------------------

df_filtered = preprocess_signals(df)
df_norm = normalize_to_percent_load(df_filtered)

# Total load (filtered, non-normalized)
df_filtered["total_load"] = df_filtered[
    ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
].sum(axis=1)

# Event detection
steps = detect_steps(df_filtered["total_load"])
heel_strikes, toe_offs = detect_heel_strike_toe_off(df_filtered)

# Gait metrics
metrics = compute_gait_metrics(heel_strikes, toe_offs, fs=FS)

# ---------------------------
# Streamlit UI
# ---------------------------

st.set_page_config(page_title="Gait Metrics", layout="centered")

st.title("Gait Metrics (Test Mode)")
st.caption("Basic validation dashboard")