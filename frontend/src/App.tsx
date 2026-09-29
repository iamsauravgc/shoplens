import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { listJobs, uploadVideo } from "./api/client";
import Dashboard from "./components/Dashboard";
import ZoneCanvas from "./components/ZoneCanvas";
import type { JobSummary } from "./types";

type View = "analyze" | "zones";

export default function App() {
  const [view, setView] = useState<View>("analyze");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const refreshJobs = () => {
    listJobs(8)
      .then(setJobs)
      .catch(() => setJobs([]));
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedJob = params.get("job");
    const linkedView = params.get("view");
    if (linkedView === "zones" || linkedView === "analyze") setView(linkedView);
    if (linkedJob) setJobId(linkedJob);
    refreshJobs();
  }, []);

  const pickFile = () => {
    setView("analyze");
    setJobId(null);
    fileInput.current?.click();
  };

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const res = await uploadVideo(file);
      setJobId(res.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const openJob = (id: string) => {
    setJobId(id);
    setView("analyze");
  };

  const backToList = () => {
    setJobId(null);
    refreshJobs();
  };

  return (
    <div className="app-shell">
      <input
        ref={fileInput}
        type="file"
        accept="video/mp4,video/mov,video/avi"
        onChange={handleFile}
      />

      <header className="nav">
        <div className="nav-brand">
          <span className="wordmark">ShopLens</span>
          <nav className="nav-tabs" aria-label="Views">
            <button
              className={view === "analyze" ? "tab is-active" : "tab"}
              onClick={() => setView("analyze")}
              aria-current={view === "analyze" ? "page" : undefined}
            >
              Analyze
            </button>
            <button
              className={view === "zones" ? "tab is-active" : "tab"}
              onClick={() => setView("zones")}
              aria-current={view === "zones" ? "page" : undefined}
            >
              Zones
            </button>
          </nav>
        </div>
        <button className="link-action" onClick={pickFile}>
          Upload
        </button>
      </header>

      <main key={`${view}-${jobId ?? ""}`} className="view">
        {view === "zones" ? (
          <ZoneCanvas />
        ) : jobId ? (
          <>
            <Dashboard jobId={jobId} />
            <button className="secondary" onClick={backToList}>
              Analyze another video
            </button>
          </>
        ) : (
          <>
            <section className="hero">
              <p className="hero-meta">Max 120 s · sample every 5th frame</p>
              <h1 className="hero-title">Upload a clip. Get the report.</h1>
              <p className="hero-figure">{jobs.length}</p>
              <p className="hero-qualifier">analyses on file</p>
              <p className="hero-body">
                Up to two minutes of footage, sampled every 5th frame — 720 frames, one plain-English
                report on what happened in the store.
              </p>
              <div className="hero-actions">
                <button
                  className={uploading ? "btn--primary is-loading" : "btn--primary"}
                  onClick={pickFile}
                  disabled={uploading}
                >
                  {uploading ? "Uploading…" : "Upload a 2-minute clip"}
                </button>
                <span className="hero-meta">MP4 · MOV · AVI</span>
              </div>
              {error && <div className="status status-error">{error}</div>}
            </section>

            {jobs.length > 0 && (
              <section>
                <h2>Recent analyses</h2>
                <ul className="job-list">
                  {jobs.map((job) => (
                    <li key={job.job_id}>
                      <button className="job-row" onClick={() => openJob(job.job_id)}>
                        <span className="job-name">{job.filename ?? job.job_id.slice(0, 8)}</span>
                        <span className="job-meta mono">
                          {job.anomaly_count ?? 0} anomalies ·{" "}
                          {new Date(job.updated_at).toLocaleDateString(undefined, {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })}
                          {job.state !== "complete" ? ` · ${job.state}` : ""}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </main>

      <footer className="footer-statement">
        <p className="footer-line">CCTV footage in. Retail intelligence out.</p>
        <div className="footer-meta">
          <span className="wordmark">ShopLens</span>
          <span>Local SQLite · CPU-only YOLOv8 + DeepSORT</span>
        </div>
      </footer>
    </div>
  );
}
