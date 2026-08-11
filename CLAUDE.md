# CLAUDE.md — ShopLens Project

> Drop this file in the project root and open the folder in Claude. Claude reads it automatically and uses it to bias every choice toward the project's goals.
>
> No setup needed. You only do this once per project.
>
> **This file is instructions for Claude, not a docs dump.** The full detail lives in three docs in this repo — read them on demand:
> - `prd.md` — product requirements (problem, user, features, success metrics, resolved questions)
> - `tech.md` — tech stack with the one-line reason for every choice
> - `epics.md` — the complete 10-week roadmap with every daily task as a checklist

---

## What this project builds

ShopLens turns existing CCTV footage into retail intelligence for small shops — person detection, multi-person tracking, zone analytics, floor heatmaps, anomaly detection, and auto-generated LLM insight reports. No GPU, no expensive hardware. A small shop owner uploads a 2-minute clip and gets a plain-English report on what's happening in their store.

The student building this will present it to a mentor and demo it live. The output must be **measurable, reproducible, and demoable** — proof of accuracy beats slick visuals.

## Tone for explaining things to the user

The person you're helping is a student (likely new to ML/deep learning) presenting this to a mentor. Talk like a smart friend, not a tutorial.

- **Plain English first.** No jargon dropped without a one-line explanation.
- **Concrete over abstract.** Show what a metric means with a real example, not a definition (e.g. "MAE 3 means the model is off by 3 people per frame on average").
- **One step at a time.** If a task has multiple parts, walk through them in order. Don't dump everything in one paragraph.
- **Reassure on errors.** If something goes wrong, say what's likely happening before listing fixes.
- **Skip the filler.** Get to the action.
- **Explain the "why"** — the mentor will ask. Every tech choice in `tech.md` has a one-line reason; repeat it when asked.

## Default stack

Every choice below has a reason. Learn the one-line reason — that's what you say to your mentor.

**Hard constraints (non-negotiable):**
- **CPU only** — no GPU available. All models must run on CPU (Colab or Railway free tier). Never write GPU-dependent code.
- **Upload-based processing** — not real-time streaming. MVP.
- **Max video length: 2 minutes** — and sample every 5th frame (2 min → 720 frames). Never process every frame.
- **Mall Dataset** for training/evaluation; YouTube retail footage for demo visuals (dual-dataset approach).

**Computer Vision:** YOLOv8n (fastest CPU-friendly detector, `ultralytics`) → DeepSORT (`deep_sort_realtime`) → OSNet re-ID → OpenCV for frame I/O. All CV models use PyTorch — never mix frameworks.

**Anomaly Detection:** Autoencoder in PyTorch (unsupervised — no labeled anomaly data needed, this is the real ML the student built) + DBSCAN (scikit-learn) for trajectory clustering.

**Backend:** FastAPI (async, handles slow I/O without blocking) + Redis + RQ (background job queue, user gets a `job_id` and polls) + PostgreSQL/Supabase (relational: zones → analytics → reports).

**LLM:** Groq API free tier (Llama-3.3-70B). Not Ollama — Railway can't run it. Fast, free, no GPU.

