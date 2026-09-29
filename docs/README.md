# ShopLens docs

Read these in order if you're new to the project.

| file | what's in it |
|---|---|
| [`prd.md`](prd.md) | Product requirements — the problem, who it's for, success metrics, resolved questions |
| [`tech.md`](tech.md) | Every stack choice with the one-line reason you give a mentor |
| [`epics.md`](epics.md) | The 10-week roadmap: daily tasks as checkboxes plus a Definition of Done per epic |
| [`shoplens_guide.md`](shoplens_guide.md) | Epic 1–2 walkthrough — detection, threshold tuning, tracking, ID-switch tuning |
| [`code_walkthrough.md`](code_walkthrough.md) | Annotated explanation of the code, written for a reviewer reading the repo cold |
| [`../CLAUDE.md`](../CLAUDE.md) | Working instructions for the AI assistant on this repo (lives at the root) |

## evidence/

Raw output from Epics 1–2, kept so the numbers above are reproducible without re-running
Colab:

| file | what it is |
|---|---|
| `detection_results.csv` | per-frame `frame_id, gt_count, detected_count, error, conf` for all 2000 Mall frames |
| `threshold_vs_error.png` | confidence threshold vs reconstruction/MAE error |
| `gt_distribution.png`, `gt_visualization.png` | ground-truth counts and where people are in the frame |
| `detection_frame1.png`, `detection_final_results.png` | detector output samples |
| `failure_cases.png` | the frames the detector was most wrong on |
| `tracking_annotated.mp4` | DeepSORT output with ID labels (12 MB, git-ignored) |
| `tracking_sample_frames.png`, `trajectories.png` | track visualizations |
| `trajectories.json` | `(x, y, frame)` per track ID |
