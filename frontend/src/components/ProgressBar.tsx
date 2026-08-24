import { useEffect, useState } from "react";
import { pollStatus } from "../api/client";
import type { JobProgress } from "../types";

interface Props {
  jobId: string;
  onComplete: () => void;
}

export default function ProgressBar({ jobId, onComplete }: Props) {
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    pollStatus(jobId, (p) => {
      if (!cancelled) setProgress(p);
    })
      .then((final) => {
        if (!cancelled && final.state === "complete") onComplete();
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, onComplete]);

  if (error) {
    return <div className="status status-error">Processing failed: {error}</div>;
  }

  const pct = progress ? Math.round((progress.step / progress.total_steps) * 100) : 0;

  return (
    <div className="progress">
      <div className="progress-label">
        {progress?.message || "Waiting for worker..."} ({pct}%)
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