**Frontend:** React (canvas-based zone drawing needs it — Streamlit can't do this) + Recharts + Fabric.js.

**Deployment:** Railway (backend — stays awake on free tier), Vercel (frontend), Cloudflare R2 (video storage, free egress), Supabase (managed PostgreSQL).

## Skills to use proactively

Install with `npx skills add <name>`. Use them at these points:

**Must have:**
- `mattpocock/skills/triage` — before starting any feature or epic, understand what to build first
- `mattpocock/skills/implement` — how to implement features properly without going off track
- `supabase/agent-skills/supabase` — Supabase best practices, table setup (Epics 3 and 8)
- `mattpocock/skills/diagnosing-bugs` — when the CV pipeline breaks, debug systematically

**Useful for frontend:**
- `anthropics/skills/frontend-design` — already installed; the React dashboard shouldn't look like a student project
- `vercel-labs/agent-skills/deploy-to-vercel` — handles the Vercel deploy at Epic 8 without config work

**Workflow:**
- `obra/superpowers/systematic-debugging` — structured debugging when stuck
- `mattpocock/skills/handoff` — when switching between sessions, picks up exactly where the last session left off

If a skill isn't installed, suggest installing it. Don't refuse the task without it.

## Key design decisions (already resolved — don't relitigate)

1. **Zones saved per store layout** — user draws zones once; every new video reuses them. Don't reset per upload.
2. **Max video 2 minutes, sample every 5th frame** — full-frame processing is 3-5 hours per clip. Document this as a design decision.
3. **LLM is Groq API** — Llama-3.3-70B via free tier. Not Ollama.
4. **Anomaly alerts flagged in dashboard + report only (MVP)** — no WebSockets/email. Note "future work: real-time alerts via email".
5. **Privacy: blur faces before storing** — non-negotiable. Original frames never saved. One extra step after detection:

```python
for box in detected_persons:
    face_region = crop_face_from_box(box)
    blurred = cv2.GaussianBlur(face_region, (99, 99), 30)
    frame[face_y:face_y+h, face_x:face_x+w] = blurred
```

## Pipeline workflow rules

When building the video processing pipeline, follow this order and these rules:

1. **One RQ job runs the whole pipeline**: read frames (every 5th) → YOLOv8 detect → DeepSORT track → zone analytics → heatmap → autoencoder anomaly scores → Groq report
2. **Progress updates to Redis at every step**: "Step 2/7: Tracking..."
3. **Blur faces immediately after detection, before anything is stored**
4. **Zone data comes from Supabase** (drawn once, reused every video)
5. **Results saved to Supabase** — zones, analytics, anomalies, reports are related entities
6. **Anomaly threshold: 95th percentile of reconstruction error** on the training set
7. **Endpoint set**: `POST /upload`, `GET /status/{job_id}`, `GET /analytics/{job_id}`, `GET /heatmap/{job_id}`, `GET /report/{job_id}`

## Build process (10 weeks → 9 epics)

> ⚠️ **Warning:** Stop working after each epic — don't start the next epic until the user says continue. **Never commit or push** unless the user explicitly says to.

The full plan with every daily task is in `epics.md` — read it before starting any epic. Claude's job is to help the student tick the boxes, one epic at a time, in order:

- [ ] **Epic 1 — Detection (Week 1):** YOLOv8 on all 2000 Mall Dataset frames, MAE/MSE vs ground truth, threshold-vs-MAE table
- [ ] **Epic 2 — Tracking (Week 2):** DeepSORT with unique IDs, annotated video via `VideoWriter`, trajectory JSON, ID-switch tuning
- [ ] **Epic 3 — Zone System (Week 3):** Fabric.js zone drawing UI, zones in Supabase, per-zone visitors/dwell/peak hour
- [ ] **Epic 4 — Heatmap (Week 4):** Gaussian heatmap PNG + morning/afternoon/evening segments, FastAPI endpoint, React display
- [ ] **Epic 5-6 — Anomaly Detection (Weeks 5-6):** autoencoder trained on normal movement, MLflow-tracked, 3 anomaly types (loitering, crowd spike, zone avoidance), precision/recall
- [ ] **Epic 6 — LLM Report (Week 7):** Groq prompt template → specific actionable insights, `POST /reports/generate`, downloadable report
- [ ] **Epic 7 — Backend + Job Queue (Week 8):** full pipeline as one RQ job with progress, 5 endpoints, React progress bar polling every 3s
- [ ] **Epic 8 — Deployment (Week 9):** Supabase + R2 setup, Railway backend, Vercel frontend, 5 test videos end-to-end
- [ ] **Epic 9 — Evaluation + Docs (Week 10):** results table (MAE/MSE, ID switch rate, precision/recall), demo video <3 min, README, technical report

## File structure (target repo layout)

```
shoplens/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + endpoints
│   │   ├── routes/           # upload, status, analytics, heatmap, report
│   │   └── db.py             # Supabase client
│   ├── workers/
│   │   └── pipeline.py       # full RQ job: detect → track → analytics → report
│   ├── cv/
│   │   ├── detector.py       # YOLOv8
│   │   ├── tracker.py        # DeepSORT
│   │   ├── zones.py          # point-in-polygon + dwell time
│   │   ├── heatmap.py        # Gaussian heatmap generation
│   │   ├── anomaly.py        # autoencoder + DBSCAN
│   │   └── blur.py           # face blurring
│   ├── models/               # trained autoencoder (MLflow registry)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ZoneCanvas.tsx    # Fabric.js zone drawing
│   │   │   ├── Heatmap.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ProgressBar.tsx   # polls /status every 3s
│   │   │   └── Report.tsx
│   └── package.json
└── notebooks/                # Colab: detection eval, tracking, autoencoder training
```

## Anti-patterns (don't do these)

- ❌ Streamlit for the frontend (can't do canvas zone drawing)
- ❌ GPU-dependent code (`cuda()`, `.to('cuda')`) — CPU only, always
- ❌ Processing every frame of a video (sample every 5th)
- ❌ Saving or storing original (unblurred) frames — privacy is non-negotiable
- ❌ Ollama for the LLM (can't run on Railway)
- ❌ Real-time anomaly alerts (WebSockets/email) — MVP flags in dashboard + report only
- ❌ Facial recognition or identity tracking of individuals (out of scope)
- ❌ POS/sales integration, inventory, loyalty tracking (out of scope)
- ❌ Skipping MLflow experiment tracking for the autoencoder — the mentor needs proof of real ML work
- ❌ Debug print statements left in final code (Week 10 cleanup)

## Code style

- **No comments unless the WHY isn't obvious** from the code itself; one line max
- Short functions, one responsibility each
- No debug print statements in final code — use logging with the pipeline's progress callback
- CV code runs in the RQ worker, not in FastAPI request handlers (async doesn't make CPU work fast)
- Keep metrics code (MAE/MSE, precision/recall) in notebooks or a metrics module so evaluation is reproducible

---

*ShopLens — 10-week project roadmap in `epics.md`.*
