import { useEffect, useRef, useState } from "react";
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

  const handleUpload = async () => {
    const file = fileInput.current?.files?.[0];
    if (!file) return;
    setError(null);
    try {
      const res = await uploadVideo(file);
      setJobId(res.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <main>
      <header className="app-header">
        <div>
          <h1>ShopLens</h1>
          <p>CCTV footage in. Retail intelligence out.</p>
        </div>
        <nav>
          <button className={view === "analyze" ? "active" : "secondary"} onClick={() => setView("analyze")}>
            Analyze
          </button>
          <button className={view === "zones" ? "active" : "secondary"} onClick={() => setView("zones")}>
            Zones
          </button>
        </nav>
      </header>

      {view === "zones" ? (
        <ZoneCanvas />
      ) : jobId ? (
        <>
          <Dashboard jobId={jobId} />
          <button
            className="secondary"
            onClick={() => {
              setJobId(null);
              refreshJobs();
            }}
          >
            Analyze another video
          </button>
        </>
      ) : (
        <>
          <input ref={fileInput} type="file" accept="video/mp4,video/mov,video/avi" />
          <button onClick={handleUpload}>Upload &amp; analyze</button>
          {error && <div className="status status-error">{error}</div>}

          {jobs.length > 0 && (
            <section className="status">
              <p className="hint">Or reopen a finished analysis</p>
              <ul className="zone-list">
                {jobs.map((job) => (
                  <li key={job.job_id}>
                    <button className="secondary" onClick={() => setJobId(job.job_id)}>
                      {job.filename ?? job.job_id.slice(0, 8)} — {job.anomaly_count ?? 0} anomalies —{" "}
                      {new Date(job.updated_at).toLocaleString()}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
