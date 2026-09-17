"""Train a risk model from Diraya historical events."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

from tools.historical_patterns import (TIME_WINDOWS, load_csv_events, load_jsonl_events,
                                       time_window_for_hour)

FEATURE_NAMES = ["zone", "hour", "time_window", "day_of_week", "task", "recent_incident_count",
                 "recent_critical_count", "ppe_violation_count", "zone_violation_count", "fall_count"]
LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def risk_label(score):
    # Future 7-day weighted incident burden: WARNING=1, CRITICAL=3.
    if score == 0:
        return "LOW"
    if score <= 3:
        return "MEDIUM"
    if score <= 7:
        return "HIGH"
    return "CRITICAL"


def short_history_risk_label(score):
    """Map the next hour's alert burden for the explicitly demo-only mode."""
    if score == 0:
        return "LOW"
    if score <= 5:
        return "MEDIUM"
    if score <= 20:
        return "HIGH"
    return "CRITICAL"


def _feature_row(events, zone, window, cutoff, lookback):
    recent = [event for event in events if event["zone"] == zone and
              cutoff - lookback <= event["timestamp"] < cutoff and
              event["time_window"] == window]
    tasks = Counter(event["task"] for event in recent)
    return {
        "zone": zone, "hour": int(window[:2]), "time_window": window,
        "day_of_week": cutoff.strftime("%A"),
        "task": tasks.most_common(1)[0][0] if tasks else "unknown",
        "recent_incident_count": len(recent),
        "recent_critical_count": sum(e["severity"] == "CRITICAL" for e in recent),
        "ppe_violation_count": sum(e["violation_type"] == "PPE Non-Compliance" for e in recent),
        "zone_violation_count": sum(e["zone_violation"] for e in recent),
        "fall_count": sum(e["fall_detected"] for e in recent),
    }


def build_training_rows(events, lookback_days=14, horizon_days=7):
    if not events:
        return [], []
    events = sorted(events, key=lambda event: event["timestamp"])
    zones = sorted({event["zone"] for event in events if event["zone"] != "Unspecified Zone"})
    start = events[0]["timestamp"].replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=lookback_days)
    end = events[-1]["timestamp"] - timedelta(days=horizon_days)
    rows, labels = [], []
    cursor = start
    while cursor <= end:
        for zone in zones:
            for window in TIME_WINDOWS:
                hour = int(window[:2])
                cutoff = cursor.replace(hour=hour)
                future = [event for event in events if event["zone"] == zone and
                          cutoff <= event["timestamp"] < cutoff + timedelta(days=horizon_days) and
                          event["time_window"] == window]
                rows.append(_feature_row(events, zone, window, cutoff, timedelta(days=lookback_days)))
                labels.append(risk_label(sum(3 if e["severity"] == "CRITICAL" else 1 for e in future)))
        # Daily cutoffs expose every weekday while retaining a chronological split.
        cursor += timedelta(days=1)
    return rows, labels


def build_short_history_rows(events):
    """Create 15-minute snapshots using 2h history to forecast the next hour."""
    events = sorted(events, key=lambda event: event["timestamp"])
    zones = sorted({event["zone"] for event in events if event["zone"] != "Unspecified Zone"})
    cursor = events[0]["timestamp"] + timedelta(hours=2)
    end = events[-1]["timestamp"] - timedelta(hours=1)
    rows, labels = [], []
    while cursor <= end:
        window = time_window_for_hour(cursor.hour)
        if window in TIME_WINDOWS:
            for zone in zones:
                future = [event for event in events if event["zone"] == zone and
                          cursor <= event["timestamp"] < cursor + timedelta(hours=1)]
                rows.append(_feature_row(events, zone, window, cursor, timedelta(hours=2)))
                labels.append(short_history_risk_label(
                    sum(3 if e["severity"] == "CRITICAL" else 1 for e in future)))
        cursor += timedelta(minutes=15)
    return rows, labels


def train(data_path="outputs/alerts.jsonl", model_path="ml/models/risk_model.joblib",
          metrics_path="ml/models/metrics.json"):
    data_path = Path(data_path)
    events = load_jsonl_events(data_path) if data_path.suffix.lower() == ".jsonl" else load_csv_events(data_path)
    if not events:
        raise ValueError("insufficient_data: no usable events")
    coverage = max(e["timestamp"] for e in events) - min(e["timestamp"] for e in events)
    demo_mode = coverage < timedelta(days=21)
    rows, labels = build_short_history_rows(events) if demo_mode else build_training_rows(events)
    if len(rows) < 20 or len(set(labels)) < 2:
        raise ValueError("insufficient_data: need at least 20 samples and two target classes")
    split = max(1, int(len(rows) * .8))
    pipeline = Pipeline([
        ("encode", DictVectorizer(sparse=False)),
        ("model", RandomForestClassifier(n_estimators=160, random_state=42, class_weight="balanced",
                                          min_samples_leaf=2, n_jobs=1)),
    ])
    pipeline.fit(rows[:split], labels[:split])
    predicted = pipeline.predict(rows[split:])
    metrics = {
        "accuracy": round(float(accuracy_score(labels[split:], predicted)), 4),
        "macro_f1": round(float(f1_score(labels[split:], predicted, average="macro", zero_division=0)), 4),
        "labels": LABELS,
        "confusion_matrix": confusion_matrix(labels[split:], predicted, labels=LABELS).tolist(),
        "train_samples": split, "test_samples": len(rows) - split,
        "class_distribution": dict(Counter(labels)),
        "training_mode": "short_history_demo" if demo_mode else "standard",
        "data_source": str(data_path),
        "history_hours": round(coverage.total_seconds() / 3600, 2),
        "note": ("Demo-only metrics from a short system alert log; not evidence of real-world performance."
                 if demo_mode else "Historical-data evaluation; requires prospective facility validation."),
    }
    target = ("1-hour future weighted alert burden (WARNING=1, CRITICAL=3): 0 LOW, 1-5 MEDIUM, 6-20 HIGH, >20 CRITICAL"
              if demo_mode else
              "7-day future weighted incident burden (WARNING=1, CRITICAL=3): 0 LOW, 1-3 MEDIUM, 4-7 HIGH, >=8 CRITICAL")
    bundle = {"pipeline": pipeline, "features": FEATURE_NAMES, "labels": LABELS,
              "target": target, "training_mode": metrics["training_mode"],
              "lookback_hours": 2 if demo_mode else 24 * 14,
              "data_source": str(data_path)}
    model_path, metrics_path = Path(model_path), Path(metrics_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="outputs/alerts.jsonl")
    parser.add_argument("--model", default="ml/models/risk_model.joblib")
    args = parser.parse_args()
    try:
        print(json.dumps(train(args.data, args.model), indent=2))
    except ValueError as exc:
        print(json.dumps({"status": "insufficient_data", "reason": str(exc)}, indent=2))
