"""Deterministic historical safety-event loading and aggregation."""
from __future__ import annotations

import csv
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger(__name__)
TIME_WINDOWS = ("08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00")


def parse_timestamp(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    text = str(value).strip().replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def time_window_for_hour(hour: int) -> str:
    for start in range(8, 18, 2):
        if start <= hour < start + 2:
            return f"{start:02d}:00-{start + 2:02d}:00"
    return "Outside configured windows"


def normalize_event(raw: dict) -> dict:
    timestamp = parse_timestamp(raw["timestamp"])
    missing = raw.get("missing_ppe", [])
    if isinstance(missing, str):
        missing = [part.strip() for part in missing.split("|") if part.strip()]
    fall = str(raw.get("fall_detected", False)).lower() in ("1", "true", "yes")
    zone_violation = str(raw.get("zone_violation", False)).lower() in ("1", "true", "yes")
    violation = raw.get("violation_type")
    if not violation:
        if fall:
            violation = "Fall"
        elif zone_violation:
            violation = "Zone Violation"
        elif missing:
            violation = "PPE Non-Compliance"
        else:
            violation = "Other"
    return {
        "timestamp": timestamp,
        "zone": (raw.get("zone") or "Unspecified Zone").strip(),
        "task": (raw.get("task") or "unknown").strip(),
        "violation_type": violation,
        "severity": str(raw.get("severity", "WARNING")).upper(),
        "missing_ppe": missing,
        "fall_detected": fall,
        "zone_violation": zone_violation,
        "time_window": time_window_for_hour(timestamp.hour),
    }


def load_csv_events(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return [normalize_event(row) for row in csv.DictReader(stream)]


def load_jsonl_events(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            events.append(normalize_event(value))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            LOG.warning("Skipping malformed alert event at %s:%d (%s)", path, number, exc)
    return events


def _dominant(events, field):
    values = [event[field] for event in events if event.get(field)]
    return Counter(values).most_common(1)[0][0] if values else None


def analyze_zone_patterns(events) -> list[dict]:
    grouped = defaultdict(list)
    for event in events:
        grouped[event["zone"]].append(event)
    return [{
        "zone": zone,
        "incident_count": len(items),
        "critical_count": sum(item["severity"] == "CRITICAL" for item in items),
        "dominant_violation": _dominant(items, "violation_type"),
    } for zone, items in sorted(grouped.items())]


def analyze_time_patterns(events) -> list[dict]:
    grouped = defaultdict(list)
    for event in events:
        grouped[event["time_window"]].append(event)
    return [{
        "time_window": window,
        "incident_count": len(items),
        "critical_count": sum(item["severity"] == "CRITICAL" for item in items),
        "dominant_violation": _dominant(items, "violation_type"),
    } for window, items in sorted(grouped.items())]


def analyze_risk_patterns(events) -> dict:
    if not events:
        return {"status": "insufficient_data"}
    ordered = sorted(events, key=lambda event: event["timestamp"])
    temporal_midpoint = ordered[0]["timestamp"] + (ordered[-1]["timestamp"] - ordered[0]["timestamp"]) / 2
    first = [event for event in ordered if event["timestamp"] < temporal_midpoint]
    second = [event for event in ordered if event["timestamp"] >= temporal_midpoint]
    delta = len(second) - len(first)
    return {
        "status": "ok",
        "total_incidents": len(events),
        "most_common_violation": _dominant(events, "violation_type"),
        "most_affected_task": _dominant(events, "task"),
        "incident_trend": "increasing" if delta > 0 else "decreasing" if delta < 0 else "stable",
    }
