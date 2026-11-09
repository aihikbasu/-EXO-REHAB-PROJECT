"""
Novelty: confidence-weighted proportional EMG control.

A hard classifier (predict one label) would make the assistance strategy
switch abruptly whenever the predicted gesture changes. This module instead
exposes the classifier's full probability distribution over gestures, so
the GUI can blend between assistance strategies proportionally to how
confident the classifier is in each one -- closer to real proportional
myoelectric control than a simple switch.

In the absence of a live EMG stream, this module samples feature rows from
a small held-out demo set (model/demo_feature_samples.csv) captured from
the real trained classifier's test split, so the probabilities shown are
genuine model outputs, not fabricated numbers.
"""

import os
import warnings

import joblib
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "emg_model.joblib")
SAMPLES_PATH = os.path.join(MODEL_DIR, "demo_feature_samples.csv")

# How each gesture's classifier confidence maps onto the Run Trial
# controller's stance/swing setpoints -- used to blend a proportional
# setpoint instead of jumping discretely between presets.
GESTURE_SETPOINTS = {
    "rest": {"stance": 0, "swing": 0},
    "flexion": {"stance": 15, "swing": 45},
    "extension": {"stance": 30, "swing": 20},
    "grasp": {"stance": 25, "swing": 35},
}


class EMGProportionalController:
    def __init__(self, ema_alpha=0.35, confidence_threshold=0.30):
        self._bundle = None
        self._samples = None
        self._load_error = None
        self.ema_alpha = ema_alpha  # smoothing factor (0 < alpha <= 1)
        self.confidence_threshold = confidence_threshold
        self.filtered_stance = 0.0
        self.filtered_swing = 0.0
        self.history = []
        
        try:
            self._bundle = joblib.load(MODEL_PATH)
            self._samples = pd.read_csv(SAMPLES_PATH)
        except Exception as exc:
            self._load_error = str(exc)

    @property
    def available(self):
        return self._bundle is not None

    @property
    def load_error(self):
        return self._load_error

    def reset_filter(self):
        """Reset EMA filter to baseline rest positions."""
        self.filtered_stance = 0.0
        self.filtered_swing = 0.0
        self.history.clear()

    def sample_window(self):
        """Pull one real feature row from the demo set, as a stand-in for
        a live EMG window. Returns (features_row, true_label)."""
        row = self._samples.sample(1).iloc[0]
        true_label = row["label"]
        features = row[self._bundle["feature_cols"]].values.reshape(1, -1)
        return features, true_label

    def predict_proportional(self, features, apply_smoothing=True):
        """Returns {gesture: probability} from the real trained classifier,
        plus raw and EMA-smoothed stance/swing setpoints weighted by probabilities.
        
        Includes confidence thresholding: if peak probability is ambiguous,
        target gracefully biases toward resting equilibrium to prevent actuator shudder.
        """
        scaler = self._bundle["scaler"]
        model = self._bundle["model"]

        features_scaled = scaler.transform(features)
        probs = model.predict_proba(features_scaled)[0]
        classes = model.classes_

        prob_dict = {cls: float(p) for cls, p in zip(classes, probs)}
        max_prob = max(prob_dict.values())
        dominant_gesture = max(prob_dict, key=prob_dict.get)

        # Raw probability-weighted target setpoints
        raw_stance = sum(
            prob_dict[g] * GESTURE_SETPOINTS[g]["stance"] for g in prob_dict
        )
        raw_swing = sum(
            prob_dict[g] * GESTURE_SETPOINTS[g]["swing"] for g in prob_dict
        )

        # If confidence is below deadband threshold, decay gently toward rest (0)
        if max_prob < self.confidence_threshold:
            target_stance = raw_stance * 0.5
            target_swing = raw_swing * 0.5
            confident = False
        else:
            target_stance = raw_stance
            target_swing = raw_swing
            confident = True

        # Exponential Moving Average (EMA) smoothing to eliminate motor jerk
        if apply_smoothing:
            self.filtered_stance = (
                self.ema_alpha * target_stance + (1.0 - self.ema_alpha) * self.filtered_stance
            )
            self.filtered_swing = (
                self.ema_alpha * target_swing + (1.0 - self.ema_alpha) * self.filtered_swing
            )
        else:
            self.filtered_stance = target_stance
            self.filtered_swing = target_swing

        result = {
            "probabilities": prob_dict,
            "dominant_gesture": dominant_gesture,
            "max_confidence": round(max_prob, 3),
            "is_confident": confident,
            "raw_stance": round(raw_stance, 1),
            "raw_swing": round(raw_swing, 1),
            "blended_stance": round(self.filtered_stance, 1),
            "blended_swing": round(self.filtered_swing, 1),
        }
        self.history.append(result)
        return result

