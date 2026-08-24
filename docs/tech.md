# ShopLens — Tech Stack

Every choice below has a reason. Learn the one-line reason — that's what you say to your mentor.

---

## Computer Vision Pipeline

| Tool | Why |
|---|---|
| **YOLOv8n** | Fastest YOLO variant that runs on CPU. Best speed-accuracy tradeoff for inference without GPU. `ultralytics` package, one-line install. |
| **DeepSORT** | Industry standard for multi-object tracking. Assigns consistent IDs across frames. `deep_sort_realtime` package. |
| **OSNet** (re-ID) | Lightweight re-identification model. Recognizes the same person re-entering a zone without facial recognition. PyTorch-based. |
| **OpenCV** | Standard frame-level video processing. YOLOv8 and DeepSORT both expect OpenCV format — no alternative. |
| **PyTorch** | All CV models (DeepSORT, OSNet, Autoencoder) use PyTorch. Mixing frameworks causes compatibility issues. |

---

## Anomaly Detection

| Tool | Why |
|---|---|
| **Autoencoder (PyTorch)** | Trained on normal movement patterns. High reconstruction error = anomaly. No labeled anomaly data needed — unsupervised. This is the actual ML you built, not just inference on a pretrained model. |
| **DBSCAN (scikit-learn)** | Clusters movement trajectories without needing to specify number of clusters upfront. Better than KMeans for spatial data with noise. |

---

## Backend

| Tool | Why |
|---|---|
| **FastAPI** | Video processing is I/O heavy and slow. FastAPI's async support handles concurrent requests without blocking. Flask has no built-in async. Django is overkill — you don't need ORM, admin panel, or session management. |
| **Redis + RQ** | Video processing takes minutes. RQ queues the job, Redis stores status. User gets a job ID immediately, polls for completion — doesn't sit on a loading screen. |
| **PostgreSQL** | Stores zone definitions, analytics results, processed video metadata. Relational because zones → analytics → reports are related entities. |

---

## LLM Insight Generation

| Tool | Why |
|---|---|
| **Groq API (free tier)** | Fastest LLM inference available for free. Llama-3.3-70B via Groq generates insight reports from structured analytics JSON. No GPU needed. Alternative: Ollama locally but slower. |

---

## Frontend

| Tool | Why |
|---|---|
| **React** | Zone annotation requires drawing on a canvas over a video frame — Streamlit can't do this. React gives full control over interactive canvas, chart rendering, and real-time job polling. You already know React. |
| **Recharts** | Lightweight charting library for React. Covers all needed chart types (bar, line, heatmap). No heavy dependencies. |
| **Fabric.js** | Canvas library for zone drawing. Lets user draw rectangles/polygons on the store frame to define zones interactively. |

---

## Deployment

| Tool | Why |
|---|---|
| **Railway** | Backend deployment. Stays awake on free tier (Render sleeps after 15 min — kills demos). Supports background workers via RQ. Good logs. |
| **Vercel** | Frontend deployment. Instant React deploys, free tier, CDN. You already use this. |
| **Cloudflare R2** | Stores uploaded videos and processed output frames. S3-compatible API, free egress (unlike AWS S3 which charges for downloads). |
| **Supabase** | Managed PostgreSQL. Free tier, no DevOps overhead, built-in dashboard to inspect data during development. |

---

## Development

| Tool | Why |
|---|---|
| **Google Colab** | CV pipeline development. Free GPU/CPU, pre-installed libraries, easy to share notebooks with mentor. |
| **MLflow** | Tracks autoencoder training experiments — loss curves, hyperparameters, model versions. Proves you did real ML experimentation. |
| **Mall Dataset** | Ground truth labels (62,325 annotated pedestrians) let you compute real evaluation metrics — MAE, MSE — proving your detection works. |

---

## Architecture Overview

```
User uploads video
       ↓
React frontend → FastAPI → RQ job queue (Redis)
                               ↓
                    Background worker:
                    OpenCV reads frames
                    YOLOv8 detects people
                    DeepSORT tracks IDs
                    Zone analytics computed
                    Autoencoder scores anomalies
                    Results saved → Supabase
                    Video frames saved → R2
                               ↓
                    Groq LLM generates insight report
                               ↓
React dashboard polls → displays heatmap, zone stats, anomalies, report
```
