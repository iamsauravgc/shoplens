# ShopLens — Guide (Epic 1 + Epic 2)

This document walks through every block of code and explains the concepts behind it.
Skim the `Why` lines to defend decisions to your mentor; open the `Concept` blocks
when you want the theory behind a cell.

---

# Epic 1 — Person Detection

## What this notebook does in one line

Feed 2000 CCTV images into a pretrained model, count people per frame, compare against
ground truth, find the best confidence setting.

## Overall flow

```text
Mall Dataset
     ↓
Ground Truth
     ↓
Explore frames
     ↓
YOLOv8n
     ↓
Single-frame smoke test
     ↓
50-frame quick evaluation
     ↓
Confidence threshold tuning
     ↓
Best threshold
     ↓
YOLO on all 2000 frames
     ↓
CSV results
     ↓
Metrics + visualizations + failure analysis
     ↓
Epic 2: Person Tracking
```

---

## Cell: Install

```python
!pip install 'numpy<2.0'
!pip install ultralytics==8.3.0
!pip install scipy
```

**Why numpy<2.0?**
Colab ships numpy 2.x by default. scipy was built against numpy 1.x. When both are
loaded together, Python can't find internal numpy modules (`numpy.rec`) and crashes.
Pinning numpy below 2.0 fixes this.

**Why ultralytics?**
That's the official YOLOv8 package. One import gives you the model, inference, and
result parsing.

**Why scipy?**
The Mall Dataset ground truth is stored as a `.mat` file — MATLAB's file format.
`scipy.io.loadmat` is the standard way to read it in Python.

---

## Cell: Imports

```python
import os
import zipfile
import csv
import time
import logging
from pathlib import Path

import cv2
import numpy as np
import scipy.io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from ultralytics import YOLO
```

Standard library stuff. Two things worth noting:

```python
logging.getLogger('ultralytics').setLevel(logging.WARNING)
```
YOLOv8 prints a lot of progress output by default. This suppresses it so the notebook
output stays clean.

<details>
<summary><strong>Concept: What each library does</strong></summary>

- **OpenCV (`cv2`)** → read images and image processing
- **NumPy (`np`)** → numerical arrays and calculations
- **SciPy** → load `mall_gt.mat`
- **Matplotlib** → visualize detections, ground truth, and metrics
- **YOLO** → detect people
- **CSV** → save detection results
- **Pathlib** → manage file paths

</details>

---

## Cell: Mount Drive + Extract Dataset

```python
DRIVE_DIR = Path('/content/drive/MyDrive/shoplens')
```

Everything saved to this folder persists after the Colab session ends. Colab's local
`/content/` folder gets wiped on disconnect — Drive doesn't.

```python
if FRAMES_DIR.exists() and len(list(FRAMES_DIR.glob('*.jpg'))) == 2000:
    print('Dataset already extracted. Skipping.')
```
On repeat sessions, extracting 2000 images takes time. This check skips it if already
done. If the frames aren't there, the notebook looks for `mall_dataset.zip` in Drive,
extracts it, or asks you to upload it, then copies the ZIP into Drive for future sessions.

```python
assert frame_count == 2000
assert GT_PATH.exists()
```
Makes sure the required dataset is available before continuing.

<details>
<summary><strong>Concept: The dataset structure</strong></summary>

```text
mall_dataset/
    frames/
        seq_000001.jpg
        seq_000002.jpg
        ...
        seq_002000.jpg
    mall_gt.mat
```

`mall_gt.mat` contains the reference information:

- `count` — a `(2000,)` array with the **actual number of people in each frame**.
  Example: Frame 1 → 35 people, Frame 2 → 36 people.
- `frame` — the **head positions** `(x, y)` of the people in each frame.

The notebook uses `count` as the primary reference for detection accuracy.

</details>

---

## Cell: Load Ground Truth

```python
def load_ground_truth(mat_path):
    mat = scipy.io.loadmat(mat_path)
    gt_counts = mat['count'].flatten().astype(int)
    ...
    gt_locations[i] = entry[0][0][0]  # (N, 2) head positions
```

`mall_gt.mat` has two useful fields:
- `count` — a flat array of 2000 integers. `count[i]` = number of people in frame `i+1`.
- `frame` — a nested MATLAB struct. Each entry holds (x, y) head positions for every
  person in that frame.

The `entry[0][0][0]` navigation looks ugly because MATLAB structs nest differently
than Python dicts. This was verified by inspecting the actual file — it gives a
`(N, 2)` array where N matches the count exactly.

