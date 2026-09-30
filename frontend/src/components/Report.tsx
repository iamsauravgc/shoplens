import { useCallback, useEffect, useState } from "react";
import { marked } from "marked";
import { generateReport, getReport } from "../api/client";
import type { ReportData } from "../types";

function downloadHtml(report: ReportData, jobId: string) {
  const body = marked.parse(report.content, { async: false }) as string;
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ShopLens insight report — ${jobId.slice(0, 8)}</title>
<style>
  :root { --cobalt: #1b4bf1; }
  body { font-family: Georgia, "Times New Roman", serif; max-width: 46rem; margin: 3rem auto; padding: 0 1.5rem; color: #14161a; line-height: 1.6; }
  header { border-bottom: 3px solid var(--cobalt); padding-bottom: .75rem; margin-bottom: 1.5rem; }
  .wordmark { font-family: Arial, Helvetica, sans-serif; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--cobalt); font-size: .85rem; }
  h1 { font-size: 1.4rem; margin: .35rem 0 0; }
  .meta { font-family: Arial, Helvetica, sans-serif; font-size: .8rem; color: #5a616b; margin-top: .4rem; }
  h2, h3 { font-family: Arial, Helvetica, sans-serif; font-size: 1.05rem; margin-top: 1.75rem; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }
  th, td { border: 1px solid #d8dce3; padding: .4rem .6rem; text-align: left; }
  th { background: #eef1f7; font-family: Arial, Helvetica, sans-serif; }
  blockquote { border-left: 3px solid var(--cobalt); margin-left: 0; padding-left: 1rem; color: #3d434d; }
  strong { color: #0d0f13; }
  footer { margin-top: 2.5rem; border-top: 1px solid #d8dce3; padding-top: .75rem; font-family: Arial, Helvetica, sans-serif; font-size: .75rem; color: #5a616b; }
</style>
</head>
<body>
<header>
  <span class="wordmark">ShopLens</span>
  <h1>Store insight report</h1>
  <p class="meta">Job ${jobId.slice(0, 8)} · generated ${new Date(report.created_at ?? Date.now()).toLocaleString()} · model ${report.model ?? "—"}</p>
</header>
<main>${body}</main>
<footer>CCTV footage in. Retail intelligence out. — ShopLens</footer>
</body>
</html>`;
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `shoplens_report_${jobId.slice(0, 8)}.html`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function Report({ jobId }: { jobId: string }) {
  const [report, setReport] = useState<ReportData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getReport(jobId)
      .then((value) => {
        setReport(value);
        setError(null);
      })
      .catch(() => setReport(null));
  }, [jobId]);

  useEffect(refresh, [refresh]);

  const handleGenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      setReport(await generateReport(jobId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h2>Insight report</h2>
      {error && <div className="status status-error">Could not generate report: {error}</div>}
      <button
        className={busy ? "btn--primary is-loading" : "btn--primary"}
        onClick={handleGenerate}
        disabled={busy}
      >
        {busy ? "Generating…" : report ? "Regenerate report" : "Generate report"}
      </button>
      <button onClick={() => report && downloadHtml(report, jobId)} disabled={!report}>
        Download
      </button>
      {report ? (
        <div
          className="report-body"
          dangerouslySetInnerHTML={{ __html: marked.parse(report.content, { async: false }) as string }}
        />
      ) : (
        <p className="hint">No report yet.</p>
      )}
    </section>
  );
}
