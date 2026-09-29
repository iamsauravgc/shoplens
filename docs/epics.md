# ShopLens — 10 Week Roadmap

Each week has one Epic (big goal) broken into daily tasks.
Complete each task before moving to the next. Don't skip ahead.
Tick the checkboxes as you go. An Epic is done only when its Definition of Done checklist is fully checked.

---

## Epic 1 — Detection Pipeline (Week 1)

**Goal:** YOLOv8 detecting people on Mall Dataset frames with measurable accuracy.

**Day 1**
- [x] Download Mall Dataset from `https://personal.ie.cuhk.edu.hk/~ccloy/downloads_mall_dataset.html`
- [x] Explore the dataset — look at 10 frames manually, understand folder structure
- [x] Read `mall_gt.mat` ground truth annotations in Python using `scipy.io.loadmat`

**Day 2**
- [x] Set up Google Colab notebook
- [x] Install: `ultralytics`, `opencv-python-headless`, `scipy`, `matplotlib`
- [x] Run YOLOv8n on a single mall frame, visualize bounding boxes

**Day 3**
- [x] Run detection on 50 frames
- [x] Extract person count per frame
- [x] Compare against ground truth count from `mall_gt.mat`

**Day 4**
- [x] Compute MAE and MSE across 50 frames
- [x] Tune confidence threshold to improve accuracy
- [x] Document results in a table (threshold vs MAE) — *added to `shoplens_guide.md` § Threshold Tuning*

**Day 5**
- [x] Run on all 2000 frames
- [x] Save results to CSV: `frame_id, detected_count, gt_count, mae` — *`shoplens_drive/detection_results.csv`, 2000 rows; per-frame `error` column carries mae (`mae` = mean of `error`), plus `conf`*
- [x] Write brief summary: detection accuracy, failure cases, findings

**Week 1 output:** Colab notebook + CSV with detection results + accuracy metrics

**Definition of Done**
- [x] YOLOv8 runs on all 2000 Mall Dataset frames — *`detection_results.csv` has 2000 rows*
- [x] CSV saved with `frame_id, detected_count, gt_count, mae` — *see column note above*
- [x] MAE/MSE computed and documented in a threshold-vs-MAE table — *7 thresholds, best `conf=0.1` MAE 5.88; full run MAE 5.71 / RMSE 6.82*
- [x] Accuracy summary written (failure cases, findings) — *`shoplens_guide.md` § Failure Analysis + `shoplens_drive/failure_cases.png`*
- [x] Colab notebook is reproducible from scratch — *`notebooks/detection.ipynb`*

---

## Epic 2 — Tracking Pipeline (Week 2)

**Goal:** DeepSORT tracking unique IDs across frames reliably.

**Day 1**
- [x] Install `deep_sort_realtime`
- [x] Understand DeepSORT input format — bounding boxes + confidence scores
- [x] Run DeepSORT on 10 consecutive mall frames, print tracked IDs

**Day 2**
- [x] Build a pipeline: frame → YOLOv8 detections → DeepSORT → tracked persons
- [x] Visualize: draw bounding boxes with ID labels on frames
- [x] Export annotated frames as video using OpenCV `VideoWriter`

**Day 3**
- [x] Track across 200 frames
- [x] Count unique IDs (unique visitors)
- [x] Identify ID switching issues (same person gets new ID) and log them

**Day 4**
- [x] Tune DeepSORT `max_age` and `n_init` parameters to reduce ID switches
- [x] Re-run and compare ID switch count before vs after tuning — *208 → 103 unique IDs, 105 fewer switches*

**Day 5**
- [x] Build trajectory recorder: for each ID, store list of (x, y, frame) positions
- [x] Visualize trajectories as lines overlaid on store frame
- [x] Save trajectories to JSON

**Week 2 output:** Tracking pipeline + annotated video + trajectory JSON

**Definition of Done**
- [x] Annotated video with ID labels exported via `VideoWriter` — *`shoplens_drive/tracking_annotated.mp4` (12 MB)*
- [x] Trajectories saved to JSON — *`data/trajectories.json`*
- [x] ID switch count measured before and after tuning (documented comparison) — *baseline 208 / best 103 over 200 frames → `code_walkthrough.md`*
- [x] Unique visitor count extracted from 200+ frames — *200-frame run, 208 baseline / 103 tuned*

---

## Epic 3 — Zone System (Week 3)

