export type AnomalyType = "loitering" | "crowd_spike" | "zone_avoidance" | "autoencoder";

export interface ZoneDef {
  id?: string;
  zone_id?: string;
  name: string;
  polygon: { x: number; y: number }[];
}

export interface ZoneSummary {
  unique_visitors: number;
  total_visits: number;
  avg_dwell_seconds: number;
  peak_hour?: number;
}

export interface AnomalyEvent {
  anomaly_type: AnomalyType;
  zone_id?: string;
  frame?: number;
  score?: number;
  details?: Record<string, unknown>;
}

export interface AnalyticsResponse {
  video_id: string;
  frames_processed?: number;
  unique_visitors?: number;
  zone_names?: Record<string, string>;
  payload?: {
    unique_visitors?: number;
    frames_processed?: number;
    zone_summary?: Record<string, ZoneSummary>;
    zone_names?: Record<string, string>;
    heatmap_keys?: string[];
  };
  anomalies?: AnomalyEvent[];
}

export interface JobProgress {
  job_id: string;
  step: number;
  total_steps: number;
  message: string;
  state: "queued" | "processing" | "complete" | "failed";
}

export interface ReportData {
  video_id: string;
  content: string;
  model?: string;
  created_at?: string;
}

export interface UploadResponse {
  job_id: string;
  status: string;
}

export interface JobSummary {
  job_id: string;
  state: "queued" | "processing" | "complete" | "failed";
  updated_at: string;
  filename?: string;
  anomaly_count?: number;
  has_analytics?: number;
  has_report?: number;
}
