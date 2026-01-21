# home_page.py - Main landing page for the Gait Analysis Dashboard

import streamlit as st
from datetime import datetime
from patient_utils import get_patient_display_name, is_demo_patient

# ---------------------------
# Page Configuration
# ---------------------------

def main():
    # Get selected patient info
    patient_name = get_patient_display_name()
    is_demo = is_demo_patient()
    
    st.set_page_config(
        page_title="Gait Analysis Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom styling
    st.markdown("""
        <style>
        .header-title {
            font-size: 3.5em;
            font-weight: bold;
            color: #0072B2;
            margin-bottom: 0.5em;
        }
        .subtitle {
            font-size: 1.3em;
            color: #555;
            margin-bottom: 2em;
        }
        .feature-box {
            background-color: #f0f2f6;
            padding: 1.5em;
            border-radius: 0.5em;
            margin: 1em 0;
            border-left: 4px solid #0072B2;
        }
        .stat-card {
            background-color: #ffffff;
            padding: 1.5em;
            border-radius: 0.5em;
            border: 1px solid #ddd;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------
    # Header Section
    # ---------------------------
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<div class="header-title">🚶 Gait Analysis Dashboard</div>', unsafe_allow_html=True)
        patient_indicator = "🎭 Demo Mode" if is_demo else f"📡 {patient_name}"
        st.markdown(f'<div class="subtitle">Real-time pressure sensor analysis and gait metrics • {patient_indicator}</div>', unsafe_allow_html=True)
    
    with col2:
        st.metric("Patient", patient_name if not is_demo else "Demo")
        st.metric("Status", "🟢 Active")

    # ---------------------------
    # Quick Stats Section
    # ---------------------------
    st.header("📊 System Overview")
    
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.markdown("""
            <div class="stat-card">
                <h3>5</h3>
                <p>Pressure Points</p>
            </div>
        """, unsafe_allow_html=True)
    
    with stats_col2:
        st.markdown("""
            <div class="stat-card">
                <h3>10</h3>
                <p>Total Sensors</p>
            </div>
        """, unsafe_allow_html=True)
    
    with stats_col3:
        st.markdown("""
            <div class="stat-card">
                <h3>25 Hz</h3>
                <p>Sampling Rate</p>
            </div>
        """, unsafe_allow_html=True)
    
    with stats_col4:
        st.markdown("""
            <div class="stat-card">
                <h3>Real-time</h3>
                <p>Live Updates</p>
            </div>
        """, unsafe_allow_html=True)

    # ---------------------------
    # Features Section
    # ---------------------------
    st.header("✨ Features")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="feature-box">
                <h4>📈 Pressure Analysis</h4>
                <p>Monitor pressure distribution across all 5 key pressure points (heel, metatarsal heads, pinky toe, big toe) on both feet with Savitzky-Golay filtering for clean signals.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <div class="feature-box">
                <h4>🔄 Left vs Right Comparison</h4>
                <p>Compare gait symmetry between left and right feet with color-coded trend lines for easy interpretation.</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="feature-box">
                <h4>⚡ Real-time Metrics</h4>
                <p>Track gait parameters including cadence, stride time, stance/swing ratio, and gait symmetry index in real-time.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <div class="feature-box">
                <h4>📱 Multi-page Dashboard</h4>
                <p>Navigate through detailed analysis pages, individual metrics, and comprehensive reports with filtered data views.</p>
            </div>
        """, unsafe_allow_html=True)

    # ---------------------------
    # Available Pages Section
    # ---------------------------
    st.header("📑 Available Pages")
    
    pages_info = {
        "🏠 Home": {
            "file": "main_page.py",
            "description": "Overview and navigation hub (you are here)"
        },
        "📊 Pressure Dashboard": {
            "file": "page_2.py",
            "description": "Detailed pressure readings with left/right foot comparison, filtered with Savitzky-Golay smoothing"
        },
        "🦶 Advanced Gait Analysis": {
            "file": "page_3.py",
            "description": "Load distribution analysis, gait symmetry, and pressure timeline visualization"
        },
        "📈 Data exploration and metrics": {
            "file": "page_4.py",
            "description": "Raw data exploration, correlation analysis, and statistical metrics"
        },
    }
    
    # Create a nice layout for page navigation
    for page_name, info in pages_info.items():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**{page_name}**")
        with col2:
            st.markdown(f"*{info['description']}*")
    
    st.divider()

    # ---------------------------
    # System Information Section
    # ---------------------------
    st.header("ℹ️ System Information")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("Sampling Frequency", "25 Hz")
    
    with info_col2:
        st.metric("Current Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with info_col3:
        st.metric("Data Source", "Cloud API")

    # ---------------------------
    # Footer
    # ---------------------------
    st.divider()
    st.markdown("""
        **Gait Analysis Dashboard v1.0** | Powered by Streamlit & FastAPI
        
        📧 For support or questions, please contact the development team.
    """)


if __name__ == "__main__":
    main()
