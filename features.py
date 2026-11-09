import numpy as np


def zero_crossings(window, threshold=1e-6):
    """Vectorized count of zero crossings with noise threshold deadband.
    
    A zero crossing occurs when consecutive non-zero samples have opposite signs.
    Samples within [-threshold, threshold] are suppressed to prevent baseline noise triggers.
    """
    w = np.asarray(window, dtype=float)
    w_clean = np.where(np.abs(w) < threshold, 0.0, w)
    signs = np.sign(w_clean)
    s_curr = signs[1:]
    s_prev = signs[:-1]
    crossings = (s_curr != 0) & (s_prev != 0) & (s_curr != s_prev)
    return int(np.sum(crossings))


def slope_sign_changes(window, threshold=1e-6):
    """Vectorized count of slope sign changes (SSC) with noise threshold deadband.
    
    Identifies local extrema where slope reverses sign and the difference
    exceeds the noise threshold.
    """
    w = np.asarray(window, dtype=float)
    diffs = np.diff(w)
    d_curr = diffs[1:]
    d_prev = diffs[:-1]
    flips = (d_curr * d_prev < 0) & (np.abs(d_curr - d_prev) > threshold)
    return int(np.sum(flips))


def mean_absolute_value(window):
    """Mean Absolute Value (MAV): primary indicator of muscle contraction amplitude."""
    return float(np.mean(np.abs(window)))


def waveform_length(window):
    """Waveform Length (WL): cumulative signal length measuring amplitude and frequency."""
    return float(np.sum(np.abs(np.diff(window))))


def rms(window):
    """Root Mean Square (RMS): relates to motor unit recruitment and signal power."""
    return float(np.sqrt(np.mean(np.square(window))))


def variance(window):
    """Signal variance (VAR): second-order central moment reflecting power."""
    return float(np.var(window))


def extract_channel_features(window):
    """Extract standard Hudgins time-domain features + RMS and Variance for one channel."""
    window = np.asarray(window, dtype=float)
    return {
        "zc": zero_crossings(window),
        "ssc": slope_sign_changes(window),
        "mav": mean_absolute_value(window),
        "wl": waveform_length(window),
        "rms": rms(window),
        "var": variance(window),
    }


def extract_features(channels):
    """Extract ordered 6-feature vector across all provided EMG channels.
    
    Args:
        channels: list of 1D numpy arrays, one per physical EMG electrode channel.
        
    Returns:
        List of float feature values of length (6 * num_channels).
    """
    row = []
    for ch in channels:
        feats = extract_channel_features(ch)
        row.extend([feats["zc"], feats["ssc"], feats["mav"], feats["wl"], feats["rms"], feats["var"]])
    return row

