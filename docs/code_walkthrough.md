# ShopLens — Code Walkthrough
## Epic 1: Person Detection + Epic 2: Tracking

This document explains what each block of code does and why it exists.
Not a tutorial — just enough context to defend every decision to your mentor.

---

## Epic 1 — Person Detection

### What this notebook does in one line
Feed 2000 CCTV images into a pretrained model, count people per frame, compare against ground truth, find the best confidence setting.

---

### Cell: Install

```python
!pip install 'numpy<2.0'
!pip install ultralytics==8.3.0
!pip install scipy
```

**Why numpy<2.0?**
Colab ships numpy 2.x by default. scipy was built against numpy 1.x. When both are loaded together, Python can't find internal numpy modules (`numpy.rec`) and crashes. Pinning numpy below 2.0 fixes this.

**Why ultralytics?**
That's the official YOLOv8 package. One import gives you the model, inference, and result parsing.

**Why scipy?**
The Mall Dataset ground truth is stored as a `.mat` file — MATLAB's file format. `scipy.io.loadmat` is the standard way to read it in Python.

---

### Cell: Imports

Standard library stuff. Two things worth noting:

```python
logging.getLogger('ultralytics').setLevel(logging.WARNING)
```
YOLOv8 prints a lot of progress output by default. This suppresses it so the notebook output stays clean.

---

### Cell: Mount Drive + Extract Dataset

```python
DRIVE_DIR = Path('/content/drive/MyDrive/shoplens')
```
Everything saved to this folder persists after the Colab session ends. Colab's local `/content/` folder gets wiped on disconnect — Drive doesn't.

```python
if FRAMES_DIR.exists() and len(list(FRAMES_DIR.glob('*.jpg'))) == 2000:
    print('Dataset already extracted. Skipping.')
```
On repeat sessions, extracting 2000 images takes time. This check skips it if already done.

---

### Cell: Load Ground Truth

```python
def load_ground_truth(mat_path):
    mat = scipy.io.loadmat(mat_path)
    gt_counts = mat['count'].flatten().astype(int)
    ...
    gt_locations[i] = entry[0][0][0]  # (N, 2) head positions
```

`mall_gt.mat` has two useful fields:
- `count` — a flat array of 2000 integers. `count[i]` = number of people in frame `i+1`.
- `frame` — a nested MATLAB struct. Each entry holds (x, y) head positions for every person in that frame.

The `entry[0][0][0]` navigation looks ugly because MATLAB structs nest differently than Python dicts. This was verified by inspecting the actual file — it gives a `(N, 2)` array where N matches the count exactly.

**Why load locations at all if we're just counting?**
Locations let us visualize where in the frame people are (the red dot overlay). Also needed in Epic 4 for heatmap generation.

---

### Cell: Explore Dataset

```python
visualize_ground_truth([1, 250, 500, 1000, 1500, 2000], ...)
```

