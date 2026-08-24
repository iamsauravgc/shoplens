import { useCallback, useEffect, useState } from "react";
import { generateReport, getReport } from "../api/client";
import type { ReportData } from "../types";

export default function Report({ jobId }: { jobId: string }) {
  const [report, setReport] = useState<ReportData | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(() => {
    getReport(jobId)
      .then(setReport)
      .catch(() => setReport(null));
  }, [jobId]);

  useEffect(refresh, [refresh]);

  const handleGenerate = async () => {
    setBusy(true);
    try {
      setReport(await generateReport(jobId));
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = () => {
    if (!report) return;
    // TODO(epic-7 day 4): render as styled HTML for a proper downloadable document
    const blob = new Blob([report.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `shoplens_report_${jobId.slice(0, 8)}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section>
      <h2>Insight report</h2>
      <button onClick={handleGenerate} disabled={busy}>
        {busy ? "Generating..." : report ? "Regenerate report" : "Generate report"}
      </button>
      <button onClick={handleDownload} disabled={!report}>
        Download
      </button>
      <pre>{report?.content ?? "No report yet."}</pre>
    </section>
  );
}
