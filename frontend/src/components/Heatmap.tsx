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
    <section id="floor-heatmap">
      <h2>Floor heatmap</h2>
      <div className="heatmap-controls">
        {TIME_RANGES.map((r) => (
          <button
            key={r}
            className={r === range ? "active" : "secondary"}
            aria-pressed={r === range}
            onClick={() => setRange(r)}
          >
            {r.charAt(0).toUpperCase() + r.slice(1)}
          </button>
        ))}
      </div>
      {failed ? (
        <p className="hint">Heatmap not available for this segment.</p>
      ) : (
        <figure className="figure-dark">
          <div className="figure-bar">
            <span>Floor heatmap</span>
            <span className="mono">{range}</span>
          </div>
          {loading && <p className="figure-loading">Rendering heatmap…</p>}
          <img
            src={src}
            alt={`Crowd density over the store floor, ${range} segment`}
            onLoad={() => setLoading(false)}
            onError={handleError}
            style={{ display: loading ? "none" : "block" }}
          />
          <figcaption>
            <span className="caption-tag">Sampled every 5th frame</span>
            Crowd density over the store floor, {range} segment.
          </figcaption>
        </figure>
      )}
    </section>
  );
}
