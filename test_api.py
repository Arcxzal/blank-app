import streamlit as st
import requests
import pandas as pd

API_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings"

st.title("Pressure Data Viewer")

response = requests.get(API_URL)
response.raise_for_status()
data = response.json()

# Flatten JSON safely
records = []
for entry in data:
    pressures = entry.get("pressures", {})
    records.append({
        "timestamp": entry.get("timestamp"),
        "bigToe": pressures.get("bigToe"),
        "pinkyToe": pressures.get("pinkyToe"),
        "metaOut": pressures.get("metaOut"),
        "metaIn": pressures.get("metaIn"),
        "heel": pressures.get("heel"),
    })

df = pd.DataFrame(records)

# FORCE proper datetime dtype
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

# Optional: drop bad rows
df = df.dropna(subset=["timestamp"])

st.dataframe(df)

st.line_chart(
    df.set_index("timestamp")[["bigToe", "pinkyToe", "metaOut", "metaIn", "heel"]]
)