**Goal:** User-defined zones with per-zone visitor counts and dwell time.

**Day 1**
- [x] Learn Fabric.js basics — draw a rectangle on a canvas image in React
- [x] Build a simple zone drawing component: load mall frame, draw zones, save zone coordinates

**Day 2**
- [x] Store zone coordinates (polygon points) in Supabase — *substituted: local SQLite*
- [x] Load zones back and overlay them on video frames in OpenCV

**Day 3**
- [x] Build zone intersection logic: given a person's (x,y) centroid, which zone are they in?
- [x] Test on 100 frames — print zone assignments per person per frame

**Day 4**
- [x] Calculate dwell time per zone per person: how many consecutive frames in the zone × frame interval
- [x] Aggregate: average dwell time per zone across all visitors

**Day 5**
- [x] Build zone analytics summary:
  - [x] Total unique visitors per zone
  - [x] Average dwell time per zone
  - [x] Peak hour per zone (hour with most visitors)
- [x] Save to Supabase — *substituted: local SQLite*

**Week 3 output:** Zone drawing UI + zone analytics saved to database

**Definition of Done**
- [x] Zone drawing UI loads a frame and saves polygon coordinates
- [x] Zones persist to Supabase and reload correctly — *substituted: local SQLite*
- [x] Zone intersection logic verified on 100 frames — `backend/scripts/verify_zones_100.py`
- [x] Per-zone visitor counts + dwell times stored in Supabase — *substituted: local SQLite*
- [x] Zone analytics summary (visitors, dwell, peak hour) computed

---

## Epic 4 — Heatmap Generation (Week 4)

**Goal:** Visual floor heatmap showing traffic intensity per zone.

**Day 1**
- [x] Understand Gaussian heatmap generation — add a Gaussian blob at each person centroid
- [x] Build `generate_heatmap(frame, positions)` function
- [x] Visualize on 1 frame

**Day 2**
- [x] Aggregate heatmap across all 2000 frames
- [x] Overlay heatmap on store frame using `cv2.addWeighted`
- [x] Export as PNG

**Day 3**
- [x] Build time-segmented heatmaps: morning (9am-12pm), afternoon (12-5pm), evening (5-9pm)
- [x] Compare heatmaps across time segments — *segments are clip-relative thirds (CCTV has no wall clock)*

**Day 4**
- [x] Build heatmap API endpoint in FastAPI: accepts `video_id` + `time_range`, returns heatmap PNG
- [x] Test endpoint with Postman — *substituted: curl / HTTP client, all 4 ranges return 200 with distinct bytes*

**Day 5**
- [x] Display heatmap in React dashboard
- [x] Add time range selector (morning/afternoon/evening)
- [x] Heatmap updates when time range changes

**Week 4 output:** Dynamic heatmap in dashboard with time segmentation

**Definition of Done**
- [x] Aggregate heatmap PNG exported for all 2000 frames — `data/out/heatmaps/mall_full.png`
- [x] Morning/afternoon/evening heatmaps generated and compared — `data/out/heatmaps/mall_*.png`
- [x] FastAPI heatmap endpoint returns valid PNG (tested in Postman) — *tested via HTTP client*
- [x] Heatmap renders in dashboard and updates on time-range change

---

## Epic 5 — Anomaly Detection (Week 5-6)

**Goal:** Autoencoder detects unusual movement patterns. This is your core ML component.

**Week 5**

**Day 1**
- [x] Understand autoencoders — encoder compresses input, decoder reconstructs. High reconstruction error = anomaly
- [x] Define feature vector per person per frame: (zone_id, dwell_time, velocity, direction_change)

**Day 2**
- [x] Extract feature vectors from all trajectories in Mall Dataset
- [x] Normalize features (StandardScaler)
- [x] Split into train (normal behavior) / test sets

**Day 3**
- [x] Build autoencoder in PyTorch: Input(4) → 8 → 4 → 2 → 4 → 8 → Output(4)
- [x] Train on normal movement features
- [x] Track training loss with MLflow

**Day 4**
- [x] Compute reconstruction error on test set
- [x] Plot error distribution — set anomaly threshold at 95th percentile
- [ ] Visualize: normal vs anomalous trajectories on store frame — *not yet produced*

