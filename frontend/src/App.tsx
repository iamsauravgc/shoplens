import { useRef, useState } from "react";
import { uploadVideo } from "./api/client";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

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
      <header>
        <h1>ShopLens</h1>
        <p>CCTV footage in. Retail intelligence out.</p>
      </header>

      {jobId ? (
        <Dashboard jobId={jobId} />
      ) : (
        <>
          {/* TODO(epic-8 day 4): add a settings view that mounts ZoneCanvas
              with a real store frame from R2 so zones can be drawn once */}
          <input ref={fileInput} type="file" accept="video/mp4,video/mov,video/avi" />
          <button onClick={handleUpload}>Upload &amp; analyze</button>
          {error && <div className="status status-error">{error}</div>}
        </>
      )}
    </main>
  );
}
