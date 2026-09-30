# ShopLens — Technical Report

Final report for the mentor review (Week 10). Companion documents: [`README.md`](../README.md)
(setup + screenshots), [`docs/code_walkthrough.md`](code_walkthrough.md) (code-level tour),
[`docs/epics.md`](epics.md) (10-week task log with evidence links).

---

## 1. Problem statement

Small retail shops already have CCTV cameras but no way to answer basic questions: which
zones customers ignore, when the rush hour actually is, whether a layout change helped.
Professional retail-analytics systems are expensive; small shops have nothing.

ShopLens turns an ordinary CCTV clip (max 2 minutes) into per-zone visitor counts and
dwell times, a floor heatmap, flagged unusual behaviour, and a plain-English report with
concrete suggestions — running entirely on a laptop CPU, with no GPU and no extra
hardware.

Constraints from `docs/prd.md` that shaped every technical decision:

- **CPU only.** No GPU was available at any point (Colab / free-tier hosting), so every
  model had to be chosen for CPU speed first, accuracy second.
- **Upload-based, not real-time.** MVP processes a clip after upload; no live streaming.
- **Max 2 minutes, sample every 5th frame.** Full-frame CPU processing was estimated at
  3–5 hours per clip; sampling bounds the workload (documented design decision).
- **Privacy is non-negotiable.** Faces are blurred right after detection; the pipeline
  never writes an unblurred frame to disk.
- **Non-technical user.** Output must be plain English, not charts-only.

---

## 2. System overview

One upload = one background job running the full pipeline in order (see
`backend/workers/pipeline.py`; each step logs its own duration):

```
read frames (every 5th) → YOLOv8n detect + blur faces → DeepSORT track
→ zone analytics → floor heatmap → autoencoder anomaly scoring → Groq LLM report
```

The React dashboard polls job status every 3 seconds and shows the current step. Zones
are drawn once in the canvas UI and reused for every future video. State lives in SQLite
(`data/shoplens.db`) and artifacts on local disk (`storage/`); jobs run on an in-process
`threading.Thread` queue. The Redis/RQ + Supabase + Cloudflare R2 stack in `tech.md`
remains the deployment target (Epic 8, deferred by decision — nothing in the code
requires it).

---

## 3. Datasets

| dataset | role |
|---|---|
| Mall Dataset — 2,000 frames + MATLAB `.mat` head annotations | development + evaluation: detection MAE/RMSE, tracking, trajectories, heatmaps |
| 86 hand-labeled zone visits (`data/labels/samples.csv`) | anomaly precision / recall ground truth |
| Retail footage from YouTube (demo clips) | realistic end-to-end demo |
| `data/test_mall.mp4` — 66 s clip, 1,980 frames | end-to-end performance measurement |

**Dual-dataset approach** (same pattern researchers use): numbers come from the
benchmark dataset because it has labels; the demo uses real footage because it looks
real. Every headline number below can be reproduced from the benchmark side.

---

## 4. Models chosen and why

