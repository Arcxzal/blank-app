# backend/blynk_http_service.py
"""
Blynk HTTP API integration (alternative to socket-based library)
Uses HTTPS REST API which works better in restricted environments
"""
import requests
import numpy as np
import pandas as pd
from typing import Dict, Optional
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
BLYNK_HTTP_API = "https://sgp1.blynk.cloud/external/api"  # Singapore server

# Virtual Pin Assignments
PIN_BIGTOE_RATING = 0       # V0
PIN_PINKYTOE_RATING = 1     # V1
PIN_METAOUT_RATING = 2      # V2
PIN_METAIN_RATING = 3       # V3
PIN_HEEL_RATING = 4         # V4
PIN_CADENCE = 5             # V5
PIN_STEP_TIME = 6           # V6
PIN_STANCE_TIME = 7         # V7
PIN_STEP_SYMMETRY = 8       # V8
PIN_GAIT_BALANCE = 9        # V9 - Biphasic L/R pressure balance (-100 to +100)

class BlynkHttpService:
    """Service to calculate gait metrics and send to Blynk via HTTP API"""
    
    def __init__(self, auth_token: str = BLYNK_AUTH_TOKEN):
        """Initialize Blynk HTTP service"""
        self.auth_token = auth_token
        self.api_url = BLYNK_HTTP_API
        self.connected = False
        
    def connect(self):
        """Test connection to Blynk HTTP API"""
        try:
            # Test by reading a virtual pin
            url = f"{self.api_url}/get?token={self.auth_token}&v0"
            response = requests.get(url, timeout=5)
            
            # Any response (even error) means we can reach the server
            self.connected = response.status_code in [200, 400]
            
            if self.connected:
                print("✓ Connected to Blynk Cloud (HTTP API)")
            return self.connected
            
        except Exception as e:
            print(f"✗ Blynk connection failed: {e}")
            self.connected = False
            return False
    
    def calculate_pressure_ratings(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Calculate pressure ratings for each sensor based on average values
        Returns numeric values on a scale of 1-100
        
        Args:
            df: DataFrame with pressure columns
            
        Returns:
            Dictionary with ratings (1-100) for each sensor
            1-33: Weak pressure
            34-66: Normal pressure
            67-100: High pressure
        """
        ratings = {}
        
        # Define sensor thresholds
        thresholds = {
            'bigToe': {'weak': 8, 'high': 45},
            'pinkyToe': {'weak': 5, 'high': 40},
            'metaOut': {'weak': 20, 'high': 50},
            'metaIn': {'weak': 20, 'high': 50},
            'heel': {'weak': 15, 'high': 55}
        }
        
        for sensor, limits in thresholds.items():
            if sensor not in df.columns:
                ratings[sensor] = 50  # Default to middle (Normal)
                continue
                
            avg_pressure = df[sensor].mean()
            weak_threshold = limits['weak']
            high_threshold = limits['high']
            
            if avg_pressure <= weak_threshold:
                # Map 0 to weak_threshold → 1 to 33
                if avg_pressure <= 0:
                    rating = 1
                else:
                    rating = int(1 + (avg_pressure / weak_threshold) * 32)
                    rating = max(1, min(33, rating))
            elif avg_pressure >= high_threshold:
                # Map high_threshold to max → 67 to 100
                max_pressure = high_threshold * 2  # Assume max is 2x high threshold
                if avg_pressure >= max_pressure:
                    rating = 100
                else:
                    ratio = (avg_pressure - high_threshold) / (max_pressure - high_threshold)
                    rating = int(67 + ratio * 33)
                    rating = max(67, min(100, rating))
            else:
                # Map weak_threshold to high_threshold → 34 to 66
                ratio = (avg_pressure - weak_threshold) / (high_threshold - weak_threshold)
                rating = int(34 + ratio * 32)
                rating = max(34, min(66, rating))
            
            ratings[sensor] = rating
        
        return ratings
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
            
            # Calculate step symmetry and gait balance
            right_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
            left_cols = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
            
            step_symmetry = 0.0
            gait_balance = 0.0
            if all(col in df.columns for col in right_cols + left_cols):
                right_total = df[right_cols].sum(axis=1).mean()
                left_total = df[left_cols].sum(axis=1).mean()
                
                if max(right_total, left_total) > 0:
                    step_symmetry = 100 - abs(right_total - left_total) / max(right_total, left_total) * 100
                
                # Biphasic gait balance: positive = left foot dominant, negative = right foot dominant
                total_pressure = left_total + right_total
                if total_pressure > 0:
                    gait_balance = ((left_total - right_total) / total_pressure) * 100
            
            # Extract scalar values
            cadence = metrics.get('cadence', 0.0)
            if np.isnan(cadence):
                cadence = 0.0
                
            stance_times = metrics.get('stance_times', np.array([]))
            swing_times = metrics.get('swing_times', np.array([]))
            
            avg_stance = np.mean(stance_times) if len(stance_times) > 0 else 0.0
            avg_swing = np.mean(swing_times) if len(swing_times) > 0 else 0.0
            
            # Calculate step time (complete gait cycle for one foot)
            # Step time = stance time + swing time, or 60/cadence if cadence available
            if cadence > 0:
                step_time = 60.0 / cadence  # seconds per step
            elif avg_stance > 0 and avg_swing > 0:
                step_time = avg_stance + avg_swing
            else:
                step_time = 0.0
            
            return {
                'cadence': float(cadence),
                'step_time': float(step_time),
                'stance_time': float(avg_stance),
                'step_symmetry': float(step_symmetry),
                'gait_balance': float(gait_balance)
            }
            
        except Exception as e:
            print(f"Error calculating gait metrics: {e}")
            return {
                'cadence': 0.0,
                'swing_time': 0.0,
                'stance_time': 0.0,
                'step_symmetry': 0.0,
                'gait_balance': 0.0
            }
    
    def send_to_blynk(self, ratings: Dict[str, str], metrics: Dict[str, float]) -> bool:
        """
        Send pressure ratings and gait metrics to Blynk via HTTP API
        
        Args:
            ratings: Dictionary with pressure ratings
            metrics: Dictionary with gait metrics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import time
            base_url = f"{self.api_url}/update?token={self.auth_token}"
            
            # Send each value individually with small delays
            updates = [
                (PIN_CADENCE, round(metrics.get('cadence', 0.0), 1)),
                (PIN_STEP_TIME, round(metrics.get('step_time', 0.0), 2)),
                (PIN_STANCE_TIME, round(metrics.get('stance_time', 0.0), 2)),
                (PIN_STEP_SYMMETRY, round(metrics.get('step_symmetry', 0.0), 1)),
                (PIN_GAIT_BALANCE, round(metrics.get('gait_balance', 0.0), 1)),
                (PIN_BIGTOE_RATING, ratings.get('bigToe', 'Normal')),
                (PIN_PINKYTOE_RATING, ratings.get('pinkyToe', 'Normal')),
                (PIN_METAOUT_RATING, ratings.get('metaOut', 'Normal')),
                (PIN_METAIN_RATING, ratings.get('metaIn', 'Normal')),
                (PIN_HEEL_RATING, ratings.get('heel', 'Normal')),
            ]
            
            success_count = 0
            for pin, value in updates:
                url = f"{base_url}&v{pin}={value}"
                try:
                    response = requests.get(url, timeout=3, allow_redirects=True)
                    if response.status_code in [200, 308]:
                        success_count += 1
                    time.sleep(0.1)  # Small delay between requests
                except:
                    pass
            
            if success_count >= 5:  # At least the key metrics sent
                print(f"✓ Sent to Blynk ({success_count}/10) - Cadence: {metrics.get('cadence', 0):.1f}, Balance: {metrics.get('gait_balance', 0):.1f}")
                return True
            else:
                print(f"⚠ Partial send to Blynk ({success_count}/10 values)")
                return False
            
        except Exception as e:
            print(f"✗ Failed to send to Blynk: {e}")
            return False
    
    def send_notification(self, title: str, message: str) -> bool:
        """
        Send a mobile push notification via Blynk's logEvent API.
        This sends an actual push notification to the user's phone.
        
        Note: You must create an event named "gait_evaluation" in Blynk Console:
        1. Go to https://blynk.cloud
        2. Navigate to Settings > Events
        3. Create event with code "gait_evaluation"
        
        Args:
            title: Notification title (not used by logEvent, but kept for compatibility)
            message: Notification message body (limited to 255 characters)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Truncate message to 255 characters (Blynk limit)
            short_message = message[:255] if len(message) > 255 else message
            
            # Use Blynk's logEvent API for mobile push notifications
            # Event code must be created in Blynk Console first
            url = f"{self.api_url}/logEvent?token={self.auth_token}&code=gait_evaluation&description={short_message}"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code in [200, 202, 204]:
                print(f"✓ Mobile notification sent: {short_message[:50]}...")
                return True
            else:
                print(f"⚠ Notification failed ({response.status_code}): {response.text}")
                print(f"   Make sure event 'gait_evaluation' exists in Blynk Console")
                return False
                
        except requests.Timeout:
            print(f"✗ Notification request timed out")
            return False
        except Exception as e:
            print(f"✗ Failed to send notification: {e}")
            return False
    
    def send_evaluation_report(self, patient_name: str, evaluation_summary: Dict) -> bool:
        """
        Send a concise evaluation report as a mobile push notification.
        Message is kept under 255 characters for Blynk compatibility.
        
        Args:
            patient_name: Patient name for the report
            evaluation_summary: Dictionary with evaluation data:
                - status: "GOOD", "NEEDS_ATTENTION", "CRITICAL"
                - cadence: Cadence value
                - step_symmetry: Step symmetry percentage
                - stance_time: Stance time
                - action_plan: List of action items (optional)
                
        Returns:
            True if notification sent, False otherwise
        """
        try:
            # Extract data with defaults
            status = evaluation_summary.get('status', 'PENDING')
            cadence = evaluation_summary.get('cadence', 0)
            symmetry = evaluation_summary.get('step_symmetry', 0)
            stance_time = evaluation_summary.get('stance_time', 0)
            
            # Format emoji based on status
            status_emoji = {
                'GOOD': '✅',
                'NEEDS_ATTENTION': '⚠️',
                'CRITICAL': '🔴',
                'PENDING': 'ℹ️'
            }.get(status, '📋')
            
            # Create short, concise message (under 255 chars)
            message = f"{status_emoji} {patient_name}: {status}\nCadence: {cadence:.1f} spm | Symmetry: {symmetry:.1f}% | Stance: {stance_time:.2f}s"
            
            # Send via Blynk notification
            return self.send_notification("Gait Evaluation", message)
            
        except Exception as e:
            print(f"✗ Failed to generate evaluation report: {e}")
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
_blynk_http_service: Optional[BlynkHttpService] = None

def get_blynk_http_service() -> BlynkHttpService:
    """Get or create BlynkHttpService singleton"""
    global _blynk_http_service
    if _blynk_http_service is None:
        _blynk_http_service = BlynkHttpService()
        _blynk_http_service.connect()
    return _blynk_http_service
