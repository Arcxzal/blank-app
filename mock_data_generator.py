"""
Mock Data Generator for Demo Patient
Generates realistic synthetic gait data for testing and demonstration purposes
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_gait_cycle(duration_sec=1.0, sampling_rate=25):
    """
    Generate one realistic gait cycle
    
    Args:
        duration_sec: Duration of one gait cycle in seconds
        sampling_rate: Samples per second (Hz)
        
    Returns:
        Dictionary with pressure values for all sensors
    """
    num_samples = int(duration_sec * sampling_rate)
    time = np.linspace(0, 1, num_samples)
    
    # Gait phases (normalized 0-1):
    # 0.0-0.15: Heel strike
    # 0.15-0.35: Mid-stance (flat foot)
    # 0.35-0.50: Push-off (toe dominant)
    # 0.50-1.0: Swing phase (minimal pressure)
    
    def pressure_pattern(t, peak_time, width, peak_pressure):
        """Gaussian-like pressure pattern centered at peak_time"""
        return peak_pressure * np.exp(-((t - peak_time) ** 2) / (2 * width ** 2))
    
    # Right foot patterns
    heel = (
        pressure_pattern(time, 0.10, 0.08, 55) +  # Heel strike
        pressure_pattern(time, 0.25, 0.12, 35) +  # Mid-stance
        np.random.normal(0, 0.3, num_samples)  # Minimal noise for smooth curves
    )
    
    meta_in = (
        pressure_pattern(time, 0.25, 0.10, 45) +  # Mid-stance
        pressure_pattern(time, 0.40, 0.08, 50) +  # Push-off prep
        np.random.normal(0, 0.3, num_samples)
    )
    
    meta_out = (
        pressure_pattern(time, 0.25, 0.10, 40) +  # Mid-stance
        pressure_pattern(time, 0.40, 0.08, 45) +  # Push-off prep
        np.random.normal(0, 0.3, num_samples)
    )
    
    big_toe = (
        pressure_pattern(time, 0.42, 0.08, 48) +  # Push-off
        np.random.normal(0, 0.3, num_samples)
    )
    
    pinky_toe = (
        pressure_pattern(time, 0.42, 0.08, 38) +  # Push-off (less than big toe)
        np.random.normal(0, 0.3, num_samples)
    )
    
    # Left foot patterns (slightly offset and with minor asymmetry)
    phase_shift = 0.5  # Left foot is half cycle behind
    time_l = (time + phase_shift) % 1.0
    
    heel_l = (
        pressure_pattern(time_l, 0.10, 0.08, 52) +  # Slightly different
        pressure_pattern(time_l, 0.25, 0.12, 33) +
        np.random.normal(0, 0.3, num_samples)
    )
    
    meta_in_l = (
        pressure_pattern(time_l, 0.25, 0.10, 43) +
        pressure_pattern(time_l, 0.40, 0.08, 48) +
        np.random.normal(0, 0.3, num_samples)
    )
    
    meta_out_l = (
        pressure_pattern(time_l, 0.25, 0.10, 38) +
        pressure_pattern(time_l, 0.40, 0.08, 43) +
        np.random.normal(0, 0.3, num_samples)
    )
    
    big_toe_l = (
        pressure_pattern(time_l, 0.42, 0.08, 46) +
        np.random.normal(0, 0.3, num_samples)
    )
    
    pinky_toe_l = (
        pressure_pattern(time_l, 0.42, 0.08, 36) +
        np.random.normal(0, 0.3, num_samples)
    )
    
    # Ensure non-negative values
    return {
        'heel': np.maximum(heel, 0),
        'meta_in': np.maximum(meta_in, 0),
        'meta_out': np.maximum(meta_out, 0),
        'big_toe': np.maximum(big_toe, 0),
        'pinky_toe': np.maximum(pinky_toe, 0),
        'heel_l': np.maximum(heel_l, 0),
        'meta_in_l': np.maximum(meta_in_l, 0),
        'meta_out_l': np.maximum(meta_out_l, 0),
        'big_toe_l': np.maximum(big_toe_l, 0),
        'pinky_toe_l': np.maximum(pinky_toe_l, 0),
    }


def generate_mock_data(num_cycles=10, cadence=120, sampling_rate=25):
    """
    Generate complete mock gait data for multiple cycles
    
    Args:
        num_cycles: Number of gait cycles to generate
        cadence: Steps per minute (typical walking: 100-120)
        sampling_rate: Samples per second
        
    Returns:
        pandas DataFrame with columns matching PressureSample model
    """
    # Calculate cycle duration from cadence
    cycle_duration = 60.0 / cadence  # seconds per step
    
    all_data = []
    current_time = datetime.now() - timedelta(seconds=num_cycles * cycle_duration)
    
    for cycle in range(num_cycles):
        # Generate one cycle
        cycle_data = generate_gait_cycle(cycle_duration, sampling_rate)
        num_samples = len(cycle_data['heel'])
        
        # Create timestamps
        timestamps = [
            current_time + timedelta(seconds=i / sampling_rate)
            for i in range(num_samples)
        ]
        
        # Build DataFrame for this cycle
        for i in range(num_samples):
            all_data.append({
                'device_id': 'DEMO',
                'timestamp': timestamps[i],
                'bigtoepressure': cycle_data['big_toe'][i],
                'pinkytoepressure': cycle_data['pinky_toe'][i],
                'metaoutpressure': cycle_data['meta_out'][i],
                'metainpressure': cycle_data['meta_in'][i],
                'heelpressure': cycle_data['heel'][i],
                'bigtoepressure_l': cycle_data['big_toe_l'][i],
                'pinkytoepressure_l': cycle_data['pinky_toe_l'][i],
                'metaoutpressure_l': cycle_data['meta_out_l'][i],
                'metainpressure_l': cycle_data['meta_in_l'][i],
                'heelpressure_l': cycle_data['heel_l'][i],
                'mux': 0,
            })
        
        current_time += timedelta(seconds=cycle_duration)
    
    df = pd.DataFrame(all_data)
    return df


def generate_extended_mock_data(duration_minutes=5, cadence=115, sampling_rate=25):
    """
    Generate extended mock data for longer time periods
    
    Args:
        duration_minutes: Total duration in minutes
        cadence: Steps per minute
        sampling_rate: Samples per second
        
    Returns:
        pandas DataFrame with extended mock data
    """
    total_steps = int(duration_minutes * cadence)
    return generate_mock_data(num_cycles=total_steps, cadence=cadence, sampling_rate=sampling_rate)


if __name__ == "__main__":
    # Test the generator
    print("Generating demo data...")
    df = generate_mock_data(num_cycles=5, cadence=120)
    print(f"\nGenerated {len(df)} samples")
    print(f"\nFirst few rows:")
    print(df.head())
    print(f"\nData statistics:")
    print(df.describe())