**Day 5**
- [x] Evaluate false positive rate on known normal behavior — *18 FP out of 61 labeled-normal visits*
- [x] Tune threshold, retrain, compare experiments in MLflow — *3 runs in experiment `shoplens-autoencoder`*
- [x] Save best model with MLflow Model Registry — *registered as `shoplens-autoencoder` v1*

**Week 6**

**Day 1**
- [x] Define 3 anomaly types: loitering (high dwell, low movement), crowd spike (sudden count increase), zone avoidance (zone consistently skipped)
- [x] Label examples of each from Mall Dataset manually — *86 labeled visits in `data/labels/samples.csv`*

**Day 2**
- [x] Integrate autoencoder into main pipeline
- [x] Flag anomalous trajectories in real-time during video processing

**Day 3**
- [x] Build anomaly alert system: store flagged events in Supabase with timestamp, zone, anomaly type — *substituted: local SQLite*

**Day 4**
- [x] Display anomaly alerts in React dashboard: timeline of alerts, highlight anomalous zones

**Day 5**
- [x] Evaluate: compute precision/recall on manually labeled anomaly examples
- [x] Document results — *precision 0.419, recall 0.520, F1 0.464 → `data/labels/results.json`*

**Week 5-6 output:** Trained autoencoder + MLflow experiment logs + anomaly alerts in dashboard

**Definition of Done**
- [x] Autoencoder trained with loss tracked in MLflow
- [x] Best model registered in MLflow Model Registry — *`shoplens-autoencoder` v1*
- [x] Anomaly threshold set at 95th percentile of reconstruction error
- [x] All 3 anomaly types (loitering, crowd spike, zone avoidance) flagged during processing
- [x] Alerts stored in Supabase and shown in dashboard timeline — *substituted: local SQLite*
- [x] Precision/recall computed on labeled examples and documented — *P=0.419, R=0.520, F1=0.464 (13 TP / 18 FP / 12 FN on 86 labeled visits)*

---

## Epic 6 — LLM Insight Report (Week 7)

**Goal:** Auto-generated plain English weekly report from analytics data.

**Day 1**
- [ ] Get Groq API key (free at console.groq.com)
- [ ] Test Groq API with simple prompt: "Summarize this retail data: {json}"
- [ ] Understand token limits and response format

**Day 2**
- [ ] Build `format_analytics_for_llm(analytics_dict)` — converts zone stats, anomalies, peak hours into structured JSON prompt
- [ ] Design prompt template that produces useful insights, not generic text

**Day 3**
- [ ] Generate sample reports from Mall Dataset analytics
- [ ] Iterate prompt until output is specific and actionable (not "Zone A had more visitors")
- [ ] Test 10 different analytics inputs

**Day 4**
- [ ] Build FastAPI endpoint: `POST /reports/generate` → triggers LLM, saves report to Supabase
- [ ] Add report to dashboard: downloadable PDF using `reportlab` or just styled HTML

**Day 5**
- [ ] Edge cases: what if a zone has zero visitors? What if anomaly count is 0?
- [ ] Handle all edge cases in prompt and response parsing

**Week 7 output:** Auto-generated insight report visible in dashboard and downloadable

**Definition of Done**
- [ ] Groq integration working with valid API key
- [ ] Prompt template produces specific, actionable insights (tested on 10 inputs)
- [ ] `POST /reports/generate` endpoint saves report to Supabase
- [ ] Report visible + downloadable from dashboard
- [ ] All edge cases (empty zones, zero anomalies) handled gracefully

---

## Epic 7 — Full Backend + Job Queue (Week 8)

**Goal:** Complete FastAPI backend with async video processing via job queue.

**Day 1**
- [ ] Set up Redis locally (Docker) and install `rq`
- [ ] Build basic job: `process_video(video_path)` runs as background RQ job
- [ ] Test: submit job, poll status, get result

**Day 2**
- [ ] Build full pipeline worker: video → detection → tracking → zone analytics → heatmap → anomaly → LLM report, all in one RQ job
- [ ] Add progress updates to Redis: "Step 2/7: Tracking..."

**Day 3**
- [ ] Build FastAPI endpoints:
  - [ ] `POST /upload` → saves video to R2, queues job, returns `job_id`
  - [ ] `GET /status/{job_id}` → returns progress
  - [ ] `GET /analytics/{job_id}` → returns full results
  - [ ] `GET /heatmap/{job_id}` → returns heatmap PNG
  - [ ] `GET /report/{job_id}` → returns LLM report

