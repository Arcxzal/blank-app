# page_6.py - Action Plan Generator

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests
from patient_utils import load_patient_data, is_demo_patient, get_patient_display_name

# ---------------------------
# Configuration
# ---------------------------

CLOUD_DATA_URL = "https://silver-space-umbrella-4j5q5647xwj735gx-8000.app.github.dev/api/readings"


# ---------------------------
# Data Loading
# ---------------------------

@st.cache_data(ttl=2)
def load_data_from_api() -> pd.DataFrame:
    response = requests.get(CLOUD_DATA_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    records = []
    for entry in data:
        timestamp = entry.get("timestamp")
        if not timestamp:
            continue
        pressures = entry.get("pressures", {})
        record = {
            "timestamp": timestamp,
            "bigToe": pressures.get("bigToe", 0),
            "pinkyToe": pressures.get("pinkyToe", 0),
            "metaOut": pressures.get("metaOut", 0),
            "metaIn": pressures.get("metaIn", 0),
            "heel": pressures.get("heel", 0),
            "bigToe_L": pressures.get("bigToe_L", 0),
            "pinkyToe_L": pressures.get("pinkyToe_L", 0),
            "metaOut_L": pressures.get("metaOut_L", 0),
            "metaIn_L": pressures.get("metaIn_L", 0),
            "heel_L": pressures.get("heel_L", 0),
        }
        records.append(record)
    
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp")
    return df


def load_mock_data() -> pd.DataFrame:
    start_date = datetime.now() - pd.Timedelta(hours=1)
    rng = pd.date_range(start_date, periods=300, freq="10s")
    df = pd.DataFrame({
        "timestamp": rng,
        "bigToe": np.abs(np.sin(np.linspace(0, 30, len(rng))) * 40 + np.random.randn(len(rng)) * 3),
        "pinkyToe": np.abs(np.sin(np.linspace(0, 25, len(rng))) * 35 + np.random.randn(len(rng)) * 3),
        "metaOut": np.abs(np.sin(np.linspace(0, 28, len(rng))) * 38 + np.random.randn(len(rng)) * 3),
        "metaIn": np.abs(np.sin(np.linspace(0, 26, len(rng))) * 36 + np.random.randn(len(rng)) * 3),
        "heel": np.abs(np.sin(np.linspace(0, 32, len(rng))) * 45 + np.random.randn(len(rng)) * 3),
        "bigToe_L": np.abs(np.sin(np.linspace(0, 30, len(rng)) + 0.5) * 40 + np.random.randn(len(rng)) * 3),
        "pinkyToe_L": np.abs(np.sin(np.linspace(0, 25, len(rng)) + 0.5) * 35 + np.random.randn(len(rng)) * 3),
        "metaOut_L": np.abs(np.sin(np.linspace(0, 28, len(rng)) + 0.5) * 38 + np.random.randn(len(rng)) * 3),
        "metaIn_L": np.abs(np.sin(np.linspace(0, 26, len(rng)) + 0.5) * 36 + np.random.randn(len(rng)) * 3),
        "heel_L": np.abs(np.sin(np.linspace(0, 32, len(rng)) + 0.5) * 45 + np.random.randn(len(rng)) * 3),
    })
    return df


# ---------------------------
# Action Plan Generation
# ---------------------------

def generate_action_plan(df: pd.DataFrame) -> dict:
    """
    Generate personalized rehabilitation action plan based on gait analysis data.
    Tailored for patients with muscle weakness undergoing rehabilitation.
    
    Args:
        df: DataFrame with pressure sensor data
        
    Returns:
        dict: Contains assessment summary and list of action recommendations
    """
    right_sensors = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    left_sensors = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
    
    actions = []
    
    # Calculate metrics
    right_total = df[right_sensors].sum(axis=1).mean()
    left_total = df[left_sensors].sum(axis=1).mean()
    symmetry_index = 100 - abs(right_total - left_total) / max(right_total, left_total) * 100
    
    # Analyze load distribution
    right_load = {sensor: df[sensor].mean() for sensor in right_sensors}
    left_load = {sensor.replace('_L', ''): df[sensor].mean() for sensor in left_sensors}
    
    # Symmetry Analysis - Rehab Focus
    if symmetry_index < 70:
        weaker_side = "right" if right_total < left_total else "left"
        actions.append({
            "priority": "🔴 High",
            "title": "Critical: Significant Limb Weakness Detected",
            "description": f"Symmetry index is {symmetry_index:.1f}%. Your {weaker_side} side shows notable weakness.",
            "recommendations": [
                "Increase focused strengthening exercises for the weaker side",
                "Start with seated or supported standing exercises (wall, parallel bars)",
                "Perform quadriceps and hip abductor strengthening 3-5x weekly",
                "Use assistive device (cane, walker) if needed for safety",
                "Document progress weekly - expect gradual improvements over weeks",
                "Consult PT if weakness is acute or worsening"
            ]
        })
    elif symmetry_index < 85:
        weaker_side = "right" if right_total < left_total else "left"
        actions.append({
            "priority": "🟡 Medium",
            "title": "Moderate Limb Weakness: Strengthen Weaker Side",
            "description": f"Symmetry index is {symmetry_index:.1f}%. Your {weaker_side} leg needs focused strengthening.",
            "recommendations": [
                "Increase single-leg stance time (hold onto support) on the weaker side",
                "Perform step-ups and mini-squats focusing on the weaker leg",
                "Use resistance band for hip and leg exercises daily",
                "Progress to single-leg balance activities as tolerated",
                "Track improvements weekly and adjust intensity gradually"
            ]
        })
    else:
        actions.append({
            "priority": "🟢 Good",
            "title": "Excellent Symmetry: Continue Maintenance",
            "description": f"Symmetry index is {symmetry_index:.1f}%! Good progress in balance and strength.",
            "recommendations": [
                "Continue current strengthening routine 3-4x weekly",
                "Progress to more challenging balance exercises",
                "Maintain consistent walking program",
                "Monitor for any regression and adjust as needed"
            ]
        })
    
    # Heel Strike Analysis - Rehab Focus
    heel_right = df['heel'].mean()
    heel_left = df['heel_L'].mean()
    
    if heel_right < 15 or heel_left < 15:
        weak_heel_side = "right" if heel_right < heel_left else "left"
        actions.append({
            "priority": "🟡 Medium",
            "title": "Weakness in Dorsiflexors: Lift Toe Phase Training",
            "description": f"Weak heel pressure on {weak_heel_side} side indicates dorsiflexor weakness.",
            "recommendations": [
                "Practice seated dorsiflexion exercises with resistance band",
                "Perform high-step walking to strengthen tibialis anterior",
                "Do heel-walking drills (walking on heels with toes up)",
                "Perform seated toe taps and heel raises to build endurance",
                "Repeat exercises daily for 5-10 minutes"
            ]
        })
    
    # Forefoot (Meta) Pressure Analysis - Rehab Focus
    meta_right = (df['metaOut'].mean() + df['metaIn'].mean()) / 2
    meta_left = (df['metaOut_L'].mean() + df['metaIn_L'].mean()) / 2
    
    if meta_right < 20 or meta_left < 20:
        weak_meta_side = "right" if meta_right < meta_left else "left"
        actions.append({
            "priority": "🟡 Medium",
            "title": "Plantar Flexor Weakness: Calf and Arch Strengthening",
            "description": f"Low forefoot pressure on {weak_meta_side} side indicates plantar flexor weakness.",
            "recommendations": [
                "Perform seated calf raises with or without resistance",
                "Practice toe presses and short foot exercises for arch strength",
                "Use resistance band for plantar flexion exercises daily",
                "Progress to standing calf raises when strength allows",
                "Include in daily routine for sustained strengthening"
            ]
        })
    elif meta_right > 50 or meta_left > 50:
        actions.append({
            "priority": "🟡 Medium",
            "title": "Forefoot Overload: Reduce Impact Stress",
            "description": "High forefoot pressure detected - likely compensating for weak areas.",
            "recommendations": [
                "Use cushioned/padded shoes to reduce forefoot impact",
                "Take frequent walking breaks to avoid fatigue",
                "Focus on full foot contact rather than forefoot striking",
                "Improve overall leg strength to normalize load distribution",
                "Wear orthotics with metatarsal support"
            ]
        })
    
    # Toe Analysis - Rehab Focus
    bigtoe_right = df['bigToe'].mean()
    bigtoe_left = df['bigToe_L'].mean()
    
    if bigtoe_right < 8 or bigtoe_left < 8:
        actions.append({
            "priority": "🟡 Medium",
            "title": "Weak Push-Off Phase: Hallux and Toe Strengthening",
            "description": "Low big toe pressure suggests weakness during push-off phase.",
            "recommendations": [
                "Perform toe flexion exercises with resistance band daily",
                "Practice picking up small objects with toes (marbles, socks)",
                "Do seated toe curls against resistance for 10-15 reps",
                "Walk slowly focusing on strong toe-off with each step",
                "Progress to standing balance on toes as strength improves"
            ]
        })
    
    # Overall Load Assessment - Rehab Focus
    avg_total = (right_total + left_total) / 2
    
    if avg_total < 12:
        actions.append({
            "priority": "🔴 High",
            "title": "Very Low Load: Severe Weakness Present",
            "description": "Overall pressure is very low. Significant strength deficit detected.",
            "recommendations": [
                "Focus on fundamental strengthening before increasing distance",
                "Start with short walks (5-10 min) on flat, safe surfaces",
                "Gradually increase walking duration by 1-2 min per week",
                "Prioritize strengthening exercises 5-6x weekly over long walks",
                "Consider supportive devices (walker, cane) for safety",
                "Ensure proper supervision/assistance with mobility"
            ]
        })
    elif avg_total < 25:
        actions.append({
            "priority": "🟡 Medium",
            "title": "Progressive Loading: Gradually Increase Activity",
            "description": "Low overall load indicates ongoing recovery phase.",
            "recommendations": [
                "Increase daily walking by 5 minutes each week as tolerated",
                "Alternate between walking and strengthening exercises",
                "Include 2-3 rest days per week for recovery",
                "Monitor for increased pain or fatigue",
                "Progress slowly - consistency matters more than intensity"
            ]
        })
    else:
        actions.append({
            "priority": "🟢 Good",
            "title": "Good Load Tolerance: Maintain Activity Level",
            "description": f"Average load of {avg_total:.1f} shows good tolerance for activity.",
            "recommendations": [
                "Continue current walking and strengthening routine",
                "Gradually increase duration or intensity as tolerated",
                "Add functional activities (stairs, uneven surfaces) if ready",
                "Maintain 3-4x weekly strengthening exercises",
                "Track progress and celebrate improvements"
            ]
        })
    
    return {
        "symmetry_index": symmetry_index,
        "avg_load": avg_total,
        "right_total": right_total,
        "left_total": left_total,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actions": actions
    }


# ---------------------------
# Main App
# ---------------------------

def main():
    # Get selected patient info
    patient_name = get_patient_display_name()
    is_demo = is_demo_patient()
    
    st.set_page_config(
        page_title="Action Plan Generator",
        layout="wide",
    )

    st.title("📋 Personalized Action Plan")
    patient_badge = "🎭 Demo Patient" if is_demo else f"📡 {patient_name}"
    st.caption(f"Viewing data for: **{patient_badge}**")
    st.write("Generate a static action plan based on your current gait analysis data.")

    # Sidebar
    st.sidebar.header("Settings")

    # Initialize session state for storing frozen plan
    if "frozen_plan" not in st.session_state:
        st.session_state.frozen_plan = None
    if "plan_generated_time" not in st.session_state:
        st.session_state.plan_generated_time = None

    # Load current data using helper function
    try:
        df = load_patient_data(num_cycles=20, cadence=115)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        df = pd.DataFrame()

    if df.empty:
        st.warning("⚠️ No data available. Please enable mock data or check your connection.")
        return

    # Generate button
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("🔄 Generate Plan"):
            plan = generate_action_plan(df)
            st.session_state.frozen_plan = plan
            st.session_state.plan_generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.success("Action plan generated!")
    
    with col2:
        if st.session_state.frozen_plan:
            st.info(f"Last updated: {st.session_state.plan_generated_time}")
        else:
            st.info("Click 'Generate Plan' to create a personalized action plan based on current data.")

    st.divider()

    # Display frozen plan
    if st.session_state.frozen_plan:
        plan = st.session_state.frozen_plan
        
        # Metrics
        st.header("📊 Key Metrics")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("Symmetry Index", f"{plan['symmetry_index']:.1f}%")
        
        with metric_col2:
            st.metric("Avg Total Load", f"{plan['avg_load']:.1f}")
        
        with metric_col3:
            st.metric("Right Foot Load", f"{plan['right_total']:.1f}")
        
        with metric_col4:
            st.metric("Left Foot Load", f"{plan['left_total']:.1f}")

        st.divider()

        # Action Plan
        st.header("💡 Recommended Actions")
        
        for i, action in enumerate(plan['actions']):
            with st.expander(f"{action['priority']} {action['title']}", expanded=(i==0)):
                st.write(f"**{action['description']}**")
                st.write("**Recommendations:**")
                for rec in action['recommendations']:
                    st.write(f"• {rec}")
        
        st.divider()
        
        # Export option
        st.header("📥 Export Plan")
        
        # Generate text report
        report_text = f"""
GAIT ANALYSIS ACTION PLAN
Generated: {plan['timestamp']}

KEY METRICS
-----------
Symmetry Index: {plan['symmetry_index']:.1f}%
Average Total Load: {plan['avg_load']:.1f}
Right Foot Load: {plan['right_total']:.1f}
Left Foot Load: {plan['left_total']:.1f}

RECOMMENDED ACTIONS
-------------------
"""
        
        for action in plan['actions']:
            report_text += f"\n{action['priority']} - {action['title']}\n"
            report_text += f"Description: {action['description']}\n"
            report_text += "Recommendations:\n"
            for rec in action['recommendations']:
                report_text += f"  • {rec}\n"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Download as Text",
                data=report_text,
                file_name=f"gait_action_plan_{st.session_state.plan_generated_time.replace(':', '-').replace(' ', '_')}.txt",
                mime="text/plain"
            )
        
        with col2:
            # CSV export of metrics
            metrics_df = pd.DataFrame({
                "Metric": ["Symmetry Index (%)", "Avg Total Load", "Right Foot Load", "Left Foot Load"],
                "Value": [f"{plan['symmetry_index']:.1f}", f"{plan['avg_load']:.1f}", f"{plan['right_total']:.1f}", f"{plan['left_total']:.1f}"]
            })
            
            st.download_button(
                label="📊 Download as CSV",
                data=metrics_df.to_csv(index=False),
                file_name=f"gait_metrics_{st.session_state.plan_generated_time.replace(':', '-').replace(' ', '_')}.csv",
                mime="text/csv"
            )
    else:
        st.info("👆 Click the 'Generate Plan' button above to create your personalized action plan.")


if __name__ == "__main__":
    main()
