# ShopLens — 10 Week Roadmap

Each week has one Epic (big goal) broken into daily tasks.
Complete each task before moving to the next. Don't skip ahead.
Tick the checkboxes as you go. An Epic is done only when its Definition of Done checklist is fully checked.

---

## Epic 1 — Detection Pipeline (Week 1)

**Goal:** YOLOv8 detecting people on Mall Dataset frames with measurable accuracy.

**Day 1**
- [ ] Download Mall Dataset from `https://personal.ie.cuhk.edu.hk/~ccloy/downloads_mall_dataset.html`
- [ ] Explore the dataset — look at 10 frames manually, understand folder structure
- [ ] Read `mall_gt.mat` ground truth annotations in Python using `scipy.io.loadmat`

**Day 2**
- [ ] Set up Google Colab notebook
- [ ] Install: `ultralytics`, `opencv-python-headless`, `scipy`, `matplotlib`
- [ ] Run YOLOv8n on a single mall frame, visualize bounding boxes

**Day 3**
- [ ] Run detection on 50 frames
- [ ] Extract person count per frame
- [ ] Compare against ground truth count from `mall_gt.mat`

**Day 4**
- [ ] Compute MAE and MSE across 50 frames
- [ ] Tune confidence threshold to improve accuracy
- [ ] Document results in a table (threshold vs MAE)

**Day 5**
- [ ] Run on all 2000 frames
- [ ] Save results to CSV: `frame_id, detected_count, gt_count, mae`
- [ ] Write brief summary: detection accuracy, failure cases, findings

**Week 1 output:** Colab notebook + CSV with detection results + accuracy metrics

**Definition of Done**
- [ ] YOLOv8 runs on all 2000 Mall Dataset frames
- [ ] CSV saved with `frame_id, detected_count, gt_count, mae`
- [ ] MAE/MSE computed and documented in a threshold-vs-MAE table
- [ ] Accuracy summary written (failure cases, findings)
- [ ] Colab notebook is reproducible from scratch

---

## Epic 2 — Tracking Pipeline (Week 2)

**Goal:** DeepSORT tracking unique IDs across frames reliably.

**Day 1**
- [ ] Install `deep_sort_realtime`
- [ ] Understand DeepSORT input format — bounding boxes + confidence scores
- [ ] Run DeepSORT on 10 consecutive mall frames, print tracked IDs

**Day 2**
- [ ] Build a pipeline: frame → YOLOv8 detections → DeepSORT → tracked persons
- [ ] Visualize: draw bounding boxes with ID labels on frames
- [ ] Export annotated frames as video using OpenCV `VideoWriter`

**Day 3**
- [ ] Track across 200 frames
- [ ] Count unique IDs (unique visitors)
- [ ] Identify ID switching issues (same person gets new ID) and log them

**Day 4**
- [ ] Tune DeepSORT `max_age` and `n_init` parameters to reduce ID switches
- [ ] Re-run and compare ID switch count before vs after tuning

**Day 5**
- [ ] Build trajectory recorder: for each ID, store list of (x, y, frame) positions
- [ ] Visualize trajectories as lines overlaid on store frame
- [ ] Save trajectories to JSON

**Week 2 output:** Tracking pipeline + annotated video + trajectory JSON

**Definition of Done**
- [ ] Annotated video with ID labels exported via `VideoWriter`
- [ ] Trajectories saved to JSON
- [ ] ID switch count measured before and after tuning (documented comparison)
- [ ] Unique visitor count extracted from 200+ frames

---

## Epic 3 — Zone System (Week 3)

**Goal:** User-defined zones with per-zone visitor counts and dwell time.

**Day 1**
- [ ] Learn Fabric.js basics — draw a rectangle on a canvas image in React
- [ ] Build a simple zone drawing component: load mall frame, draw zones, save zone coordinates

**Day 2**
- [ ] Store zone coordinates (polygon points) in Supabase
- [ ] Load zones back and overlay them on video frames in OpenCV

**Day 3**
- [ ] Build zone intersection logic: given a person's (x,y) centroid, which zone are they in?
- [ ] Test on 100 frames — print zone assignments per person per frame

**Day 4**
- [ ] Calculate dwell time per zone per person: how many consecutive frames in the zone × frame interval
- [ ] Aggregate: average dwell time per zone across all visitors

**Day 5**
- [ ] Build zone analytics summary:
  - [ ] Total unique visitors per zone
  - [ ] Average dwell time per zone
  - [ ] Peak hour per zone (hour with most visitors)
- [ ] Save to Supabase

**Week 3 output:** Zone drawing UI + zone analytics saved to database

**Definition of Done**
- [ ] Zone drawing UI loads a frame and saves polygon coordinates
- [ ] Zones persist to Supabase and reload correctly
- [ ] Zone intersection logic verified on 100 frames
- [ ] Per-zone visitor counts + dwell times stored in Supabase
- [ ] Zone analytics summary (visitors, dwell, peak hour) computed

