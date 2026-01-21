import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import numpy as np
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt

# Backend API URL
API_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev"

# ---------------------------
# Patient Selection Sidebar
# ---------------------------
st.sidebar.title("👤 Patient Selection")
st.sidebar.markdown("---")

# Initialize session state
if 'selected_patient_id' not in st.session_state:
    st.session_state.selected_patient_id = "demo"
if 'patients_list' not in st.session_state:
    st.session_state.patients_list = []
if 'show_add_patient' not in st.session_state:
    st.session_state.show_add_patient = False
if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = False

# Load patients from API
@st.cache_data(ttl=10)
def load_patients():
    try:
        response = requests.get(f"{API_URL}/api/patients", timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

# Fetch patients
patients = load_patients()
st.session_state.patients_list = patients

# Create patient options list
patient_options = [{"id": "demo", "name": "Demo Patient (Synthetic Data)"}]
for p in patients:
    patient_options.append({"id": p["id"], "name": p["name"]})

# Patient selector
selected_index = 0
for i, opt in enumerate(patient_options):
    if opt["id"] == st.session_state.selected_patient_id:
        selected_index = i
        break

selected_patient = st.sidebar.selectbox(
    "Select Patient:",
    options=range(len(patient_options)),
    format_func=lambda x: patient_options[x]["name"],
    index=selected_index,
    key="patient_selector"
)

# Update session state
st.session_state.selected_patient_id = patient_options[selected_patient]["id"]
st.session_state.selected_patient_name = patient_options[selected_patient]["name"]

# Display patient info
if st.session_state.selected_patient_id == "demo":
    st.sidebar.info("🎭 **Demo Mode**\n\nShowing synthetic gait data for testing and demonstration.")
else:
    patient_detail = next((p for p in patients if p["id"] == st.session_state.selected_patient_id), None)
    if patient_detail:
        st.sidebar.success(f"📡 **Real Patient**\n\n**Name:** {patient_detail['name']}\n**Age:** {patient_detail.get('age', 'N/A')}\n**ID:** {patient_detail['id']}")
        
        # Delete patient section
        if not st.session_state.show_delete_confirm:
            if st.sidebar.button("🗑️ Delete This Patient", type="secondary"):
                st.session_state.show_delete_confirm = True
                st.rerun()
        else:
            st.sidebar.warning("⚠️ **Are you sure?**\n\nThis will permanently delete the patient and all their data.")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.sidebar.button("✅ Confirm", type="primary"):
                    try:
                        response = requests.delete(
                            f"{API_URL}/api/patients/{st.session_state.selected_patient_id}",
                            timeout=5
                        )
                        if response.status_code == 200:
                            st.sidebar.success("✅ Patient deleted")
                            st.session_state.selected_patient_id = "demo"
                            st.session_state.show_delete_confirm = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.sidebar.error("Failed to delete patient")
                            st.session_state.show_delete_confirm = False
                    except Exception as e:
                        st.sidebar.error(f"Error: {e}")
                        st.session_state.show_delete_confirm = False
            with col2:
                if st.sidebar.button("❌ Cancel"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()
    else:
        st.sidebar.success("📡 **Real Patient**\n\nShowing real sensor data.")

st.sidebar.markdown("---")

# Add patient button
if st.sidebar.button("➕ Add New Patient"):
    st.session_state.show_add_patient = True

# Add patient form
if st.session_state.show_add_patient:
    st.sidebar.subheader("Create New Patient")
    with st.sidebar.form("add_patient_form"):
        new_name = st.text_input("Name*", placeholder="Enter patient name")
        new_age = st.number_input("Age", min_value=0, max_value=120, value=None, placeholder="Optional")
        new_notes = st.text_area("Notes", placeholder="Optional notes")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Create")
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if submit and new_name:
            try:
                response = requests.post(
                    f"{API_URL}/api/patients",
                    json={"name": new_name, "age": new_age, "notes": new_notes},
                    timeout=5
                )
                if response.status_code == 201:
                    st.success(f"✅ Created patient: {new_name}")
                    st.session_state.show_add_patient = False
                    st.cache_data.clear()  # Refresh patient list
                    st.rerun()
                else:
                    st.error("Failed to create patient")
            except Exception as e:
                st.error(f"Error: {e}")
        elif submit:
            st.error("Name is required")
        
        if cancel:
            st.session_state.show_add_patient = False
            st.rerun()

st.sidebar.markdown("---")

# ---------------------------
# Navigation Setup
# ---------------------------

main_page = st.Page("main_page.py", title="Home", icon="🏠")
page_2 = st.Page("page_2.py", title="Pressure Dashboard", icon="📊")
page_3 = st.Page("page_3.py", title="Additional analysis page", icon="🦶")
page_4 = st.Page("page_4.py", title="Data exploration and metrics", icon="📈")
page_6 = st.Page("page_6.py", title="Action Plan", icon="💡")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_6,])

# Run the selected page
pg.run()