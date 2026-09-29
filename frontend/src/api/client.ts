import type { AnalyticsResponse, JobProgress, JobSummary, ReportData, UploadResponse, ZoneDef } from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request("/upload", { method: "POST", body: form });
}

export async function pollStatus(
  jobId: string,
  onTick: (progress: JobProgress) => void,
  intervalMs = 3000,
): Promise<JobProgress> {
  for (;;) {
    const progress = await request<JobProgress>(`/status/${jobId}`);
    onTick(progress);
    if (progress.state === "complete" || progress.state === "failed") {
      return progress;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export async function getAnalytics(jobId: string): Promise<AnalyticsResponse> {
  return request(`/analytics/${jobId}`);
}

export function heatmapUrl(jobId: string, timeRange: string): string {
  return `${BASE}/heatmap/${jobId}?time_range=${encodeURIComponent(timeRange)}`;
}

export async function getReport(jobId: string): Promise<ReportData | null> {
  try {
    return await request<ReportData>(`/report/${jobId}`);
  } catch (err) {
    if (err instanceof Error && err.message.startsWith("404")) return null;
    throw err;
  }
}

export function generateReport(jobId: string): Promise<ReportData> {
  return request("/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_id: jobId }),
  });
}

export function listZones(): Promise<ZoneDef[]> {
  return request("/zones");
}

export async function listJobs(limit = 10): Promise<JobSummary[]> {
  const res = await request<{ jobs: JobSummary[] }>(`/jobs?limit=${limit}`);
  return res.jobs;
}

export function saveZone(zone: { name: string; polygon: { x: number; y: number }[] }): Promise<ZoneDef> {
  return request("/zones", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(zone),
  });
}

export async function deleteZone(zoneId: string): Promise<void> {
  const res = await fetch(`${BASE}/zones/${zoneId}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
}

export function zoneFrameUrl(): string {
  return `${BASE}/zones/frame`;
}