Before running any model, look at what the data actually looks like. The red dots are ground truth head positions. This tells you:
- Camera is top-down (bird's eye), not eye-level
- People are small (30-50px tall)
- Frame is 320×480px

This matters because YOLOv8 was trained on COCO — mostly eye-level photos of full-body people. Top-down CCTV is a harder problem for it. You see this coming before results disappoint you.

---

### Cell: detect_persons()

```python
results = model(str(img_path), classes=[0], conf=conf, verbose=False, device='cpu')
xyxy = boxes.xyxy.cpu().numpy()
```

- `classes=[0]` — COCO class 0 is "person". Without this, YOLOv8 would also detect cars, chairs, etc.
- `conf=conf` — minimum confidence to count a detection. Below this score, YOLOv8 ignores the detection.
- `device='cpu'` — no GPU available. Forces CPU inference.
- `.xyxy` — bounding box format: (x1, y1, x2, y2) = top-left and bottom-right corners.
- `.cpu().numpy()` — PyTorch tensors live on GPU/CPU memory. `.cpu()` moves to CPU, `.numpy()` converts to a regular numpy array.

---

### Cell: compute_metrics()

```python
errors = np.array([r['error'] for r in results])
mae  = errors.mean()
rmse = np.sqrt((errors ** 2).mean())
```

**MAE (Mean Absolute Error):** average of `|detected - gt|` across all frames. If MAE = 5, you're off by 5 people per frame on average. Simple and intuitive.

**RMSE (Root Mean Squared Error):** penalises large errors more than small ones. If you're off by 1 person on most frames but 20 on a few, RMSE catches that where MAE might not.

**Why both?** Mentor might ask. MAE tells you typical performance. RMSE tells you how bad the worst cases are.

---

### Cell: Threshold Tuning

```python
THRESHOLDS = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
```

The confidence threshold controls what counts as a valid detection:
- **Too low (0.1):** model reports detections it's not sure about. More false positives.
- **Too high (0.4):** model only reports detections it's very sure about. Misses real people.

We test 7 values on 50 frames first (fast, ~2 min) rather than all 2000 (slow, ~20 min). Once we know the best threshold, we use it for the full run.

Result: **0.1 won** — even at the lowest threshold, the model under-detects. Raising the bar makes it worse, not better. This confirms the top-down angle is the real problem, not false positives.

---

### Cell: Full Run — 2000 Frames

```python
f.flush()  # write immediately — safe against disconnects
```

The most important line in this cell. Without `flush()`, Python buffers writes in memory and only saves to disk in chunks. If Colab disconnects mid-run, you lose everything buffered. With `flush()`, every row is written to Drive immediately.

```python
completed = set()
if OUTPUT_CSV.exists():
    for row in reader:
        completed.add(int(row['frame_id']))
remaining = [i for i in ALL_FRAMES if i not in completed]
```
Resume logic. If you've already processed 1200 frames and the session drops, re-running this cell picks up from frame 1201 instead of starting over.

---

### Cell: Failure Analysis

```python
sorted_by_error = sorted(full_results, key=lambda x: x['error'], reverse=True)
worst_10 = sorted_by_error[:10]
```

Find the 10 frames where the model was most wrong. Visualize them. This is what your mentor wants to see — not just "MAE = 5.71" but "here's why, here's what the hard frames look like."

Common patterns:
- Heavy occlusion (people overlapping)
- Crowd near top of frame (small, far away)
- People partially cut off at frame edges

---

### Cell: Summary

Saves `epic1_summary.txt` to Drive. This is the text you paste into your technical report. Has every metric, the best threshold, and failure cases documented.

---
---

## Epic 2 — Multi-Person Tracking

### What this notebook does in one line
Feed detected persons into DeepSORT which assigns a consistent ID to each person across frames, then record their movement paths.

---

### Cell: pkg_resources patch

```python
_stub = types.ModuleType('pkg_resources')
def _resource_filename(package, resource):
    base = '/usr/local/lib/python3.12/dist-packages/deep_sort_realtime'
    return os.path.join(base, resource)
_stub.resource_filename = _resource_filename
sys.modules.setdefault('pkg_resources', _stub)
```

`deep_sort_realtime` internally uses `pkg_resources` (part of `setuptools`) to find its pretrained weight files. Colab's Python 3.12 doesn't ship `pkg_resources` as a standalone module. Rather than installing a full `setuptools`, we create a minimal fake module that only implements the one function DeepSORT actually needs — `resource_filename` — and points it to the correct path. This is a surgical fix that avoids changing the environment.

---

### Cell: detect_persons() — different from Epic 1

```python
detections_for_tracker.append(([float(x1), float(y1), w, h], float(c), 'person'))
```

Epic 1's `detect_persons` returned `xyxy` (x1,y1,x2,y2). DeepSORT expects a different format: `[x1, y1, width, height]` — the top-left corner plus dimensions, not two corners. We convert here before passing to the tracker.

**Why does DeepSORT use a different format?**
Historical convention. YOLO uses xyxy internally, most trackers use xywh. You'll see this mismatch often in CV pipelines.

---

### Cell: make_tracker()

```python
DeepSort(max_age=30, n_init=3, embedder_gpu=False)
```

**max_age:** If a person disappears from frame (behind a pillar, occluded) the tracker keeps their ID "alive" for this many frames hoping they'll reappear. After 30 frames without a match, the track is deleted and the person gets a new ID next time they appear.

**n_init:** A detection must appear in 3 consecutive frames before getting a confirmed track ID. Prevents random noise (a bag, a shadow) from being tracked as a person.

**embedder_gpu=False:** DeepSORT uses a MobileNetV2 neural network to extract appearance features (what the person looks like) to help re-identify them. `embedder_gpu=False` runs this on CPU.

---

### Cell: run_tracking_pipeline()

```python
trajectories = defaultdict(list)   # track_id -> [(frame_idx, cx, cy), ...]
frame_data   = {}                  # frame_idx -> [(track_id, x1, y1, x2, y2), ...]
```

Two data structures built in parallel:
- `trajectories` — indexed by person ID. Lets you ask "where did person 7 go?"
- `frame_data` — indexed by frame number. Lets you ask "who was in frame 150?"

Both are needed. Zone analytics (Epic 3) needs `trajectories`. Video annotation needs `frame_data`.

```python
if not t.is_confirmed():
    continue
```
Only process confirmed tracks — those that have appeared in at least `n_init` consecutive frames. Unconfirmed tracks are tentative detections that might be noise.

```python
cx = (x1 + x2) / 2
cy = (y1 + y2) / 2
```
Centroid of the bounding box. We track the centre point, not the full box, because it's more stable and sufficient for zone intersection later.

---

### Cell: Parameter Tuning

```python
CONFIGS = [
    {'max_age': 20, 'n_init': 2},
    {'max_age': 30, 'n_init': 3},
    {'max_age': 40, 'n_init': 3},
    {'max_age': 50, 'n_init': 5},
]
```

We measure "unique IDs assigned" — not accuracy against ground truth, because tracking ground truth matching is complex. The proxy metric is: **fewer unique IDs on the same footage = better**, because it means fewer ID switches (one physical person counted as multiple IDs).

Run on 100 frames (not 200) for speed — enough to compare configs.

---

### Cell: draw_tracked_frame()

```python
rgba = plt.cm.tab20(int(tid) % 20)
colour = (int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))
```

`tab20` is a matplotlib colormap with 20 distinct colours. `tid % 20` maps any track ID to one of those 20 colours — same ID always gets the same colour. `int(tid)` needed because DeepSORT returns string IDs and `%` on a string is string formatting, not modulo.

---

### Cell: Export Video

```python
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(str(VIDEO_OUT), fourcc, 10.0, (w, h))
```

`fourcc` is a 4-character code that tells OpenCV which video codec to use. `mp4v` = MPEG-4 Part 2 — widely supported, plays in browsers and VLC. `10.0` = 10 frames per second playback speed.

---

### Cell: Trajectory Visualisation

```python
combined = cv2.addWeighted(base_img, 0.4, overlay, 0.6, 0)
```

Blend two images: the original frame at 40% opacity, and the trajectory overlay at 60% opacity. Result: you can see both the store background and the movement paths simultaneously.

---

### Cell: Save JSON

```python
trajectories_serialisable = {
    str(tid): [
        {'frame': int(f), 'cx': round(cx, 2), 'cy': round(cy, 2)}
        for f, cx, cy in points
    ]
    for tid, points in trajectories_final.items()
}
```

Convert to JSON-serialisable format. Python dicts with integer keys can't be serialised to JSON directly — JSON only allows string keys. `str(tid)` handles that. `round(cx, 2)` keeps file size small — 2 decimal places is more than precise enough for zone intersection.

This JSON is the handoff from Epic 2 to Epic 3. Zone analytics reads centroid positions from here.

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