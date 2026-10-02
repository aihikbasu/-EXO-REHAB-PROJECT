# EMG Gesture Classification

Classifiers for surface EMG gesture recognition (rest, flexion, extension,
grasp), built for the wearable rehabilitation exoskeleton project.

## Data

Raw, labeled EMG recordings from 10 real subjects (20 sessions), sourced
from the public UCI "EMG Data for Gestures" dataset (Myo armband, 8
channels, millisecond-resolution timestamps, per-sample gesture labels).
Source: https://archive.ics.uci.edu/dataset/481/emg+data+for+gestures

Each file is a continuous recording where the subject performs a sequence
of gestures. `build_dataset.py` slices contiguous same-label segments into
overlapping windows and extracts features per window.

Label mapping used (4 of the dataset's 7 original classes, matching the
project's target gestures):
| Raw label | Gesture |
|---|---|
| 1 | rest |
| 2 | grasp (hand clenched in a fist) |
| 3 | flexion (wrist flexion) |
| 4 | extension (wrist extension) |

Radial/ulnar deviation and unmarked samples are excluded.

## Files

- `features.py` -- feature extraction from raw EMG windows (zero crossings,
  slope sign changes, mean absolute value, waveform length, RMS, variance)
- `build_dataset.py` -- segments raw labeled recordings into windows and
  builds the feature dataset (`data/emg_gesture_dataset.csv`)
- `train.py` -- trains and evaluates SVM and Random Forest classifiers

## Methodology note: avoiding data leakage

Windows are extracted with 50% overlap, so windows from the same gesture
repetition are highly similar to each other. An initial version of this
pipeline split windows into train/test independently, which let near-
identical overlapping windows leak across the split and produced an
inflated, meaningless 100% accuracy. This was caught and fixed: the final
version splits by gesture repetition (`GroupShuffleSplit`), so all windows
from a given repetition stay entirely in either train or test. The results
below reflect genuine performance on unseen repetitions.

## Results

2,470 windows across 4 balanced classes, from 10 subjects, split by gesture
repetition (not by individual window).

| Model | Accuracy |
|---|---|
| SVM (RBF kernel) | 96.0% |
| Random Forest | 96.2% |

Rest and flexion are classified almost perfectly. The main confusion is
grasp vs. flexion (both involve finger-flexor activation), consistent with
the underlying muscle physiology. Confusion matrices are in this repo
(`confusion_matrix_svm.png`, `confusion_matrix_random_forest.png`).

## Next steps

- Replace this public dataset with live data from the lab's own EMG sensors
  once an activity-timing protocol is available for it
- Build a loader matching the lab sensors' actual file format once known
- Feed classifier output into the exoskeleton GUI's Run Trial page to
  directly drive the assistance strategy / actuator control
