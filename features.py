import numpy as np


def zero_crossings(window, threshold=1e-6):
    signs = np.sign(window)
    signs[np.abs(window) < threshold] = 0
    crossings = 0
    for i in range(1, len(signs)):
        if signs[i] != 0 and signs[i - 1] != 0 and signs[i] != signs[i - 1]:
            crossings += 1
    return crossings


def slope_sign_changes(window, threshold=1e-6):
    diffs = np.diff(window)
    count = 0
    for i in range(1, len(diffs)):
        if diffs[i] * diffs[i - 1] < 0 and abs(diffs[i] - diffs[i - 1]) > threshold:
            count += 1
    return count


def mean_absolute_value(window):
    return float(np.mean(np.abs(window)))


def waveform_length(window):
    return float(np.sum(np.abs(np.diff(window))))


def rms(window):
    return float(np.sqrt(np.mean(np.square(window))))


def variance(window):
    return float(np.var(window))


def extract_channel_features(window):
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
    """channels: list of raw sample arrays, one per EMG channel."""
    row = []
    for ch in channels:
        feats = extract_channel_features(ch)
        row.extend([feats["zc"], feats["ssc"], feats["mav"], feats["wl"], feats["rms"], feats["var"]])
    return row
