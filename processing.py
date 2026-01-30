import numpy as np
from scipy.signal import savgol_filter, find_peaks

FS = 25  # sampling frequency (Hz)


# Use filtered but non-normalized data when absolute load magnitude matters (e.g. total load, step detection via total load).
# Use filtered and normalized data when relative contributions matter (e.g., load distribution, COP, relative pressure analysis).


#df_filtered = preprocess_signals(df)
# df_norm = normalize_to_percent_load(df_filtered)

# df_filtered["total_load"] = df_filtered[['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']].sum(axis=1)
# steps = detect_steps(df_filtered["total_load"])
# heel_strikes, toe_offs = detect_heel_strike_toe_off(df_filtered)
# metrics = compute_gait_metrics(heel_strikes, toe_offs)

#metrics["stance_times"]
#metrics["swing_times"]
#metrics["cadence"]


# -------------------------------
# Savitzky–Golay filtering
# -------------------------------
def savgol_filter_signal(signal, fs=FS):
    """
    Apply Savitzky–Golay filter to one sensor channel.
    Window length is ~0.5 s and enforced to be valid.
    """
    signal = np.asarray(signal)

    window_length = int(0.5 * fs)  # ~0.5 s
    if window_length % 2 == 0:
        window_length += 1

    if len(signal) < window_length:
        return signal

    return savgol_filter(signal, window_length=window_length, polyorder=3)


def preprocess_signals(df):
    """
    Input: DataFrame with columns for right and left foot sensors
    Output: filtered DataFrame (non-destructive)
    """
    filtered = df.copy()

    # Right foot sensors
    right_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    # Left foot sensors
    left_cols = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
    
    # Process all available columns
    for col in right_cols + left_cols:
        if col in filtered.columns:
            filtered[col] = savgol_filter_signal(filtered[col].values)

    return filtered


# -------------------------------
# Load normalization
# -------------------------------
def normalize_to_percent_load(df):
    """
    Normalize sensor loads to % of total load per frame.
    Returns a new DataFrame with normalized values for both feet.
    """
    norm = df.copy()
    
    # Right foot sensors
    right_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    # Left foot sensors
    left_cols = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
    
    # Normalize right foot
    right_available = [col for col in right_cols if col in norm.columns]
    if right_available:
        total_load_r = norm[right_available].sum(axis=1, skipna=True)
        total_load_r = total_load_r.replace(0, np.nan)  # avoid divide-by-zero
        for col in right_available:
            norm[col] = (norm[col] / total_load_r) * 100.0
    
    # Normalize left foot
    left_available = [col for col in left_cols if col in norm.columns]
    if left_available:
        total_load_l = norm[left_available].sum(axis=1, skipna=True)
        total_load_l = total_load_l.replace(0, np.nan)  # avoid divide-by-zero
        for col in left_available:
            norm[col] = (norm[col] / total_load_l) * 100.0

    return norm


# -------------------------------
# Step / stance detection
# -------------------------------
def detect_steps(total_load, fs=FS):
    """
    Detect stance phases using peaks in total load.
    Uses adaptive distance based on detected step frequency.
    Returns indices of detected steps.
    """
    total_load = np.asarray(total_load)

    if total_load.size == 0:
        return np.array([])

    if np.nanmax(total_load) == 0:
        return np.array([])

    # Threshold empirically tuned: 30% of max total load (observed: 1299-4331)
    threshold = max(1299, 0.30 * np.nanmax(total_load))

    # Use adaptive distance instead of fixed 0.5s
    # Start with conservative estimate: minimum 0.3s between steps (200 bpm max cadence)
    # This captures faster walking while avoiding multiple peaks from single step
    min_distance = int(0.3 * fs)  # ~7-8 samples at 25 Hz
    
    peaks, _ = find_peaks(
        total_load,
        height=threshold,
        distance=min_distance
    )

    return peaks


def compute_total_load(df_filtered, foot='right'):
    """
    Compute total load for a specific foot.
    
    Args:
        df_filtered: DataFrame with filtered pressure data
        foot: 'right' or 'left' foot
    
    Returns:
        total_load: array of total load values
    """
    if foot.lower() == 'left':
        sensor_cols = ['bigToe_L', 'pinkyToe_L', 'metaOut_L', 'metaIn_L', 'heel_L']
    else:  # default to right
        sensor_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    
    # Sum only available columns
    available_cols = [col for col in sensor_cols if col in df_filtered.columns]
    
    if not available_cols:
        return np.zeros(len(df_filtered))
    
    return df_filtered[available_cols].sum(axis=1, skipna=True).values

    return peaks


