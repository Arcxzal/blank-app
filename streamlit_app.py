import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import numpy as np
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt


from test_api import df
from processing import (
    FS,
    savgol_filter_signal,
    preprocess_signals,
    normalize_to_percent_load,
    detect_steps,
    detect_heel_strike_toe_off,
    compute_gait_metrics,
)


main_page = st.Page("main_page.py", title="Main Page", icon="🎈")
page_2 = st.Page("page_2.py", title="Page 2", icon="❄️")
page_3 = st.Page("page_3.py", title="Page 3", icon="🎉")
page_4 = st.Page("page_4.py", title="Page 4", icon="🚀")
page_5 = st.Page("page_5.py", title="Page 5", icon="🌟")
page_6 = st.Page("page_6.py", title="Page 6", icon="7")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5,])

# Run the selected page
pg.run()

# Processing

df_filtered = preprocess_signals(df)
df_norm = normalize_to_percent_load(df_filtered)

df_filtered["total_load"] = df_filtered[['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']].sum(axis=1)
steps = detect_steps(df_filtered["total_load"])
heel_strikes, toe_offs = detect_heel_strike_toe_off(df_filtered)
metrics = compute_gait_metrics(heel_strikes, toe_offs)

# metrics["stance_times"]
# metrics["swing_times"]
# metrics["cadence"]