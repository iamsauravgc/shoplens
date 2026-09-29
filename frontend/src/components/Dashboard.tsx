import { useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAnalytics } from "../api/client";
import type { AnalyticsResponse, AnomalyEvent } from "../types";
import Heatmap from "./Heatmap";
import ProgressBar from "./ProgressBar";
import Report from "./Report";

export default function Dashboard({ jobId }: { jobId: string }) {
  const [ready, setReady] = useState(false);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    getAnalytics(jobId)
      .then((data) => {
        setAnalytics(data);
        setAnomalies(data.anomalies ?? []);
        setFetchError(null);
      })
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : String(err)));
  }, [jobId, ready]);

  const onComplete = useCallback(() => setReady(true), []);

  if (!ready) {
    return <ProgressBar jobId={jobId} onComplete={onComplete} />;
  }

  const payload = analytics?.payload ?? {};
  const zoneNames = payload.zone_names ?? analytics?.zone_names ?? {};
  const zoneSummary = payload.zone_summary ?? {};
  const chartData = Object.entries(zoneSummary).map(([zoneId, stats]) => ({
    zone: zoneNames[zoneId] ?? zoneId.slice(0, 8),
    visitors: stats.unique_visitors,
  }));
  const nameOf = (zoneId?: string) => (zoneId ? (zoneNames[zoneId] ?? zoneId.slice(0, 8)) : "");

  return (
    <div className="dashboard">
      {fetchError && <div className="status status-error">Could not load analytics: {fetchError}</div>}

      <section className="stats-row">
        <div className="stat">
          <span className="stat-value">{payload.frames_processed ?? analytics?.frames_processed ?? "—"}</span>
          <span className="stat-label">frames processed</span>
        </div>
        <div className="stat">
          <span className="stat-value">{payload.unique_visitors ?? analytics?.unique_visitors ?? "—"}</span>
          <span className="stat-label">unique visitors</span>
        </div>
        <div className="stat">
          <span className="stat-value">{Object.keys(zoneSummary).length}</span>
          <span className="stat-label">zones</span>
        </div>
        <div className="stat">
          <span className="stat-value">{anomalies.length}</span>
          <span className="stat-label">anomalies</span>
        </div>
      </section>

      <Heatmap jobId={jobId} />

      <section>
        <h2>Zone traffic</h2>
        {chartData.length === 0 ? (
          <p className="hint">No zone data — draw zones in the Zones tab, then re-run the video.</p>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="zone" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="visitors" fill="#38bdf8" name="Unique visitors" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
            <table className="zone-table">
              <thead>
                <tr>
                  <th>Zone</th>
                  <th>Visitors</th>
                  <th>Visits</th>
                  <th>Avg dwell</th>
                  <th>Peak hour</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(zoneSummary).map(([zoneId, stats]) => (
                  <tr key={zoneId}>
                    <td>{nameOf(zoneId)}</td>
                    <td>{stats.unique_visitors}</td>
                    <td>{stats.total_visits}</td>
                    <td>{stats.avg_dwell_seconds}s</td>
                    <td>{stats.peak_hour != null ? `${String(stats.peak_hour).padStart(2, "0")}:00` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>

      <section>
        <h2>Anomaly timeline</h2>
        {anomalies.length === 0 ? (
          <p>No anomalies detected.</p>
        ) : (
          <ul className="anomaly-list">
            {anomalies.map((a, i) => (
              <li key={i}>
                <strong>{a.anomaly_type.replace("_", " ")}</strong>
                {a.zone_id ? ` in ${nameOf(a.zone_id)}` : ""}
                {a.frame != null ? ` @ frame ${a.frame}` : ""}
                {typeof a.score === "number" ? ` (score ${a.score.toFixed(3)})` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>

      <Report jobId={jobId} />
    </div>
  );
}
