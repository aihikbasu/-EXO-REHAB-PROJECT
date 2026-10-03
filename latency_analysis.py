"""
Novelty #2: Real-time feasibility analysis.

A rehabilitation exoskeleton needs classification fast enough to keep up
with the device's control loop, not just high offline accuracy. This
measures actual per-window latency (feature extraction + classification)
for SVM and Random Forest, and checks whether that latency fits inside the
window step time -- i.e. whether the pipeline could in principle keep up
with the real-time EMG stream at this window/step size.
"""

import json
import time
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from build_dataset import STEP, WINDOW_SIZE
from features import extract_features

ASSUMED_SAMPLE_RATE_HZ = 200  # matches the Myo-armband-derived dataset's approx rate
STEP_TIME_MS = (STEP / ASSUMED_SAMPLE_RATE_HZ) * 1000


def load_data(path="data/emg_gesture_dataset.csv"):
    df = pd.read_csv(path)
    X = df.drop(columns=["label", "run_id", "subject_id"])
    y = df["label"]
    groups = df["run_id"]
    return X, y, groups


def measure_feature_extraction_latency(n_trials=200, n_channels=8):
    """Time extract_features() on synthetic windows of the real window size."""
    rng = np.random.default_rng(0)
    times = []
    for _ in range(n_trials):
        channels = [rng.normal(0, 1, WINDOW_SIZE) for _ in range(n_channels)]
        start = time.perf_counter()
        extract_features(channels)
        times.append((time.perf_counter() - start) * 1000)
    return times


def measure_classifier_latency(model, X_single_rows, n_trials=200):
    times = []
    for i in range(min(n_trials, len(X_single_rows))):
        row = X_single_rows[i:i + 1]
        start = time.perf_counter()
        model.predict(row)
        times.append((time.perf_counter() - start) * 1000)
    return times


def main():
    X, y, groups = load_data()

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train = y.iloc[train_idx]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    svm = SVC(kernel="rbf", C=10, gamma="scale")
    svm.fit(X_train_scaled, y_train)

    rf = RandomForestClassifier(n_estimators=200, random_state=42)
    rf.fit(X_train, y_train)

    feat_times = measure_feature_extraction_latency()
    svm_times = measure_classifier_latency(svm, X_test_scaled)
    rf_times = measure_classifier_latency(rf, X_test.values)

    report = {
        "assumed_sample_rate_hz": ASSUMED_SAMPLE_RATE_HZ,
        "window_size_samples": WINDOW_SIZE,
        "step_size_samples": STEP,
        "step_time_ms": round(STEP_TIME_MS, 2),
        "feature_extraction_ms": {
            "mean": round(float(np.mean(feat_times)), 3),
            "p95": round(float(np.percentile(feat_times, 95)), 3),
        },
        "svm_inference_ms": {
            "mean": round(float(np.mean(svm_times)), 3),
            "p95": round(float(np.percentile(svm_times, 95)), 3),
        },
        "random_forest_inference_ms": {
            "mean": round(float(np.mean(rf_times)), 3),
            "p95": round(float(np.percentile(rf_times, 95)), 3),
        },
    }

    for name, times in (("SVM", svm_times), ("Random Forest", rf_times)):
        total_mean = report["feature_extraction_ms"]["mean"] + np.mean(times)
        fits = total_mean < STEP_TIME_MS
        report[f"{name.lower().replace(' ', '_')}_real_time_feasible"] = bool(fits)
        print(f"{name}: feature extraction + inference = {total_mean:.3f} ms "
              f"(budget: {STEP_TIME_MS:.1f} ms per step) -> "
              f"{'FITS' if fits else 'TOO SLOW'}")

    with open("latency_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nNote: these timings were measured on this development machine, not the "
          f"target Raspberry Pi. They establish feasibility in principle; actual Pi "
          f"timings should be re-measured once hardware is available.")


if __name__ == "__main__":
    main()