**Why load locations at all if we're just counting?**
Locations let us visualize where in the frame people are (the red dot overlay).
Also needed in Epic 4 for heatmap generation.

---

## Cell: Explore Dataset

```python
visualize_ground_truth([1, 250, 500, 1000, 1500, 2000], ...)
```

Before running any model, look at what the data actually looks like. The red dots are
ground truth head positions. This tells you:
- Camera is top-down (bird's eye), not eye-level
- People are small (30-50px tall)
- Frame is 320×480px

This matters because YOLOv8 was trained on COCO — mostly eye-level photos of full-body
people. Top-down CCTV is a harder problem for it. You see this coming before results
disappoint you.

The notebook also creates two plots:
- **Count distribution** — histogram of how often each person-count range occurs
- **Count over time** — line plot of how the count changes across the 2000 frames

---

## Cell: detect_persons()

```python
def detect_persons(model, img_path: Path, conf: float = 0.3):
    results = model(str(img_path), classes=[0], conf=conf, verbose=False, device='cpu')
    xyxy = boxes.xyxy.cpu().numpy()
```

- `classes=[0]` — COCO class 0 is "person". Without this, YOLOv8 would also detect
  cars, chairs, etc.
- `conf=conf` — minimum confidence to count a detection. Below this score, YOLOv8
  ignores the detection.
- `device='cpu'` — no GPU available. Forces CPU inference.
- `.xyxy` — bounding box format: (x1, y1, x2, y2) = top-left and bottom-right corners.
- `.cpu().numpy()` — PyTorch tensors live on GPU/CPU memory. `.cpu()` moves to CPU,
  `.numpy()` converts to a regular numpy array.

<details>
<summary><strong>Concept: Why <code>classes=[0]</code></strong></summary>

The YOLO model is trained on COCO classes, and COCO class ID `0 = person`. So:

```python
classes=[0]
```

means **"only detect people."** The detector does not need to return cars, bags,
chairs, etc.

</details>

<details>
<summary><strong>Concept: What <code>conf</code> (the confidence threshold) is</strong></summary>

`conf` determines how confident YOLO must be before keeping a detection.

- **Too low** → YOLO accepts weak detections (a bag, a shadow). This creates
  **false positives**.
- **Too high** → YOLO becomes stricter and discards real people whose confidence
  isn't high enough. This creates **false negatives** (missed people).

Because the threshold is a trade-off, the notebook tunes this value rather than
assuming the default is optimal.

</details>

<details>
<summary><strong>Concept: Bounding boxes as <code>[x1, y1, x2, y2]</code></strong></summary>

YOLO returns bounding boxes as:

```text
[x1, y1, x2, y2]
```

where `(x1,y1)` is the top-left corner and `(x2,y2)` the bottom-right corner:

```text
(x1,y1) ───────────────┐
   │                   │
   │      person       │
   │                   │
   └───────────────(x2,y2)
```

The function returns `count` (number of detected people) and `xyxy` (all bounding
boxes). If there are no detections: `return 0, np.empty((0, 4))`.

</details>

---

## Cell: compute_metrics()

```python
errors = np.array([r['error'] for r in results])
mae  = errors.mean()
rmse = np.sqrt((errors ** 2).mean())
```

<details>
<summary><strong>Concept: MAE vs RMSE (the two main metrics)</strong></summary>

**Error per frame** = `abs(detected - gt)`. If GT = 40 and detected = 37, error = 3.

**MAE (Mean Absolute Error):** average of `|detected - gt|` across all frames.
If MAE = 5, you're off by 5 people per frame on average. Simple and intuitive.

Example: errors of 2, 4, 0 → MAE = (2 + 4 + 0) / 3 = 2.

**RMSE (Root Mean Squared Error):** square each error, average them, take the square
root. It **penalises large errors more than small ones**:

```python
np.sqrt((errors ** 2).mean())
```

Example: errors of 1, 1, 1, 10 — the 10 has a much larger effect on RMSE than on MAE.

**Why both?** Mentor might ask. MAE tells you typical performance. RMSE tells you how
bad the worst cases are.

**Max error:** `errors.max()` — the largest counting error on any single frame.

**Exact matches:** `(errors == 0).sum()` — how many frames got the exact person count
correct.

</details>

---

## Cell: Threshold Tuning

```python
THRESHOLDS = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
```

The confidence threshold controls what counts as a valid detection:
- **Too low (0.1):** model reports detections it's not sure about. More false positives.
- **Too high (0.4):** model only reports detections it's very sure about. Misses real people.

We test 7 values on 50 frames first (fast, ~2 min) rather than all 2000 (slow, ~20 min).
Once we know the best threshold, we use it for the full run.

```python
best = min(threshold_results, key=lambda x: x['mae'])
BEST_CONF = best['conf']
```
The winning threshold is the one with the **lowest MAE** on the 50-frame sample.

Result: **0.1 won** — even at the lowest threshold, the model under-detects. Raising the
bar makes it worse, not better. This confirms the top-down angle is the real problem,
not false positives.

---

## Cell: Full Run — 2000 Frames

```python
f.flush()  # write immediately — safe against disconnects
```

The most important line in this cell. Without `flush()`, Python buffers writes in memory
and only saves to disk in chunks. If Colab disconnects mid-run, you lose everything
buffered. With `flush()`, every row is written to Drive immediately.

```python
completed = set()
if OUTPUT_CSV.exists():
    for row in reader:
        completed.add(int(row['frame_id']))
remaining = [i for i in ALL_FRAMES if i not in completed]
```
Resume logic. If you've already processed 1200 frames and the session drops, re-running
this cell picks up from frame 1201 instead of starting over.

The notebook also prints progress and an ETA every 100 frames:

```text
[ 500/2000] frame 500 | 4.2 fps | ETA: 6.0 min
```

<details>
<summary><strong>Concept: Why the CSV row-by-row safety matters</strong></summary>

Each CSV row contains:

```text
frame_id | gt_count | detected_count | error | conf
```

The combination of `f.flush()` + resume logic means:

```text
f.flush()
   +
resume logic
   ↓
Safe long-running processing
```

If Colab disconnects after frame 1000, the already-flushed results are safely stored in
Drive, and the next run continues from 1001 — no need to rerun frames already processed.

</details>

---

## Cell: Failure Analysis

```python
sorted_by_error = sorted(full_results, key=lambda x: x['error'], reverse=True)
worst_10 = sorted_by_error[:10]
```

Find the 10 frames where the model was most wrong. Visualize them. This is what your
mentor wants to see — not just "MAE = 5.71" but "here's why, here's what the hard
frames look like."

The notebook then overlays YOLO boxes (green) and ground-truth heads (red) on the three
worst frames and saves `failure_cases.png`.

<details>
<summary><strong>Concept: Why YOLO struggles on this footage</strong></summary>

Common patterns on the worst frames:

1. **Heavy occlusion** — people overlap, so YOLO misses one → under-detection.
2. **Top-down camera angle** — COCO training images mostly show people at eye level,
   so this viewpoint is less familiar → lower confidence.
3. **Distant/small people** — people near the top of the frame are small; higher
   thresholds discard these weak detections.

This also explains why the confidence threshold can't simply be set very high.

</details>

---

## Cell: Summary

Saves `epic1_summary.txt` to Drive. This is the text you paste into your technical
report. Has every metric, the best threshold, and failure cases documented.

---

# Epic 2 — Multi-Person Tracking

## What this notebook does in one line

Feed detected persons into DeepSORT which assigns a consistent ID to each person across
frames, then record their movement paths.

## Overall flow

```text
Images → YOLO detects people → DeepSORT assigns IDs → trajectories are recorded
→ parameters are tuned → final tracking data is exported → Epic 3 zone analytics
```

---

## Cell: Install + imports

```python
!pip install 'numpy<2.0'
!pip install ultralytics==8.3.0
!pip install deep_sort_realtime
!pip install scipy
```

Same story as Epic 1 plus `deep_sort_realtime` for tracking. One extra detail: the cell
ends with a Colab runtime restart, because `deep_sort_realtime` must be installed before
its import.

Main imports:

```python
from deep_sort_realtime.deepsort_tracker import DeepSort
```

<details>
<summary><strong>Concept: What DeepSORT does</strong></summary>

YOLO answers: **"There is a person here."**

DeepSORT answers: **"This person is probably the same person I saw earlier, so keep
the same ID."**

It matches detections across frames and assigns persistent identities (ID 1, ID 2, ...).

</details>

---

## Cell: pkg_resources patch

```python
_stub = types.ModuleType('pkg_resources')
def _resource_filename(package, resource):
    base = '/usr/local/lib/python3.12/dist-packages/deep_sort_realtime'
    return os.path.join(base, resource)
_stub.resource_filename = _resource_filename
sys.modules.setdefault('pkg_resources', _stub)
```

`deep_sort_realtime` internally uses `pkg_resources` (part of `setuptools`) to find its
pretrained weight files. Colab's Python 3.12 doesn't ship `pkg_resources` as a standalone
module. Rather than installing a full `setuptools`, we create a minimal fake module that
only implements the one function DeepSORT actually needs — `resource_filename` — and
points it to the correct path. This is a surgical fix that avoids changing the environment.

---

## Cell: detect_persons() — different from Epic 1

```python
detections_for_tracker.append(([float(x1), float(y1), w, h], float(c), 'person'))
```

Epic 1's `detect_persons` returned `xyxy` (x1,y1,x2,y2). DeepSORT expects a different
format: `[x1, y1, width, height]` — the top-left corner plus dimensions, not two corners.
We convert here before passing to the tracker.

```python
w = x2 - x1
h = y2 - y1
```

<details>
<summary><strong>Concept: xyxy → xywh conversion</strong></summary>

Example:

```text
[x1, y1, x2, y2]        →        [x1, y1, w, h]
[100, 50, 200, 250]     →        [100, 50, 100, 200]
```

width  = 200 - 100 = 100
height = 250 - 50  = 200

The bounding box itself hasn't changed — only its representation. **Why does DeepSORT
use a different format?** Historical convention. YOLO uses xyxy internally, most
trackers use xywh. You'll see this mismatch often in CV pipelines.

The function returns three things:
1. `detections_for_tracker` — formatted for DeepSORT
2. `xyxy` — original corner-coordinate boxes for visualization
3. `confs` — confidence values

</details>

---

## Cell: make_tracker()

```python
DeepSort(max_age=30, n_init=3, embedder_gpu=False)
```

<details>
<summary><strong>Concept: <code>max_age</code> vs <code>n_init</code> (easy memory rule)</strong></summary>

**`n_init` = "How many times should I see you before I trust you?"**

A detection must appear in 3 consecutive frames before getting a confirmed track ID.
Prevents random noise (a bag, a shadow) from being tracked as a person.

```text
Frame 1 → detection → not trusted yet
Frame 2 → detection → still not confirmed
Frame 3 → detection → confirmed track
```

**`max_age` = "How long should I wait for you when I can't see you?"**

If a person disappears from frame (behind a pillar, occluded) the tracker keeps their
ID "alive" for this many frames hoping they'll reappear. After 30 frames without a
match, the track is deleted and the person gets a new ID next time they appear.

Higher `max_age` helps maintain IDs through temporary misses but can create ghost tracks.

**`embedder_gpu=False`:** DeepSORT uses a MobileNetV2 neural network to extract
appearance features (what the person looks like) to help re-identify them. Setting this
to False runs it on CPU.

</details>

---

## Cell: run_tracking_pipeline()

```python
trajectories = defaultdict(list)   # track_id -> [(frame_idx, cx, cy), ...]
frame_data   = {}                  # frame_idx -> [(track_id, x1, y1, x2, y2), ...]
```

Two data structures built in parallel:
- `trajectories` — indexed by person ID. Lets you ask "where did person 7 go?"
- `frame_data` — indexed by frame number. Lets you ask "who was in frame 150?"

Both are needed. Zone analytics (Epic 3) needs `trajectories`. Video annotation needs
`frame_data`.

```python
if not t.is_confirmed():
    continue
```
Only process confirmed tracks — those that have appeared in at least `n_init`
consecutive frames. Unconfirmed tracks are tentative detections that might be noise.

```python
cx = (x1 + x2) / 2
cy = (y1 + y2) / 2
```
Centroid of the bounding box. We track the centre point, not the full box, because it's
more stable and sufficient for zone intersection later.

<details>
<summary><strong>Concept: trajectories vs frame_data</strong></summary>

**`trajectories`** is **person-centric** — the movement history of each person:

```text
ID 5 →
    frame 1: (320, 150)
    frame 2: (322, 153)
    frame 3: (325, 157)
```

It answers **"where has this particular person been over time?"** and is the structure
that moves into **Epic 3**, saved as `trajectories.json`.

**`frame_data`** is **frame-centric** — who is visible in each frame:

```text
Frame 50 →
    ID 7  → bounding box
    ID 12 → bounding box
    ID 15 → bounding box
```

It answers **"who is visible in this frame, and where are they?"** and is used to
reconstruct the annotated frames and the tracking video.

**Memory rule:** `trajectories` = person history → goes to Epic 3; `frame_data` =
per-frame snapshot → used for Epic 2 visualization/video.

</details>

<details>
<summary><strong>Concept: Why we track the center point <code>(cx, cy)</code></strong></summary>

DeepSORT returns the box as `x1, y1, x2, y2`. The center is:

```python
cx = (x1 + x2) / 2
cy = (y1 + y2) / 2
```

```text
(x1,y1) ─────────────
   │       ●         │
   │     center      │
   │                 │
   ─────────────(x2,y2)
```

The center point represents the person's position and is stored per track as
`(frame, center_x, center_y)` — the input for trajectory drawing and zone analytics.

</details>

---

## Cell: Parameter Tuning

```python
CONFIGS = [
    {'max_age': 20, 'n_init': 2},
    {'max_age': 30, 'n_init': 3},
    {'max_age': 40, 'n_init': 3},
    {'max_age': 50, 'n_init': 5},
]
```

We measure "unique IDs assigned" — not accuracy against ground truth, because tracking
ground truth matching is complex. The proxy metric is: **fewer unique IDs on the same
footage = better**, because it means fewer ID switches (one physical person counted as
multiple IDs).

```python
best_cfg = min(tuning_results, key=lambda x: x['unique_ids'])
```

The best configuration produces the **fewest unique IDs**. Run on 100 frames (not 200)
for speed — enough to compare configs.

---

## Cell: draw_tracked_frame()

```python
rgba = plt.cm.tab20(int(tid) % 20)
colour = (int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))
```

`tab20` is a matplotlib colormap with 20 distinct colours. `tid % 20` maps any track ID
to one of those 20 colours — same ID always gets the same colour. `int(tid)` needed
because DeepSORT returns string IDs and `%` on a string is string formatting, not modulo.

For each confirmed track the cell draws the bounding box and writes the ID label, then
displays selected frames so you can visually check the tracking behaves.

---

## Cell: Export Video

```python
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(str(VIDEO_OUT), fourcc, 10.0, (w, h))
```

`fourcc` is a 4-character code that tells OpenCV which video codec to use. `mp4v` =
MPEG-4 Part 2 — widely supported, plays in browsers and VLC. `10.0` = 10 frames per
second playback speed, so 200 frames ≈ 20 seconds of video.

Each annotated frame is written with `writer.write(ann)` and the video is finalized
with `writer.release()`.

---

## Cell: Trajectory Visualisation

```python
combined = cv2.addWeighted(base_img, 0.4, overlay, 0.6, 0)
```

<details>
<summary><strong>Concept: <code>cv2.addWeighted()</code> overlay blending</strong></summary>

Blend two images: the original frame at 40% opacity, and the trajectory overlay at 60%
opacity:

```text
Original image
      +
Trajectory overlay
      ↓
Blended image
```

Result: you can see both the store background and the movement paths simultaneously.
The trajectories are drawn on a separate overlay layer — line by line, connecting each
person's consecutive center points — then blended, so the original frame stays visible.

The final image is saved as `trajectories.png`.

</details>

---

## Cell: Save JSON

```python
trajectories_serialisable = {
    str(tid): [
        {'frame': int(f), 'cx': round(cx, 2), 'cy': round(cy, 2)}
        for f, cx, cy in points
    ]
    for tid, points in trajectories_final.items()
}
```

<details>
<summary><strong>Concept: Why keys are converted to strings</strong></summary>

Python dicts with integer keys can't be serialised to JSON directly — JSON only allows
string keys. `str(tid)` handles that. `round(cx, 2)` keeps file size small — 2 decimal
places is more than precise enough for zone intersection.

```json
{
  "trajectories": {
    "1": [
      {"frame": 1, "cx": 320.5, "cy": 150.2},
      {"frame": 2, "cx": 323.0, "cy": 153.0}
    ]
  }
}
```

This JSON is the handoff from Epic 2 to Epic 3. Zone analytics reads centroid positions
from here, without rerunning YOLO and DeepSORT.

</details>

---

## What carries forward

| Output | Used in |
|---|---|
| `detection_results.csv` | Epic 9 evaluation |
| `trajectories.json` | Epic 3 zone analytics |
| `trajectories.png` | README / mentor presentation |
| `tracking_annotated.mp4` | Demo video (Epic 9) |
| `BEST_CONF = 0.1` | All future notebooks |
| `BEST_MAX_AGE`, `BEST_N_INIT` | Epic 3 pipeline |