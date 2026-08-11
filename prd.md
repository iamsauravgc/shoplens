# ShopLens — Product Requirements Document

## Problem Statement

Small and medium retail shop owners have zero visibility into how customers behave inside their stores. They don't know which shelves get ignored, how long customers stand in certain areas, when rush hours actually happen, or whether their store layout is working. Large malls pay lakhs for professional analytics systems. Small shops have nothing.

ShopLens solves this by turning existing CCTV footage into actionable retail intelligence — no expensive hardware, no manual observation.

---

## Target User

**Primary:** Small retail shop owner or store manager in South/Southeast Asia

- Has 1-3 CCTV cameras already installed
- No data science background — needs plain English insights, not raw numbers
- Makes decisions about shelf placement, staffing, store layout manually today
- Frustrated that they can't measure what's working

---

## Core Features (MVP)

### 1. Video ingestion + person detection
Upload CCTV footage (MP4/AVI) → system detects every person in every frame using YOLOv8. Shows annotated video with bounding boxes as confirmation that detection is working.

### 2. Multi-person tracking
DeepSORT assigns a unique ID to each person across frames. Tracks their path through the store. Foundation for all analytics above this layer.

### 3. Zone definition
User draws custom zones on a static frame (Zone A = entrance, Zone B = shelf row 1, etc.) using an interactive canvas. All analytics are computed per zone, not just a raw heatmap.

### 4. Zone analytics
Per zone: total visitors, average dwell time, peak hour, engagement score. Answers "which zone is underperforming despite high foot traffic?"

### 5. Floor heatmap
Visual overlay on store frame showing hot (high traffic) and cold (ignored) zones. Updates per time segment.

### 6. Anomaly detection
Autoencoder trained on normal movement patterns flags unusual behavior — someone standing in one spot too long, sudden crowd spike, loitering near entrance.

### 7. LLM insight report
Weekly auto-generated plain English summary: "Zone B had 40% more traffic than Zone C but 3x lower dwell time. Consider moving high-margin products to Zone B."

### 8. Dashboard
React frontend showing all analytics, heatmap, zone stats, anomaly alerts, and downloadable insight report.

---

## Nice to Have (Post-MVP)

- Multi-camera support with cross-camera re-identification
- Emotion/engagement detection from face crops
- Real-time live stream processing (MVP is upload-based)
- Mobile app
- Comparison between two time periods

---

## Out of Scope

- Facial recognition or identity tracking of specific individuals
- POS/sales data integration
- Inventory management
- Customer loyalty tracking

---

## Success Metrics

- Person detection accuracy ≥ 85% on Mall Dataset ground truth (MAE < 3)
- Zone dwell time calculation working correctly on 5+ test videos
- Anomaly detection flags at least 3 types of unusual behavior with < 20% false positive rate
- Dashboard loads and displays full analytics within 30 seconds of video processing completing
- LLM report is coherent and actionable (mentor evaluation)

---

## Technical Assumptions

- Upload-based processing, not real-time streaming (MVP)
- No GPU available — all models must run on CPU (Colab or Railway free tier)
- Mall Dataset used for development and evaluation
- Single camera per upload for MVP
- Users are non-technical — UI must be simple

---

Option 3 — Dual dataset approach:

Use Mall Dataset for training and evaluation (has labels, proves accuracy)

Use YouTube retail footage for demo (looks real, impressive visually)

This is actually what researchers do — train/evaluate on benchmark dataset, demo on real footage.

## Open Questions

1. Should zone drawing be saved per store layout or reset per video upload?
Zone drawing — save per store layout
User draws zones once for their store. Every new video uploaded uses the same zones automatically. Resetting every upload makes no sense — store layout doesn't change daily.

2. What is the maximum video length to support (storage + processing time constraint)?
Max video length — 2 minutes

Railway free tier + CPU processing = roughly 3-5 seconds per frame. At 30fps, 2 minutes = 3600 frames = ~3-5 hours processing. Too slow.

Solution: sample every 5th frame instead of every frame. 2 min video → 720 frames → manageable. Document this as a design decision.

3. Which LLM for insight generation — local (Ollama) or API (Groq free tier)?
LLM — Groq API

Ollama runs locally — Railway deployment can't run Ollama. Groq free tier gives Llama-3.3-70B via API, fast, free, no GPU needed. Easy choice.

4. Should anomaly alerts be real-time notifications or just flagged in the report?
Anomaly alerts — flagged in report only (MVP)

Real-time notifications need WebSockets, push notifications, email integration — too much scope for 10 weeks. Flag anomalies in the dashboard and include in the weekly report. Add "future work: real-time alerts via email" in your documentation.

5. How to handle privacy — blur faces before storing processed frames?

Privacy — yes, blur faces

Non-negotiable if you're demoing this publicly or deploying it. One extra step after detection:

python
for box in detected_persons:
    face_region = crop_face_from_box(box)
    blurred = cv2.GaussianBlur(face_region, (99,99), 30)
    frame[face_y:face_y+h, face_x:face_x+w] = blurred

Blurred frames get stored, original never saved. Mention this in PRD as a privacy feature — mentors love this.