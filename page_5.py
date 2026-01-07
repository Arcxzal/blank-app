import streamlit as st
import requests

# URL of your API (adjust if using a remote host)
API_URL = "http://127.0.0.1:8000/api/readings"

st.title("API Test")

try:
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        st.success("Successfully fetched data from API!")
        st.write(data)  # display raw JSON
    else:
        st.error(f"Error fetching data: {response.status_code}")
except Exception as e:
    st.error(f"Exception: {e}")
