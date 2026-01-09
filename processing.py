import numpy as np
from scipy.signal import savgol_filter, find_peaks

FS = 25  # sampling frequency (Hz)


# Use filtered but non-normalized data when absolute load magnitude matters (e.g. total load, step detection via total load).
# Use filtered and normalized data when relative contributions matter (e.g., load distribution, COP, relative pressure analysis).


# df_filtered = preprocess_signals(df)
# df_norm = normalize_to_percent_load(df_filtered)

# df_filtered["total_load"] = df_filtered[['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']].sum(axis=1)
# steps = detect_steps(df_filtered["total_load"])
# heel_strikes, toe_offs = detect_heel_strike_toe_off(df_filtered)
# metrics = compute_gait_metrics(heel_strikes, toe_offs)

# metrics["stance_times"]
# metrics["swing_times"]
# metrics["cadence"]


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
    Input: DataFrame with columns ['timestamp','s1'...'s5']
    Output: filtered DataFrame (non-destructive)
    """
    filtered = df.copy()

    for col in ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']:
        filtered[col] = savgol_filter_signal(filtered[col].values)

    return filtered


# -------------------------------
# Load normalization
# -------------------------------
def normalize_to_percent_load(df):
    """
    Normalize sensor loads to % of total load per frame.
    Returns a new DataFrame.
    """
    sensor_cols = ['bigToe', 'pinkyToe', 'metaOut', 'metaIn', 'heel']
    norm = df.copy()

    total_load = norm[sensor_cols].sum(axis=1, skipna=True)
    total_load = total_load.replace(0, np.nan)  # avoid divide-by-zero

    for col in sensor_cols:
        norm[col] = (norm[col] / total_load) * 100.0

    return norm


# -------------------------------
# Step / stance detection
# -------------------------------
def detect_steps(total_load, fs=FS):
    """
    Detect stance phases using peaks in total load.
    Returns indices of detected steps.
    """
    total_load = np.asarray(total_load)

    if total_load.size == 0:
        return np.array([])

    if np.nanmax(total_load) == 0:
        return np.array([])

    threshold = 0.2 * np.nanmax(total_load)

    peaks, _ = find_peaks(
        total_load,
        height=threshold,
        distance=int(0.4 * fs)  # minimum 0.4 s between steps
    )

    return peaks


# -------------------------------
# Heel strike / Toe off detection
# -------------------------------

def detect_heel_strike_toe_off(df_filtered, fs=FS):
    """
    Detect heel-strike and toe-off events from filtered pressure signals.

    Heel-strike:
        - Heel sensor rises above a threshold
    Toe-off:
        - Forefoot load drops below a threshold after stance

    Returns:
        heel_strikes: indices of heel-strike events
        toe_offs: indices of toe-off events
    """

    heel = df_filtered["heel"].values
    forefoot = (
        df_filtered["bigToe"].values +
        df_filtered["metaOut"].values +
        df_filtered["metaIn"].values
    )

    # --- Adaptive thresholds ---
    heel_thresh = 0.15 * np.nanmax(heel)
    forefoot_thresh = 0.15 * np.nanmax(forefoot)

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