| component | choice | why (the one-liner for the mentor) |
|---|---|---|
| Person detection | **YOLOv8n** (`ultralytics`) | fastest CPU-friendly variant of a well-benchmarked family; larger variants buy accuracy we can't afford without a GPU |
| Tracking | **DeepSORT** (`deep_sort_realtime`) + **OSNet** re-ID, `embedder_gpu=False` | appearance re-ID is what keeps IDs stable when people cross paths; runs on CPU |
| Tracker tuning | `max_age=30`, `n_init=3` | tuned in `notebooks/02_tracking.ipynb`: unique IDs on the same 200-frame clip dropped **208 → 103** — fewer fragments means fewer ID switches |
| Anomaly detection | **PyTorch autoencoder** `4→8→4→2→4→8→4` (MLP) | unsupervised: no labelled anomaly data needed; trained on *normal* visits only, so anything it reconstructs badly is unusual |
| Autoencoder input | 4 features per zone visit: zone index, dwell seconds, mean velocity, direction-change rate | captures "who stayed, where, moving how" without storing any identity |
| Anomaly threshold | **95th percentile of training-set reconstruction error** = 1.120 (test p95 = 1.165) | fixed rule from the start; prevents per-video threshold shopping. Training: 400 epochs, Adam 1e-3, MSE, seed 42, 80/20 split, 341 train rows — tracked in **MLflow** (`mlflow ui`) |
| Behaviour rules | loitering: dwell ≥ 30 s **and** standstill speed < 1.5 px/s · crowd spike: count > 2× the rolling 50-frame baseline · zone avoidance: zone gets < 25% of typical traffic and < 5 visitors (only judged when median traffic ≥ 10) | autoencoder answers "*is this visit odd?*"; the rules give it a human-readable type for the report |
| Insight report | **Groq API**, `openai/gpt-oss-120b` (configurable via `LLM_MODEL`) | free tier, fast, no GPU — Ollama was rejected because it cannot run on the deployment target |
| Frontend | React + Fabric.js + Recharts | zone drawing needs a real canvas (Streamlit can't do it) |

---

## 5. Evaluation — metrics and results

### 5.1 Person detection (Mall Dataset, 2,000 frames vs ground truth)

| metric | value |
|---|---|
| MAE | **5.71** people/frame |
| RMSE | **6.82** |
| best confidence threshold | **0.10** (full threshold-vs-MAE table in `docs/shoplens_guide.md`) |

Evidence: `docs/evidence/detection_results.csv`, `threshold_vs_error.png`,
`detection_final_results.png`, `failure_cases.png`.
Reproduce: `cd backend && python -m evaluation.metrics ../docs/evidence/detection_results.csv`

*Honest note:* the PRD target was MAE < 3 — **not met** (5.71). The failures cluster in
crowd-dense frames with heavy occlusion; the fact that the best threshold is 0.10 (not
the default 0.25) shows low-confidence detections matter here. See Limitations.

### 5.2 Multi-person tracking (tuned DeepSORT)

| metric | before tuning | after tuning |
|---|---|---|
| unique IDs on the same 200-frame clip | 208 | **103** |
| short-lived tracks (< 5 points), full 2,000-frame run | — | **2 of 182 (1.1 %)** |

Fewer IDs on identical footage = fewer ID switches (a switch splits one person into two
IDs). The second row counts fragments directly from the recorded trajectories
(`data/trajectories.json`: frames 10–1995, 20,892 centroid points).

Evidence: `docs/evidence/tracking_annotated.mp4`, `trajectories.png`,
`tracking_sample_frames.png`, `trajectories.json`. Reproduce: `notebooks/02_tracking.ipynb`.

*Caveat:* this is a proxy metric, not the MOT-standard IDSW count — see Limitations.

### 5.3 Anomaly detection (86 hand-labeled visits)

| precision | recall | F1 |
|---|---|---|
| **0.419** | **0.520** | **0.464** |

The PRD target was < 20 % false positives — **not met**: precision 0.419 means ~58 % of
flags on this small labelled set were false alarms. The label set is only 86 visits and
the threshold was set by the fixed p95 rule rather than tuned on labels. Evidence:
`docs/evidence/anomaly_trajectories.png` (24 anomalous / 40 normal / 118 context tracks;
regenerate with `python backend/scripts/plot_anomaly_trajectories.py`). Reproduce:
`cd backend && python scripts/score_labels.py`.

### 5.4 LLM insight report

- **Prompt-template sweep: 10 / 10 test cases pass live**
  (`python backend/scripts/report_prompt_sweep.py --live`): zone names come only from the
  user's own drawings (no hallucinated zones), anomaly counts in the text match the
  actual rows sent to the model, and the internal `notes` field is never surfaced.
- A report failure **never fails the job**: step 7 is guarded, the UI shows the error
  with a Regenerate button (`docs/evidence/corrupt_video_ui.png` shows the same error
  path for a bad upload).
- Qualitative quality is the mentor's call — see `docs/screenshots/07-report.png`.

### 5.5 End-to-end performance (laptop CPU: AMD Ryzen 7 8845HS, no GPU)

`data/test_mall.mp4`: 66 s → 1,980 frames → **396 sampled** (every 5th):

| pipeline step | time |
|---|---|
| read frames | 1.1 s |
| YOLOv8n detection + face blur | 113.9 s |
| DeepSORT tracking | 337.8 s |
| zone analytics | 0.3 s |
| heatmap | 13.4 s |
| anomaly scoring | 4.9 s |
| LLM report (Groq) | 3.5 s |
| **total** | **475 s (~8 min)** |

**~7.2 minutes of processing per minute of video** → a full 2-minute upload ≈ 15 minutes.
Tracking alone is 71 % of the runtime; frame sampling (÷5) is what keeps this usable.
Every run logs `pipeline finished for <job> in <seconds> (<min> min processing per min of
video, …)`, so the number is continuously reproducible.

---

## 6. Privacy

Faces are blurred (Gaussian, 99×99) immediately after detection, **before any processed
frame is written to storage** — see `backend/cv/blur.py` and the "detect + blur" step
above. The only unblurred data on disk is the source clip the owner uploaded themselves;
every artifact the pipeline derives (trajectories, heatmaps, analytics, report) comes
from blurred data or pure numbers. No facial recognition or identity tracking is
performed — DeepSORT IDs exist only inside a single clip to make counting possible and
are not linked to any person.

---

## 7. Limitations and future work

1. **Detection MAE 5.71 vs target < 3.** Crowd-dense, occluded frames dominate the
   error; confidence threshold had to drop to 0.10. Future: threshold/anchor tuning per
   camera height, or a dedicated crowd-counting head alongside YOLO boxes.
2. **Anomaly precision 0.419.** 86 labelled visits is a small calibration set, the p95
   threshold is deliberately untuned (no label leakage), and the loitering/spike rule
   constants are reasoned defaults. Future: calibrate on labelled examples (calibration
   note in `backend/cv/anomaly.py`) and collect more labels.
3. **ID-switch rate is a proxy** (unique-ID count + short-track fragments), not
   MOT-standard IDSW. The direct helper already exists
   (`cv/tracker.count_id_switches`); wiring it into `evaluation/metrics.py` is a
   half-day job.
4. **Zone visit threshold untuned** (`min_frames=3` in `cv/zones.py`): someone brushing
   past a zone edge may count as a visit.
5. **Anomaly *types* are rules, not learned** — the autoencoder only says "odd"; the
   three labels (loitering, crowd spike, zone avoidance) come from thresholded rules.
   A supervised classifier over the latent space is the natural next step.
6. **LLM dependency:** report quality and availability depend on the Groq free tier;
   the model is configurable (`LLM_MODEL` / `LLM_API_URL`) and the job survives a
   report failure regardless.
7. **Deployment deferred (Epic 8):** runs locally on `threading.Thread` + SQLite + local
   disk; Supabase/R2/Railway wiring is prepared (`supabase/schema.sql`,
   `railway.toml`) but not executed. Real-time anomaly alerts (email/WebSockets) are
   listed in the PRD as post-MVP.
8. **Zone-drawing persistence is per-installation**, tied to one store layout — multi-
   store support is out of scope for the MVP.

---

## 8. Reproducibility map

| claim | command / artifact |
|---|---|
| detection MAE/RMSE, threshold table | `cd backend && python -m evaluation.metrics ../docs/evidence/detection_results.csv` |
| tracking IDs before/after tuning | `notebooks/02_tracking.ipynb` + `docs/evidence/tracking_annotated.mp4` |
| anomaly precision/recall/F1 | `cd backend && python scripts/score_labels.py` (labels: `data/labels/samples.csv`) |
| anomaly trajectory plot | `python backend/scripts/plot_anomaly_trajectories.py` → `docs/evidence/anomaly_trajectories.png` |
| autoencoder training + threshold | `cd backend && python training/train_autoencoder.py` → MLflow run (`mlflow ui --backend-store-uri mlruns`) |
| LLM prompt sweep (10 cases) | `python backend/scripts/report_prompt_sweep.py --live` |
| pipeline timing | any upload, then the `pipeline finished …` line in the backend log |
| screenshots of the UI | `node frontend/scripts/screenshots.mjs <completed-job-id>` |
| full roadmap status | `docs/epics.md` |
