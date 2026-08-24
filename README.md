# ShopLens

Turn existing CCTV footage into retail intelligence for small shops — person detection, multi-person tracking, zone analytics, floor heatmaps, anomaly detection, and an auto-generated plain-English insight report. No GPU required.

<!-- TODO(epic-9 day 3): one-paragraph non-technical explanation + demo GIF -->

## Architecture

```
User uploads video
       ↓
React frontend → FastAPI → RQ job queue (Redis)
                               ↓
                    Background worker:
                    OpenCV reads frames (every 5th)
                    YOLOv8n detects people → faces blurred
                    DeepSORT tracks IDs
                    Zone analytics computed
                    Heatmap generated
                    Autoencoder scores anomalies
                    Results saved → Supabase
                    Video frames stored → Cloudflare R2
                               ↓
                    Groq LLM generates insight report
                               ↓
React dashboard polls → heatmap, zone stats, anomalies, report
```

## Repo layout

```
shoplens/
├── backend/
│   ├── app/            FastAPI app, routes, Supabase/R2 clients
│   ├── cv/             detector, tracker, zones, heatmap, anomaly, blur
│   ├── workers/        RQ pipeline job
│   ├── evaluation/     metrics for the results table
│   └── models/         trained autoencoder (.pth) exported from Colab
├── frontend/           React + Vite + TypeScript dashboard
├── notebooks/          Colab: detection eval, tracking, autoencoder training
├── supabase/schema.sql table definitions
└── docs/               prd, tech decisions, epics roadmap
```

## Run locally

Prereqs: Python 3.11+, Node 18+, Docker (for Redis).

```bash
# 1. Redis
docker run -d -p 6379:6379 redis:7

# 2. Backend API
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in real values
uvicorn app.main:app --reload

# 3. Pipeline worker (separate terminal, same venv)
cd backend
rq worker video --url redis://localhost:6379/0

# 4. Frontend
cd frontend
npm install
npm run dev
```

## Evaluation

Results on the Mall Dataset (2000 frames):

| metric | value |
|---|---|
| detection MAE | <!-- TODO(epic-9 day 1): from evaluation/metrics.py --> |
| detection RMSE | |
| unique track IDs (200 frames) | |
| anomaly precision / recall | |

Reproduce with `python -m evaluation.metrics <detection_results.csv>`.

## Deployment

- **Backend** → Railway (`railway.toml`). Deploy a second service from the same repo with start command `rq worker video --url $REDIS_URL` for background processing.
- **Frontend** → Vercel (project root set to `frontend/`).
- **Storage** → Cloudflare R2 bucket.
- **Database** → Supabase; run `supabase/schema.sql` once.

## Performance

<!-- TODO(epic-8 day 5): measure and document processing time per minute of video -->

## Screenshots

<!-- TODO(epic-9 day 3): dashboard, zone drawing UI, heatmap, anomaly timeline -->