---

## Epic 4 — Heatmap Generation (Week 4)

**Goal:** Visual floor heatmap showing traffic intensity per zone.

**Day 1**
- [ ] Understand Gaussian heatmap generation — add a Gaussian blob at each person centroid
- [ ] Build `generate_heatmap(frame, positions)` function
- [ ] Visualize on 1 frame

**Day 2**
- [ ] Aggregate heatmap across all 2000 frames
- [ ] Overlay heatmap on store frame using `cv2.addWeighted`
- [ ] Export as PNG

**Day 3**
- [ ] Build time-segmented heatmaps: morning (9am-12pm), afternoon (12-5pm), evening (5-9pm)
- [ ] Compare heatmaps across time segments

**Day 4**
- [ ] Build heatmap API endpoint in FastAPI: accepts `video_id` + `time_range`, returns heatmap PNG
- [ ] Test endpoint with Postman

**Day 5**
- [ ] Display heatmap in React dashboard
- [ ] Add time range selector (morning/afternoon/evening)
- [ ] Heatmap updates when time range changes

**Week 4 output:** Dynamic heatmap in dashboard with time segmentation

**Definition of Done**
- [ ] Aggregate heatmap PNG exported for all 2000 frames
- [ ] Morning/afternoon/evening heatmaps generated and compared
- [ ] FastAPI heatmap endpoint returns valid PNG (tested in Postman)
- [ ] Heatmap renders in dashboard and updates on time-range change

---

## Epic 5 — Anomaly Detection (Week 5-6)

**Goal:** Autoencoder detects unusual movement patterns. This is your core ML component.

**Week 5**

**Day 1**
- [ ] Understand autoencoders — encoder compresses input, decoder reconstructs. High reconstruction error = anomaly
- [ ] Define feature vector per person per frame: (zone_id, dwell_time, velocity, direction_change)

**Day 2**
- [ ] Extract feature vectors from all trajectories in Mall Dataset
- [ ] Normalize features (StandardScaler)
- [ ] Split into train (normal behavior) / test sets

**Day 3**
- [ ] Build autoencoder in PyTorch: Input(4) → 8 → 4 → 2 → 4 → 8 → Output(4)
- [ ] Train on normal movement features
- [ ] Track training loss with MLflow

**Day 4**
- [ ] Compute reconstruction error on test set
- [ ] Plot error distribution — set anomaly threshold at 95th percentile
- [ ] Visualize: normal vs anomalous trajectories on store frame

**Day 5**
- [ ] Evaluate false positive rate on known normal behavior
- [ ] Tune threshold, retrain, compare experiments in MLflow
- [ ] Save best model with MLflow Model Registry

**Week 6**

**Day 1**
- [ ] Define 3 anomaly types: loitering (high dwell, low movement), crowd spike (sudden count increase), zone avoidance (zone consistently skipped)
- [ ] Label examples of each from Mall Dataset manually

**Day 2**
- [ ] Integrate autoencoder into main pipeline
- [ ] Flag anomalous trajectories in real-time during video processing

**Day 3**
- [ ] Build anomaly alert system: store flagged events in Supabase with timestamp, zone, anomaly type

**Day 4**
- [ ] Display anomaly alerts in React dashboard: timeline of alerts, highlight anomalous zones

**Day 5**
- [ ] Evaluate: compute precision/recall on manually labeled anomaly examples
- [ ] Document results

**Week 5-6 output:** Trained autoencoder + MLflow experiment logs + anomaly alerts in dashboard

**Definition of Done**
- [ ] Autoencoder trained with loss tracked in MLflow
- [ ] Best model registered in MLflow Model Registry
- [ ] Anomaly threshold set at 95th percentile of reconstruction error
- [ ] All 3 anomaly types (loitering, crowd spike, zone avoidance) flagged during processing
- [ ] Alerts stored in Supabase and shown in dashboard timeline
- [ ] Precision/recall computed on labeled examples and documented

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
| - [ ] | 1 | Detection | YOLOv8 on Mall Dataset with MAE metrics |
| - [ ] | 2 | Tracking | DeepSORT with trajectory JSON |
| - [ ] | 3 | Zone System | Zone drawing UI + dwell time analytics |
| - [ ] | 4 | Heatmap | Dynamic heatmap in dashboard |
| - [ ] | 5-6 | Anomaly Detection | Trained autoencoder + MLflow logs |
| - [ ] | 7 | LLM Report | Auto-generated insight report |
| - [ ] | 8 | Backend | Full async pipeline with job queue |
| - [ ] | 9 | Deployment | Live at public URL |
| - [ ] | 10 | Evaluation | Metrics, demo, documentation |
