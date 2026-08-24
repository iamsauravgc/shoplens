import json
import logging
import os

import httpx

from app.db import fetch_analytics, insert_report

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

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
- Keep it under 400 words.
"""


def format_analytics_for_llm(analytics: dict) -> dict:
    zones = analytics.get("zone_summary") or {}
    anomalies = analytics.get("anomalies") or []
    formatted = {
        "totals": {
            "unique_visitors": analytics.get("unique_visitors", 0),
            "frames_processed": analytics.get("frames_processed", 0),
        },
        "zones": [
            {"zone_id": zone_id, **stats} for zone_id, stats in sorted(zones.items())
        ],
        "anomalies": [
            {
                "type": a.get("anomaly_type"),
                "zone_id": a.get("zone_id"),
                "frame": a.get("frame"),
            }
            for a in anomalies[:50]
        ],
        "notes": [],
    }
    # edge cases from Epic 7 Day 5: zero-visitor zones and zero anomalies must not break generation
    if not formatted["zones"]:
        formatted["notes"].append("No zones defined or no visitors recorded.")
    else:
        empty_zones = [z["zone_id"] for z in formatted["zones"] if z.get("unique_visitors", 0) == 0]
        if empty_zones:
            formatted["notes"].append(f"Zones with zero visitors: {', '.join(empty_zones)}")
    if not formatted["anomalies"]:
        formatted["notes"].append("No anomalies detected in this period.")
    return formatted


def build_prompt(formatted: dict) -> str:
    return REPORT_PROMPT_TEMPLATE.format(analytics_json=json.dumps(formatted, indent=2))


async def generate_report(analytics: dict) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.4,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(format_analytics_for_llm(analytics))},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


async def generate_and_store_report(video_id: str) -> dict | None:
    analytics_row = fetch_analytics(video_id)
    if analytics_row is None:
        return None
    content = await generate_report(analytics_row.get("payload") or {})
    return insert_report({"video_id": video_id, "content": content, "model": GROQ_MODEL})
