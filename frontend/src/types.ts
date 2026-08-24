export type AnomalyType = "loitering" | "crowd_spike" | "zone_avoidance";

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
  payload?: {
    unique_visitors?: number;
    zone_summary?: Record<string, ZoneSummary>;
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
