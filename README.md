# ShopLens

Turn existing CCTV footage into retail intelligence for small shops — person detection, multi-person tracking, zone analytics, floor heatmaps, anomaly detection, and an auto-generated plain-English insight report. No GPU required.

<!-- TODO(epic-9 day 3): one-paragraph non-technical explanation + demo GIF -->

## Architecture

```
User uploads video (max 2 min)
       ↓
React frontend → FastAPI
                   ↓
        background thread (one per upload)
        OpenCV reads frames (every 5th)
        YOLOv8n detects people → faces blurred
        DeepSORT tracks IDs
        Zone analytics computed
        Heatmap generated
        Autoencoder scores anomalies
        Groq LLM writes the insight report
                   ↓
        data/shoplens.db (SQLite) + storage/ (local disk)
                   ↓
React dashboard polls → stats, zone table, heatmap, anomaly timeline, report
```

> **Current vs planned:** this is the MVP that runs entirely locally — jobs run on an
> in-process `threading.Thread`, state lives in SQLite + local disk. The Redis/RQ queue,
> Supabase and Cloudflare R2 in `tech.md` are the Epic 8–9 deployment targets; nothing in
> the code requires them yet.

## Repo layout

```
shoplens/
├── CLAUDE.md              instructions for the AI assistant working on this repo
├── .env.example           copy to .env; only GROQ_API_KEY is needed for reports
├── railway.toml           Railway deploy config (Epic 9)
├── backend/
│   ├── app/
│   │   ├── main.py        FastAPI app + router registration
│   │   ├── config.py      repo-relative paths + env settings
│   │   ├── db.py          SQLite schema and queries
│   │   ├── jobs.py        background-thread queue + resume on restart
│   │   ├── storage.py     uploaded-video storage
│   │   ├── routes/        upload, status, jobs, analytics, heatmap, report, zones
│   │   └── services/      Groq report generation
│   ├── cv/                detector, tracker, zones, heatmap, anomaly, blur
│   ├── workers/pipeline.py  one job: detect → track → zones → heatmap → anomalies → report
│   ├── evaluation/metrics.py  MAE/RMSE and precision/recall helpers
│   ├── training/          train_autoencoder.py, register_model.py (MLflow registry)
│   ├── scripts/           evaluation + data scripts (verify_zones_100, score_labels, ...)
│   ├── models/            autoencoder.pth, threshold.json, zone_index.json
│   └── Dockerfile, requirements.txt
├── frontend/              React + Vite + TypeScript dashboard
│   └── src/components/    ZoneCanvas, Dashboard, Heatmap, ProgressBar, Report
├── notebooks/             Colab: detection, tracking, autoencoder training
├── data/
│   ├── mall_dataset/      extracted Mall Dataset frames (git-ignored)
│   ├── labels/            samples.csv, results.json, labeling worksheets
│   ├── out/               mall heatmaps + autoencoder training plot
│   ├── shoplens.db        SQLite database (git-ignored)
│   └── *.json             generated position/trajectory caches (git-ignored)
├── storage/               uploaded videos + per-job heatmaps (git-ignored)
├── docs/                  prd, tech, epics, guide, walkthrough, evidence
└── supabase/schema.sql    table definitions for the Epic 9 cloud deploy
```

## Run locally

Prereqs: Python 3.11+, Node 18+. **No Docker, Redis or RQ required** — processing runs on a
background thread inside the API process.

```bash
# 1. Backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env            # optional; GROQ_API_KEY only affects the report step

cd backend
uvicorn app.main:app --reload   # http://localhost:8000/health
```

```bash
# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Upload a clip under 2 minutes, draw zones once (they persist for every later video), then
watch the progress bar through detection → tracking → zones → heatmap → anomalies → report.

## Evaluation

Results on the Mall Dataset (2000 frames) and 86 hand-labeled visits:

| metric | value |
|---|---|
| detection MAE | 5.71 people/frame |
| detection RMSE | 6.82 |
| best confidence threshold | 0.10 |
| unique track IDs (200 frames) | 103 tuned (208 before tuning) |
| anomaly precision / recall / F1 | 0.419 / 0.520 / 0.464 |

Reproduce:

```bash
cd backend
python -m evaluation.metrics ../docs/evidence/detection_results.csv
python scripts/score_labels.py
```

The threshold-vs-MAE table and ID-switch comparison live in
[`docs/shoplens_guide.md`](docs/shoplens_guide.md) and
[`docs/code_walkthrough.md`](docs/code_walkthrough.md).

## Docs

| file | what's in it |
|---|---|
| [`docs/prd.md`](docs/prd.md) | problem, target user, success metrics |
| [`docs/tech.md`](docs/tech.md) | every stack choice with a one-line reason |
| [`docs/epics.md`](docs/epics.md) | 10-week roadmap — daily checklist + Definitions of Done |
| [`docs/shoplens_guide.md`](docs/shoplens_guide.md) | Epic 1–2 walkthrough (detection + tracking) |
| [`docs/code_walkthrough.md`](docs/code_walkthrough.md) | annotated code explanation for the mentor |
| [`docs/evidence/`](docs/evidence/) | screenshots, detection CSV, annotated video for Epic 1–2 |

## Deployment

- **Backend** → Railway (`railway.toml`). A second service can run the worker once Epic 8
  moves processing to Redis + RQ.
- **Frontend** → Vercel (project root set to `frontend/`).
- **Storage** → Cloudflare R2 (currently `storage/` on local disk).
- **Database** → Supabase; run `supabase/schema.sql` once (currently `data/shoplens.db`).

## Performance

<!-- TODO(epic-8 day 5): measure and document processing time per minute of video -->

## Screenshots

<!-- TODO(epic-9 day 3): dashboard, zone drawing UI, heatmap, anomaly timeline -->
