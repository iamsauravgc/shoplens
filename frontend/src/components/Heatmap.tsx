import { useCallback, useEffect, useState } from "react";
import { heatmapUrl } from "../api/client";

const TIME_RANGES = ["full", "morning", "afternoon", "evening"] as const;
type TimeRange = (typeof TIME_RANGES)[number];

export default function Heatmap({ jobId }: { jobId: string }) {
  const [range, setRange] = useState<TimeRange>("full");
  const [failed, setFailed] = useState(false);

  // TODO(epic-4 day 5): show a loading state while the PNG regenerates after range change
  useEffect(() => setFailed(false), [range, jobId]);

  const handleError = useCallback(() => setFailed(true), []);
  const src = heatmapUrl(jobId, range);

  return (
    <section>
      <h2>Floor heatmap</h2>
      <div className="heatmap-controls">
        {TIME_RANGES.map((r) => (
          <button key={r} onClick={() => setRange(r)} disabled={r === range}>
            {r}
          </button>
        ))}
      </div>
      {failed ? (
        <p>Heatmap not available yet.</p>
      ) : (
        <img src={src} alt={`Heatmap (${range})`} onError={handleError} />
      )}
    </section>
  );
}
