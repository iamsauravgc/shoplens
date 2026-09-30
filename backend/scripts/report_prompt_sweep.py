"""Epic 6 DoD: run the report prompt over 10 synthetic analytics inputs.

Offline by default (formats prompts only). Pass --live to actually call the
LLM for every case and print the generated reports.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.report import build_prompt, format_analytics_for_llm, generate_report

ZONE_NAMES = {
    "z-entrance": "Entrance strip",
    "z-aisle": "Center aisle",
    "z-checkout": "Stock room",
}


def zone(vid: int, visits: int, dwell: float, peak: int | None = 14) -> dict:
    stats = {"unique_visitors": vid, "total_visits": visits, "avg_dwell_seconds": dwell}
    if peak is not None:
        stats["peak_hour"] = peak
    return stats


def anomaly(kind: str, zone_id: str | None = "z-entrance", frame: int | None = 120) -> dict:
    return {"anomaly_type": kind, "zone_id": zone_id, "frame": frame}


CASES: list[tuple[str, dict]] = [
    ("no zones at all", {"unique_visitors": 0, "frames_processed": 720}),
    (
        "zero anomalies",
        {
            "unique_visitors": 40,
            "frames_processed": 720,
            "zone_summary": {"z-entrance": zone(40, 45, 3.1)},
            "zone_names": ZONE_NAMES,
        },
    ),
    (
        "single zone with zero visitors",
        {
            "unique_visitors": 0,
            "frames_processed": 720,
            "zone_summary": {
                "z-entrance": zone(0, 0, 0.0),
                "z-aisle": zone(0, 0, 0.0),
            },
            "zone_names": ZONE_NAMES,
            "anomalies": [],
        },
    ),
    (
        "crowd spike heavy",
        {
            "unique_visitors": 210,
            "frames_processed": 720,
            "zone_summary": {"z-entrance": zone(210, 240, 2.0)},
            "zone_names": ZONE_NAMES,
            "anomalies": [anomaly("crowd_spike", None, f) for f in range(10, 200, 20)],
        },
    ),
    (
        "loitering heavy",
        {
            "unique_visitors": 60,
            "frames_processed": 720,
            "zone_summary": {"z-aisle": zone(60, 70, 95.4)},
            "zone_names": ZONE_NAMES,
            "anomalies": [anomaly("loitering", "z-aisle", f) for f in range(30, 400, 40)],
        },
    ),
    (
        "zone avoidance",
        {
            "unique_visitors": 88,
            "frames_processed": 720,
            "zone_summary": {
                "z-entrance": zone(88, 95, 4.2),
                "z-checkout": zone(0, 0, 0.0),
            },
            "zone_names": ZONE_NAMES,
            "anomalies": [anomaly("zone_avoidance", "z-checkout", None)],
        },
    ),
    (
        "balanced normal day",
        {
            "unique_visitors": 95,
            "frames_processed": 720,
            "zone_summary": {
                "z-entrance": zone(95, 110, 4.0, 11),
                "z-aisle": zone(70, 82, 6.5, 15),
                "z-checkout": zone(30, 34, 2.2, 17),
            },
            "zone_names": ZONE_NAMES,
            "anomalies": [anomaly("autoencoder", "z-aisle", 412)],
        },
    ),
    (
        "very high dwell everywhere",
        {
            "unique_visitors": 25,
            "frames_processed": 720,
            "zone_summary": {
                "z-entrance": zone(25, 28, 140.0, 20),
                "z-aisle": zone(22, 30, 128.7, 20),
            },
            "zone_names": ZONE_NAMES,
            "anomalies": [anomaly("loitering", "z-entrance", 500)],
        },
    ),
    (
        "six zones mixed",
        {
            "unique_visitors": 150,
            "frames_processed": 720,
            "zone_summary": {
                f"z-{i}": zone(10 + i * 7, 12 + i * 8, 1.5 + i, i + 8) for i in range(6)
            },
            "zone_names": {f"z-{i}": f"Zone {chr(65 + i)}" for i in range(6)},
            "anomalies": [anomaly("crowd_spike", "z-3", 99)],
        },
    ),
    (
        "missing peak_hour + unknown zone in anomaly",
        {
            "unique_visitors": 12,
            "frames_processed": 180,
            "zone_summary": {"z-entrance": {"unique_visitors": 12, "total_visits": 14, "avg_dwell_seconds": 2.0}},
            "zone_names": ZONE_NAMES,
            "anomalies": [{"anomaly_type": "autoencoder", "zone_id": "z-gone", "frame": 7}],
        },
    ),
]


def call_with_backoff(analytics: dict, attempts: int = 4) -> str:
    """Free tiers rate-limit (429); back off instead of failing the sweep."""
    import time

    import httpx as _httpx

    for attempt in range(attempts):
        try:
            return asyncio.run(generate_report(analytics))
        except _httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429 or attempt == attempts - 1:
                raise
            wait = 20 * (attempt + 1)
            print(f"     429 rate-limited — waiting {wait}s then retrying...")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="call the LLM for every case")
    parser.add_argument("--start", type=int, default=1, help="first case to run (1-based)")
    args = parser.parse_args()

    for i, (label, analytics) in enumerate(CASES, 1):
        if i < args.start:
            continue
        formatted = format_analytics_for_llm(analytics)
        prompt = build_prompt(formatted)
        print(f"[{i:02d}] {label}: prompt ok ({len(prompt)} chars), notes={formatted['notes']}")
        if args.live:
            content = call_with_backoff(analytics)
            print("     ---- report ----")
            print("     " + content.replace("\n", "\n     "))
            print("     ----------------")
    print(f"\n{len(CASES) - args.start + 1} cases run" + (" (live)" if args.live else " (offline)"))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    raise SystemExit(main())
