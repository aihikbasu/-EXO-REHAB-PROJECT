# EMG Gesture Classification for Exoskeleton Control

Classifiers for surface EMG gesture recognition (rest, flexion, extension,
grasp), built for the wearable rehabilitation exoskeleton project, with
three methodological contributions beyond standard classification.

## Data

Raw, labeled EMG recordings from 10 real subjects (20 sessions), from the
public UCI "EMG Data for Gestures" dataset (Myo armband, 8 channels,
per-sample gesture labels).
Source: https://archive.ics.uci.edu/dataset/481/emg+data+for+gestures

## Base Pipeline

- `features.py` -- feature extraction from raw EMG windows (zero crossings,
  slope sign changes, mean absolute value, waveform length, RMS, variance)
- `build_dataset.py` -- segments raw labeled recordings into overlapping
  windows (grouped by gesture repetition and subject), extracts features
- `train.py` -- trains/evaluates SVM and Random Forest with a leakage-free,
  grouped train/test split

**Base results**: 2,470 windows, 4 balanced classes, 10 subjects.
SVM 96.0% / Random Forest 96.2% accuracy (within-subject-pool split).

## Novelty 1: Cross-Subject Generalization + Calibration

`loso_calibration.py` -- EMG signal characteristics vary between people, so
a classifier trained on some subjects often performs worse on a new,
unseen one. This measures that gap with leave-one-subject-out (LOSO)
cross-validation, then tests whether a lightweight per-subject calibration
step (normalizing a new subject's features using a small calibration slice
of their own data, rather than the training subjects' statistics) closes it.

**Results**: Mean LOSO accuracy 86.5% without calibration -> 88.2% with
calibration. The effect is not uniform -- some subjects improve
substantially (subject 8: 83.8% -> 96.6%), a few see a small decrease. See
`loso_chart.png`.

## Novelty 2: Real-Time Feasibility Analysis

`latency_analysis.py` -- accuracy alone doesn't establish that a classifier
can run inside a live control loop. This measures actual feature
extraction + inference latency per signal window and checks it against the
window step time, for both models.

**Results**: Feature extraction ~1.2ms, SVM inference ~0.1ms, Random Forest
inference ~9.4ms -- both comfortably within the 500ms-per-step budget at
the dataset's ~200Hz sampling rate. Measured on a development machine, not
yet the target Raspberry Pi; worth re-measuring once hardware is available.

## Novelty 3: Confidence-Weighted Proportional Control

`rehab_gui/core/emg_control.py` -- rather than a hard classification
switching the assistance strategy abruptly, this exposes the classifier's
full probability distribution over gestures and blends the GUI's
stance/swing setpoints proportionally to that confidence -- closer to
proportional myoelectric control than a discrete switch. Wired directly
into the Run Trial page of the exoskeleton GUI, using the actual trained
model (not a mock), sampling real held-out feature rows as a stand-in for
a live EMG stream.

## Next Steps

- Replace the public dataset with live data from the lab's own EMG
  sensors, once an activity-timing protocol is available
- Re-measure latency on the actual Raspberry Pi
- Extend calibration to require even less labeled data per new subject
