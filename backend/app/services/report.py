import json
import logging

import httpx

from app.config import get_settings
from app.db import fetch_analytics, fetch_anomalies, insert_report

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a retail analytics analyst. You write weekly insight reports for the owner of a "
    "small shop, based on CCTV-derived analytics: per-zone visitor counts, dwell times, and "
    "flagged anomalies (loitering, crowd spikes, zone avoidance)."
)

REPORT_PROMPT_TEMPLATE = """Write a concise insight report for the shop owner based on this data.

Data:
{analytics_json}

Rules:
- Reference concrete numbers from the data in every point.
- Lead with the single most actionable finding.
- Group findings as: Traffic, Dwell time, Anomalies, Recommended actions.
- No generic filler like "Zone A had more visitors than Zone B" without numbers.
- If the notes field says something is empty, say plainly that there was no activity and suggest one plausible reason to check.
- Never mention the notes field itself, JSON structure, or data-format details in the report — it is for your context only.
- Keep it under 400 words.
"""


def format_analytics_for_llm(analytics: dict) -> dict:
    zones = analytics.get("zone_summary") or {}
    zone_names = analytics.get("zone_names") or {}
    anomalies = analytics.get("anomalies") or []
    name_of = lambda zid: zone_names.get(zid, zid[:8] if zid else "—")
    counts: dict[str, int] = {}
    for a in anomalies:
        t = a.get("anomaly_type") or "unknown"
        counts[t] = counts.get(t, 0) + 1
    formatted = {
        "totals": {
            "unique_visitors": analytics.get("unique_visitors", 0),
            "frames_processed": analytics.get("frames_processed", 0),
            "anomaly_count": len(anomalies),
        },
        "zones": [
            {"name": name_of(zone_id), "zone_id": zone_id, **stats}
            for zone_id, stats in sorted(zones.items())
        ],
        "anomaly_counts_by_type": counts,
        "anomalies": [
            {
                "type": a.get("anomaly_type"),
                "zone": name_of(a.get("zone_id")),
                "frame": a.get("frame"),
            }
            for a in anomalies[:20]
        ],
        "notes": [],
    }
    # edge cases from Epic 7 Day 5: zero-visitor zones and zero anomalies must not break generation
    if not formatted["zones"]:
        formatted["notes"].append("No zones defined or no visitors recorded.")
    else:
        empty_zones = [z["name"] for z in formatted["zones"] if z.get("unique_visitors", 0) == 0]
        if empty_zones:
            formatted["notes"].append(f"Zones with zero visitors: {', '.join(empty_zones)}")
    if not anomalies:
        formatted["notes"].append("No anomalies detected in this period.")
    return formatted


def build_prompt(formatted: dict) -> str:
    return REPORT_PROMPT_TEMPLATE.format(analytics_json=json.dumps(formatted, indent=2))


async def generate_report(analytics: dict) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    payload = {
        "model": settings.llm_model,
        "temperature": 0.4,
        # gpt-oss is a reasoning model: it spends tokens thinking before answering,
        # so 1024 would truncate a 400-word report
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(format_analytics_for_llm(analytics))},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(settings.llm_api_url, json=payload, headers=headers)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


async def generate_and_store_report(video_id: str) -> dict | None:
    analytics_row = fetch_analytics(video_id)
    if analytics_row is None:
        return None
    payload = dict(analytics_row.get("payload") or {})
    # the stored analytics payload never carried anomalies — pull them so the LLM sees them
    payload["anomalies"] = fetch_anomalies(video_id)
    content = await generate_report(payload)
    return insert_report({"video_id": video_id, "content": content, "model": get_settings().llm_model})
