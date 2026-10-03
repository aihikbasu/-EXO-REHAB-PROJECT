"""
Novelty #1: Cross-subject generalization + calibration.

EMG signal characteristics vary significantly between people (electrode
placement, muscle mass, skin impedance), so a classifier trained on some
subjects often performs worse on a completely new, unseen subject. This
script measures that gap directly with leave-one-subject-out (LOSO)
cross-validation, then tests whether a simple per-subject calibration step
(z-score normalizing each subject's own features before classification)
closes it.

Calibration here means: for the held-out test subject, compute feature
mean/std from a small labeled calibration set (e.g. their first repetition
of each gesture) and use it to normalize their remaining data, instead of
using the training subjects' global feature statistics.
"""

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

FEATURE_COLS = None  # set after loading


def load_data(path="data/emg_gesture_dataset.csv"):
    df = pd.read_csv(path)
    global FEATURE_COLS
    FEATURE_COLS = [c for c in df.columns if c not in ("label", "run_id", "subject_id")]
    return df


def run_without_calibration(df, subject, model_fn):
    """Standard LOSO: train on all other subjects, test on this one,
    using the training subjects' feature scaling for everything."""
    train_df = df[df["subject_id"] != subject]
    test_df = df[df["subject_id"] == subject]

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_df[FEATURE_COLS])
    X_test = scaler.transform(test_df[FEATURE_COLS])

    model = model_fn()
    model.fit(X_train, train_df["label"])
    preds = model.predict(X_test)
    return accuracy_score(test_df["label"], preds)


def run_with_calibration(df, subject, model_fn, calibration_runs_per_class=1):
    """LOSO with per-subject calibration: a small slice of the held-out
    subject's own data (their first repetition of each gesture) is used
    to compute subject-specific feature normalization, applied before
    classifying the rest of their data."""
    train_df = df[df["subject_id"] != subject]
    test_subject_df = df[df["subject_id"] == subject]

    # pick calibration runs: first N run_ids per class for this subject
    calib_runs = (
        test_subject_df.groupby("label")["run_id"]
        .apply(lambda s: s.unique()[:calibration_runs_per_class])
    )
    calib_run_ids = set(r for runs in calib_runs for r in runs)

    calib_df = test_subject_df[test_subject_df["run_id"].isin(calib_run_ids)]
    eval_df = test_subject_df[~test_subject_df["run_id"].isin(calib_run_ids)]

    if len(eval_df) == 0:
        return None  # not enough data to hold out an eval set

    # subject-specific scaling, fit on the subject's own calibration slice
    subj_scaler = StandardScaler()
    subj_scaler.fit(calib_df[FEATURE_COLS])

    X_train = subj_scaler.transform(train_df[FEATURE_COLS])
    X_eval = subj_scaler.transform(eval_df[FEATURE_COLS])

    model = model_fn()
    model.fit(X_train, train_df["label"])
    preds = model.predict(X_eval)
    return accuracy_score(eval_df["label"], preds)


def main():
    df = load_data()
    subjects = sorted(df["subject_id"].unique())

    def make_svm():
        return SVC(kernel="rbf", C=10, gamma="scale")

    results = {"subject": [], "no_calibration": [], "with_calibration": []}

    for subject in subjects:
        acc_plain = run_without_calibration(df, subject, make_svm)
        acc_calib = run_with_calibration(df, subject, make_svm)

        results["subject"].append(str(subject))
        results["no_calibration"].append(float(acc_plain))
        results["with_calibration"].append(float(acc_calib) if acc_calib is not None else None)

        calib_str = f"{acc_calib:.3f}" if acc_calib is not None else "n/a"
        print(f"Subject {subject}: no-calibration={acc_plain:.3f}  with-calibration={calib_str}")

    valid_calib = [a for a in results["with_calibration"] if a is not None]
    summary = {
        "mean_no_calibration": float(np.mean(results["no_calibration"])),
        "mean_with_calibration": float(np.mean(valid_calib)),
        "per_subject": results,
    }

    print("\n=== Summary ===")
    print(f"Mean LOSO accuracy, no calibration:   {summary['mean_no_calibration']:.3f}")
    print(f"Mean LOSO accuracy, with calibration: {summary['mean_with_calibration']:.3f}")

    with open("loso_results.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
