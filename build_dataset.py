"""
Turns the raw UCI EMG gesture recordings into a windowed, labeled feature
dataset ready for training. Each file is a continuous recording with a
class label per sample; this script slices contiguous same-label runs into
fixed-size windows and extracts features per window using features.py.

Label mapping (from the UCI 'EMG Data for Gestures' dataset):
  0 - unmarked           -> dropped
  1 - hand at rest       -> rest
  2 - hand clenched fist -> grasp
  3 - wrist flexion      -> flexion
  4 - wrist extension    -> extension
  5 - radial deviation   -> dropped (not one of the four target gestures)
  6 - ulnar deviation    -> dropped
"""

import glob

import numpy as np
import pandas as pd

from features import extract_features

LABEL_MAP = {1: "rest", 2: "grasp", 3: "flexion", 4: "extension"}
WINDOW_SIZE = 200  # samples per window
STEP = 100  # 50% overlap

CHANNEL_COLS = [f"channel{i}" for i in range(1, 9)]


def load_subject_file(path):
    df = pd.read_csv(path, sep="\t")
    df.columns = [c.strip() for c in df.columns]
    return df


def windows_for_run(df_run, label, run_key):
    """Slide fixed windows over one contiguous same-label run.

    run_key is carried through to every window from this run so that, at
    train/test split time, overlapping windows from the same gesture
    repetition can be kept together instead of leaking across the split.
    """
    rows = []
    values = df_run[CHANNEL_COLS].values
    n = len(values)
    for start in range(0, n - WINDOW_SIZE + 1, STEP):
        window = values[start:start + WINDOW_SIZE]
        channels = [window[:, i] for i in range(window.shape[1])]
        feats = extract_features(channels)
        rows.append(feats + [label, run_key])
    return rows


def build_from_file(path):
    subject = path.split("/")[-1].replace(".txt", "")
    df = load_subject_file(path)
    df = df[df["class"].isin(LABEL_MAP.keys())].reset_index(drop=True)

    all_rows = []
    # group contiguous runs of the same class (gestures are performed in blocks)
    df["run_id"] = (df["class"] != df["class"].shift()).cumsum()
    for run_id, run_df in df.groupby("run_id"):
        label = LABEL_MAP[run_df["class"].iloc[0]]
        run_key = f"{subject}_run{run_id}"
        all_rows.extend(windows_for_run(run_df, label, run_key))
    return all_rows


def main():
    files = sorted(glob.glob("data/subject_*.txt"))
    print(f"Found {len(files)} subject files: {files}")

    columns = []
    for ch in range(1, 9):
        columns += [f"ch{ch}_zc", f"ch{ch}_ssc", f"ch{ch}_mav", f"ch{ch}_wl", f"ch{ch}_rms", f"ch{ch}_var"]
    columns.append("label")
    columns.append("run_id")

    all_rows = []
    for path in files:
        rows = build_from_file(path)
        print(f"  {path}: {len(rows)} windows")
        all_rows.extend(rows)

    out = pd.DataFrame(all_rows, columns=columns)
    out.to_csv("data/emg_gesture_dataset.csv", index=False)
    print(f"\nTotal windows: {len(out)}")
    print(out["label"].value_counts())


if __name__ == "__main__":
    main()
