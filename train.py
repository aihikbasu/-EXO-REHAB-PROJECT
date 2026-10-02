import json

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, classification_report
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def load_data(path="data/emg_gesture_dataset.csv"):
    df = pd.read_csv(path)
    X = df.drop(columns=["label", "run_id"])
    y = df["label"]
    groups = df["run_id"]
    return X, y, groups


def train_and_evaluate(model, name, X_train, X_test, y_train, y_test, labels):
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print(f"\n=== {name} ===")
    print(f"Accuracy: {acc:.3f}")
    print(classification_report(y_test, preds, labels=labels))

    disp = ConfusionMatrixDisplay.from_predictions(
        y_test, preds, labels=labels, xticks_rotation=30,
    )
    disp.figure_.set_size_inches(6, 5)
    disp.figure_.tight_layout()
    disp.figure_.savefig(f"confusion_matrix_{name.lower().replace(' ', '_')}.png", dpi=150)
    plt.close(disp.figure_)

    return acc


def main():
    X, y, groups = load_data()
    labels = sorted(y.unique())

    # Split by gesture repetition (run), not by individual window -- windows
    # from the same run overlap heavily and would leak across train/test if
    # split independently, inflating accuracy artificially.
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    results = {}

    svm = SVC(kernel="rbf", C=10, gamma="scale")
    results["svm"] = train_and_evaluate(svm, "SVM", X_train_scaled, X_test_scaled, y_train, y_test, labels)

    rf = RandomForestClassifier(n_estimators=200, random_state=42)
    results["random_forest"] = train_and_evaluate(rf, "Random Forest", X_train, X_test, y_train, y_test, labels)

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nSummary:")
    for name, acc in results.items():
        print(f"  {name}: {acc:.3f}")


if __name__ == "__main__":
    main()