# -------------------------------
# Heel strike / Toe off detection
# -------------------------------

def detect_heel_strike_toe_off(df_filtered, fs=FS, foot='right'):
    """
    Detect heel-strike and toe-off events from filtered pressure signals.

    Heel-strike:
        - Heel sensor rises above a threshold
    Toe-off:
        - Forefoot load drops below a threshold after stance

    Args:
        df_filtered: DataFrame with pressure data
        fs: sampling frequency (Hz)
        foot: 'right' or 'left' foot

    Returns:
        heel_strikes: indices of heel-strike events
        toe_offs: indices of toe-off events
    """
    
    # Select sensors based on foot
    if foot.lower() == 'left':
        heel_col = "heel_L"
        toe_cols = ["bigToe_L", "metaOut_L", "metaIn_L"]
    else:  # default to right
        heel_col = "heel"
        toe_cols = ["bigToe", "metaOut", "metaIn"]
    
    # Check if columns exist
    if heel_col not in df_filtered.columns:
        return np.array([]), np.array([])
    
    heel = df_filtered[heel_col].values
    
    # Sum available forefoot sensors
    forefoot = np.zeros(len(df_filtered))
    for col in toe_cols:
        if col in df_filtered.columns:
            forefoot += df_filtered[col].values

    # --- Adaptive thresholds (empirically tuned from real walk data) ---
    # Heel: treat any non-zero reading as a valid heel-strike trigger
    # Keep adaptive scaling but enforce an absolute minimum of 1
    heel_max = np.nanmax(heel) if heel.size > 0 and np.nanmax(heel) > 0 else 1
    heel_thresh = max(1, 0.30 * heel_max)  # absolute min: 1
    # Forefoot: max observed 3720, using 25% threshold
    forefoot_max = np.nanmax(forefoot) if forefoot.size > 0 and np.nanmax(forefoot) > 0 else 1
    forefoot_thresh = max(930, 0.25 * forefoot_max)  # empirical min: 930

    heel_strikes = []
    toe_offs = []

    in_stance = False

    for i in range(1, len(df_filtered)):
        # Heel-strike: heel crosses threshold upward
        if not in_stance:
            if heel[i-1] < heel_thresh and heel[i] >= heel_thresh:
                heel_strikes.append(i)
                in_stance = True

        # Toe-off: forefoot drops below threshold downward
        else:
            if forefoot[i-1] >= forefoot_thresh and forefoot[i] < forefoot_thresh:
                toe_offs.append(i)
                in_stance = False

    return np.array(heel_strikes), np.array(toe_offs)


# -------------------------------
# Stance, Swing time + Cadence detection
# -------------------------------

def compute_gait_metrics(heel_strikes, toe_offs, fs=FS):
    """
    Compute stance time, swing time, and cadence from gait events.

    Inputs:
        heel_strikes : array of indices (initial contact)
        toe_offs     : array of indices (end of stance)
        fs           : sampling frequency (Hz)

    Returns:
        metrics : dict containing
            - stance_times (seconds)
            - swing_times (seconds)
            - cadence (steps per minute)
    """

    heel_strikes = np.asarray(heel_strikes)
    toe_offs = np.asarray(toe_offs)

    stance_times = []
    swing_times = []

    # Pair heel-strike -> toe-off (stance)
    for hs in heel_strikes:
        # find first toe-off after this heel-strike
        to_candidates = toe_offs[toe_offs > hs]
        if len(to_candidates) == 0:
            continue

        to = to_candidates[0]
        stance_times.append((to - hs) / fs)

    # Pair toe-off -> next heel-strike (swing)
    for to in toe_offs:
        hs_candidates = heel_strikes[heel_strikes > to]
        if len(hs_candidates) == 0:
            continue

        hs_next = hs_candidates[0]
        swing_times.append((hs_next - to) / fs)

    # Cadence (steps per minute)
    if len(heel_strikes) > 1:
        step_intervals = np.diff(heel_strikes) / fs
        cadence = 60.0 / np.mean(step_intervals)
    else:
        cadence = np.nan

    return {
        "stance_times": np.array(stance_times),
        "swing_times": np.array(swing_times),
        "cadence": cadence
    }

