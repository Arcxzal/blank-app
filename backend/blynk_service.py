# backend/blynk_service.py
"""
Blynk integration service for sending gait metrics and pressure ratings
"""
import BlynkLib
import numpy as np
import pandas as pd
from typing import Dict, Optional, List
import sys
import os

# Add parent directory to path to import processing module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing import (
    preprocess_signals, 
    detect_heel_strike_toe_off, 
    compute_gait_metrics,
    compute_total_load
)

# Blynk Configuration
BLYNK_AUTH_TOKEN = "qCSvSCCeRSutZIb7CPt4Ppvp0qyEij_o"

# Virtual Pin Assignments
PIN_BIGTOE_RATING = 0       # V0
PIN_PINKYTOE_RATING = 1     # V1
PIN_METAOUT_RATING = 2      # V2
PIN_METAIN_RATING = 3       # V3
PIN_HEEL_RATING = 4         # V4
PIN_CADENCE = 5             # V5
PIN_SWING_TIME = 6          # V6
PIN_STANCE_TIME = 7         # V7
PIN_STEP_SYMMETRY = 8       # V8

class BlynkService:
    """Service to calculate gait metrics and send to Blynk"""
    
    def __init__(self, auth_token: str = BLYNK_AUTH_TOKEN):
        """Initialize Blynk connection"""
        self.auth_token = auth_token
        self.blynk = BlynkLib.Blynk(auth_token)
        self.connected = False
        
    def connect(self):
        """Establish connection to Blynk"""
        try:
            # Test connection by trying to write to a virtual pin
            self.blynk.virtual_write(PIN_CADENCE, 0)
            self.connected = True
            print("✓ Connected to Blynk Cloud")
            return True
        except Exception as e:
            print(f"✗ Blynk connection failed: {e}")
            self.connected = False
            return False
    
    def calculate_pressure_ratings(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Calculate pressure ratings for each sensor based on average values
        
        Args:
            df: DataFrame with pressure columns
            
        Returns:
            Dictionary with ratings for each sensor
        """
        ratings = {}
        
        # Define sensor thresholds (based on your page_6.py analysis)
        thresholds = {
            'bigToe': {'weak': 8, 'high': 45},
            'pinkyToe': {'weak': 5, 'high': 40},
            'metaOut': {'weak': 20, 'high': 50},
            'metaIn': {'weak': 20, 'high': 50},
            'heel': {'weak': 15, 'high': 55}
        }
        
        for sensor, limits in thresholds.items():
            if sensor not in df.columns:
                ratings[sensor] = "No Data"
                continue
                
            avg_pressure = df[sensor].mean()
            
            if avg_pressure < limits['weak']:
                ratings[sensor] = "Weak"
            elif avg_pressure > limits['high']:
                ratings[sensor] = "High"
            else:
                ratings[sensor] = "Normal"
        
        return ratings
    
    def calculate_gait_metrics(self, df: pd.DataFrame, foot: str = 'right') -> Dict:
        """
        Calculate gait metrics from pressure data
        
        Args:
            df: DataFrame with pressure sensor columns
            foot: 'right' or 'left' foot
            
        Returns:
            Dictionary with cadence, swing_time, stance_time, step_symmetry
        """
        try:
            # Preprocess signals
            df_filtered = preprocess_signals(df)
            
            # Detect gait events
            heel_strikes, toe_offs = detect_heel_strike_toe_off(df_filtered, foot=foot)
            
            # Compute metrics
            metrics = compute_gait_metrics(heel_strikes, toe_offs)
            
            # Calculate step symmetry (if both feet data available)
            right_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
            left_cols = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
            
            step_symmetry = 0.0
            if all(col in df.columns for col in right_cols + left_cols):
                right_total = df[right_cols].sum(axis=1).mean()
                left_total = df[left_cols].sum(axis=1).mean()
                
                if max(right_total, left_total) > 0:
                    step_symmetry = 100 - abs(right_total - left_total) / max(right_total, left_total) * 100
            
            # Extract scalar values
            cadence = metrics.get('cadence', 0.0)
            if np.isnan(cadence):
                cadence = 0.0
                
            stance_times = metrics.get('stance_times', np.array([]))
            swing_times = metrics.get('swing_times', np.array([]))
            
            avg_stance = np.mean(stance_times) if len(stance_times) > 0 else 0.0
            avg_swing = np.mean(swing_times) if len(swing_times) > 0 else 0.0
            
            return {
                'cadence': float(cadence),
                'swing_time': float(avg_swing),
                'stance_time': float(avg_stance),
                'step_symmetry': float(step_symmetry)
            }
            
        except Exception as e:
            print(f"Error calculating gait metrics: {e}")
            return {
                'cadence': 0.0,
                'swing_time': 0.0,
                'stance_time': 0.0,
                'step_symmetry': 0.0
            }
    
    def send_to_blynk(self, ratings: Dict[str, str], metrics: Dict[str, float]) -> bool:
        """
        Send pressure ratings and gait metrics to Blynk
        
        Args:
            ratings: Dictionary with pressure ratings
            metrics: Dictionary with gait metrics
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Send pressure ratings (V0-V4)
            self.blynk.virtual_write(PIN_BIGTOE_RATING, ratings.get('bigToe', 'No Data'))
            self.blynk.virtual_write(PIN_PINKYTOE_RATING, ratings.get('pinkyToe', 'No Data'))
            self.blynk.virtual_write(PIN_METAOUT_RATING, ratings.get('metaOut', 'No Data'))
            self.blynk.virtual_write(PIN_METAIN_RATING, ratings.get('metaIn', 'No Data'))
            self.blynk.virtual_write(PIN_HEEL_RATING, ratings.get('heel', 'No Data'))
            
            # Send gait metrics (V5-V8)
            self.blynk.virtual_write(PIN_CADENCE, round(metrics.get('cadence', 0.0), 1))
            self.blynk.virtual_write(PIN_SWING_TIME, round(metrics.get('swing_time', 0.0), 2))
            self.blynk.virtual_write(PIN_STANCE_TIME, round(metrics.get('stance_time', 0.0), 2))
            self.blynk.virtual_write(PIN_STEP_SYMMETRY, round(metrics.get('step_symmetry', 0.0), 1))
            
            print(f"✓ Sent to Blynk - Cadence: {metrics.get('cadence', 0):.1f}, Symmetry: {metrics.get('step_symmetry', 0):.1f}%")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send to Blynk: {e}")
            self.connected = False
            return False
    
    def process_and_send(self, df: pd.DataFrame) -> Dict:
        """
        Complete pipeline: calculate metrics and send to Blynk
        
        Args:
            df: DataFrame with pressure sensor data
            
        Returns:
            Dictionary containing ratings and metrics
        """
        # Calculate ratings
        ratings = self.calculate_pressure_ratings(df)
        
        # Calculate gait metrics
        metrics = self.calculate_gait_metrics(df, foot='right')
        
        # Send to Blynk
        success = self.send_to_blynk(ratings, metrics)
        
        return {
            'ratings': ratings,
            'metrics': metrics,
            'blynk_sent': success
        }


# Singleton instance
_blynk_service: Optional[BlynkService] = None

def get_blynk_service() -> BlynkService:
    """Get or create BlynkService singleton"""
    global _blynk_service
    if _blynk_service is None:
        _blynk_service = BlynkService()
        _blynk_service.connect()
    return _blynk_service
