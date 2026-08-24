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

  useEffect(() => {
    if (!ready) return;
    // TODO(epic-8 day 4): surface fetch errors in the UI instead of failing silently
    getAnalytics(jobId)
      .then((data) => {
        setAnalytics(data);
        setAnomalies(data.anomalies ?? []);
      })
      .catch(() => undefined);
  }, [jobId, ready]);

  const onComplete = useCallback(() => setReady(true), []);

  if (!ready) {
    return <ProgressBar jobId={jobId} onComplete={onComplete} />;
  }

  const zoneSummary = analytics?.payload?.zone_summary ?? {};
  const chartData = Object.entries(zoneSummary).map(([zone, stats]) => ({
    zone,
    visitors: stats.unique_visitors,
  }));

  return (
    <div className="dashboard">
      {/* TODO(epic-9 day 3): polish layout — this should not look like a student project */}
      <Heatmap jobId={jobId} />

      <section>
        <h2>Zone traffic</h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="zone" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="visitors" fill="#38bdf8" />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section>
        <h2>Anomaly timeline</h2>
        {anomalies.length === 0 ? (
          <p>No anomalies detected.</p>
        ) : (
          <ul className="anomaly-list">
            {anomalies.map((a, i) => (
              <li key={i}>
                <strong>{a.anomaly_type}</strong> {a.zone_id ? `in ${a.zone_id}` : ""}
                {a.frame != null ? ` @ frame ${a.frame}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>

      <Report jobId={jobId} />
    </div>
  );
}
