import csv
import json
from datetime import datetime, timedelta

import joblib
import pytest

from agents.prediction_agent import PredictionAgent
from ml.risk_predictor import RiskPredictor
from ml.train_risk_model import train
from tools.historical_patterns import (analyze_risk_patterns, analyze_time_patterns,
                                       analyze_zone_patterns, load_jsonl_events)


@pytest.fixture(scope="module")
def prediction_assets(tmp_path_factory):
    root = tmp_path_factory.mktemp("prediction")
    history, model = root / "events.csv", root / "model.joblib"
    fields = ["timestamp", "zone", "task", "violation_type", "severity",
              "missing_ppe", "fall_detected", "zone_violation"]
    zones = ["Welding Area", "Loading Area", "Assembly Area", "Maintenance Bay"]
    with history.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for day in range(45):
            for index, zone in enumerate(zones):
                if (day + index) % 3:
                    writer.writerow({"timestamp": (datetime(2026, 1, 1, 8 + index * 2) +
                                                     timedelta(days=day)).isoformat(),
                                     "zone": zone, "task": "Welding", "violation_type": "PPE Non-Compliance",
                                     "severity": "CRITICAL" if (day + index) % 5 == 0 else "WARNING",
                                     "missing_ppe": "Helmet", "fall_detected": False,
                                     "zone_violation": False})
    train(history, model, root / "metrics.json")
    return root, history, model


def event(zone="A", hour=14, severity="WARNING", violation="PPE Non-Compliance"):
    return {"timestamp": datetime(2026, 1, 1, hour), "zone": zone, "task": "Welding",
            "violation_type": violation, "severity": severity, "missing_ppe": ["Helmet"],
            "fall_detected": False, "zone_violation": violation == "Zone Violation",
            "time_window": "14:00-16:00" if hour == 14 else "08:00-10:00"}


def test_historical_patterns_and_zone_aggregation():
    events = [event("A"), event("A", severity="CRITICAL"), event("B", violation="Fall")]
    risk = analyze_risk_patterns(events)
    zones = {row["zone"]: row for row in analyze_zone_patterns(events)}
    assert risk["most_common_violation"] == "PPE Non-Compliance"
    assert risk["most_affected_task"] == "Welding"
    assert zones["A"]["incident_count"] == 2
    assert zones["A"]["critical_count"] == 1


def test_time_aggregation():
    rows = analyze_time_patterns([event(hour=14), event(hour=14, severity="CRITICAL"), event(hour=8)])
    result = {row["time_window"]: row for row in rows}
    assert result["14:00-16:00"]["incident_count"] == 2
    assert result["14:00-16:00"]["critical_count"] == 1


def test_model_loading_and_inference(prediction_assets):
    _, _, model = prediction_assets
    predictor = RiskPredictor(model)
    features = {"zone": "Welding Area", "hour": 14, "time_window": "14:00-16:00",
                "day_of_week": "Monday", "task": "Welding", "recent_incident_count": 4,
                "recent_critical_count": 1, "ppe_violation_count": 3,
                "zone_violation_count": 0, "fall_count": 0}
    assert predictor.predict(features) in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_agent_outputs_zone_and_time_and_survives_llm_failure(prediction_assets):
    root, history, model = prediction_assets
    class BrokenModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("offline")
    class BrokenClient:
        models = BrokenModels()
    result = PredictionAgent(history, root / "missing.jsonl", model, root / "out.json",
                             BrokenClient(), "demo").run()
    assert result["status"] == "ok"
    assert result["prediction"]["expected_risk_zone"]
    assert result["prediction"]["critical_time_window"]
    assert len(result["zone_predictions"]) == 4
    assert len(result["time_predictions"]) == 5
    assert result["explanation"]


def test_missing_and_malformed_alerts_are_tolerated(tmp_path):
    assert load_jsonl_events(tmp_path / "missing.jsonl") == []
    path = tmp_path / "alerts.jsonl"
    path.write_text('{bad json}\n' + json.dumps({"timestamp": "2026-01-01T14:00:00",
                    "severity": "WARNING", "task": "test"}), encoding="utf-8")
    assert len(load_jsonl_events(path)) == 1


def test_empty_history_returns_insufficient_data(prediction_assets, tmp_path):
    _, _, model = prediction_assets
    empty = tmp_path / "empty.csv"
    empty.write_text("timestamp,zone,task,violation_type,severity,missing_ppe,fall_detected,zone_violation\n",
                     encoding="utf-8")
    result = PredictionAgent(empty, tmp_path / "none.jsonl", model, tmp_path / "out.json").run()
    assert result["status"] == "insufficient_data"
