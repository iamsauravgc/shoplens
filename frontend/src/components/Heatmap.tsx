import { useCallback, useEffect, useState } from "react";
import { heatmapUrl } from "../api/client";

const TIME_RANGES = ["full", "morning", "afternoon", "evening"] as const;
type TimeRange = (typeof TIME_RANGES)[number];

function rangeFromUrl(): TimeRange {
  const requested = new URLSearchParams(window.location.search).get("range");
  return TIME_RANGES.find((r) => r === requested) ?? "full";
}

export default function Heatmap({ jobId }: { jobId: string }) {
  const [range, setRange] = useState<TimeRange>(rangeFromUrl);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setFailed(false);
    setLoading(true);
  }, [range, jobId]);

  const handleError = useCallback(() => {
    setFailed(true);
    setLoading(false);
  }, []);
  const src = heatmapUrl(jobId, range);

  return (
    <section>
      <h2>Floor heatmap</h2>
      <div className="heatmap-controls">
        {TIME_RANGES.map((r) => (
          <button
            key={r}
            className={r === range ? "active" : "secondary"}
            onClick={() => setRange(r)}
          >
            {r}
          </button>
        ))}
      </div>
      {failed ? (
        <p className="hint">Heatmap not available for this segment.</p>
      ) : (
        <>
          {loading && <p className="hint">Loading heatmap…</p>}
          <img
            src={src}
            alt={`Heatmap (${range})`}
            onLoad={() => setLoading(false)}
            onError={handleError}
            style={{ display: loading ? "none" : "block" }}
          />
        </>
      )}
    </section>
  );
}