**Day 4**
- [ ] Connect React frontend to all endpoints
- [ ] Build job progress bar: polls `/status` every 3 seconds
- [ ] Show results automatically when job completes

**Day 5**
- [ ] Error handling: what if video is corrupted? What if job fails midway?
- [ ] Add retry logic and error messages in UI

**Week 8 output:** Full end-to-end pipeline working locally

**Definition of Done**
- [ ] Full pipeline (video → report) runs as a single RQ job with progress updates
- [ ] All 5 API endpoints implemented and tested
- [ ] Frontend progress bar polls status and shows results on completion
- [ ] Corrupt-video and mid-job failure cases handled with retry + UI error messages

---

## Epic 8 — Deployment (Week 9)

**Goal:** Live deployed system accessible via public URL.

**Day 1**
- [ ] Set up Supabase project — create tables: `videos`, `zones`, `analytics`, `anomalies`, `reports`
- [ ] Set up Cloudflare R2 bucket for video storage
- [ ] Test R2 upload from Python

**Day 2**
- [ ] Deploy FastAPI to Railway
- [ ] Set environment variables: Supabase URL, R2 credentials, Groq API key
- [ ] Test all API endpoints on Railway URL

**Day 3**
- [ ] Deploy React frontend to Vercel
- [ ] Connect frontend to Railway backend URL
- [ ] Test full flow: upload video → processing → dashboard

**Day 4**
- [ ] Upload 5 different test videos, verify everything works end-to-end
- [ ] Fix deployment bugs (CORS, env vars, file paths)

**Day 5**
- [ ] Performance: how long does processing take per minute of video?
- [ ] Optimize the slowest step (likely detection loop)
- [ ] Document processing time in README

**Week 9 output:** Live deployed ShopLens at public URL

**Definition of Done**
- [ ] Supabase tables + R2 bucket created and connected
- [ ] FastAPI deployed on Railway, all endpoints pass on live URL
- [ ] React frontend deployed on Vercel, connected to backend
- [ ] 5 test videos processed end-to-end without errors
- [ ] Processing time per minute of video measured and documented

---

## Epic 9 — Evaluation + Documentation (Week 10)

**Goal:** Prove it works with numbers. Write everything up cleanly.

**Day 1**
- [ ] Run full evaluation on Mall Dataset:
  - [ ] Detection MAE/MSE vs ground truth
  - [ ] Tracking ID switch rate
  - [ ] Anomaly detection precision/recall
- [ ] Write results table

**Day 2**
- [ ] Record a demo video: upload footage → show processing → walk through dashboard → show insight report
- [ ] Keep it under 3 minutes

**Day 3**
- [ ] Write README.md:
  - [ ] What the project does (non-technical explanation)
  - [ ] Architecture diagram
  - [ ] How to run locally
  - [ ] Evaluation results
  - [ ] Screenshots

**Day 4**
- [ ] Write technical report (for mentor):
  - [ ] Problem statement
  - [ ] Dataset used
  - [ ] Models chosen and why
  - [ ] Evaluation metrics and results
  - [ ] Limitations and future work

**Day 5**
- [ ] Final cleanup: remove debug print statements, fix any UI issues
- [ ] Push everything to GitHub
- [ ] Submit project link + demo video

**Week 10 output:** GitHub repo + demo video + technical report + live deployment

**Definition of Done**
- [ ] Results table with detection MAE/MSE, ID switch rate, anomaly precision/recall
- [ ] Demo video recorded, under 3 minutes
- [ ] README.md complete with architecture diagram and run instructions
- [ ] Technical report written for mentor
- [ ] Code cleaned up, pushed to GitHub, project link + demo submitted

---

## Summary

| Status | Week | Epic | Key Output |
|---|---|---|---|
| - [x] | 1 | Detection | YOLOv8 on Mall Dataset with MAE metrics |
| - [x] | 2 | Tracking | DeepSORT with trajectory JSON |
| - [x] | 3 | Zone System | Zone drawing UI + dwell time analytics |
| - [x] | 4 | Heatmap | Dynamic heatmap in dashboard |
| - [x] | 5-6 | Anomaly Detection | Trained autoencoder + MLflow logs |
| - [ ] | 7 | LLM Report | Auto-generated insight report |
| - [ ] | 8 | Backend | Full async pipeline with job queue |
| - [ ] | 9 | Deployment | Live at public URL |
| - [ ] | 10 | Evaluation | Metrics, demo, documentation |
