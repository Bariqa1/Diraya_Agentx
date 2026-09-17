"""Separate LangGraph workflow for historical and predictive safety analysis."""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ml.risk_predictor import RiskPredictor
from tools.historical_patterns import (TIME_WINDOWS, analyze_risk_patterns,
                                       analyze_time_patterns, analyze_zone_patterns,
                                       load_csv_events, load_jsonl_events)

LOG = logging.getLogger(__name__)
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


class PredictionState(TypedDict, total=False):
    events: list[dict]
    analysis: dict
    result: dict


class PredictionAgent:
    """Orchestrates facts and model output; optional LLM text cannot alter facts."""

    def __init__(self, history_path="outputs/alerts.jsonl",
                 alerts_path=None, model_path="ml/models/risk_model.joblib",
                 output_path="outputs/prediction_summary.json", llm_client=None, llm_model=None):
        self.history_path = Path(history_path)
        self.alerts_path = Path(alerts_path) if alerts_path else None
        self.output_path = Path(output_path)
        self.model_path = Path(model_path)
        self.llm_client, self.llm_model = llm_client, llm_model
        graph = StateGraph(PredictionState)
        graph.add_node("load_history", self._load_history)
        graph.add_node("analyze_history", self._analyze_history)
        graph.add_node("predict_risk", self._predict_risk)
        graph.add_edge(START, "load_history")
        graph.add_edge("load_history", "analyze_history")
        graph.add_edge("analyze_history", "predict_risk")
        graph.add_edge("predict_risk", END)
        self.graph = graph.compile()

    def _load_history(self, state):
        primary = (load_jsonl_events(self.history_path) if self.history_path.suffix.lower() == ".jsonl"
                   else load_csv_events(self.history_path))
        alerts = load_jsonl_events(self.alerts_path) if self.alerts_path else []
        return {"events": primary + alerts}

    @staticmethod
    def _analyze_history(state):
        events = state["events"]
        return {"analysis": {"risk": analyze_risk_patterns(events),
                             "zones": analyze_zone_patterns(events),
                             "times": analyze_time_patterns(events)}}

    @staticmethod
    def _features(events, zone, window, when, lookback_hours=24 * 14):
        cutoff = when.replace(hour=int(window[:2]), minute=0, second=0, microsecond=0)
        recent = [event for event in events if event["zone"] == zone and event["time_window"] == window
                  and cutoff - timedelta(hours=lookback_hours) <= event["timestamp"] < cutoff]
        tasks = Counter(event["task"] for event in recent)
        return {"zone": zone, "hour": int(window[:2]), "time_window": window,
                "day_of_week": cutoff.strftime("%A"),
                "task": tasks.most_common(1)[0][0] if tasks else "unknown",
                "recent_incident_count": len(recent),
                "recent_critical_count": sum(e["severity"] == "CRITICAL" for e in recent),
                "ppe_violation_count": sum(e["violation_type"] == "PPE Non-Compliance" for e in recent),
                "zone_violation_count": sum(e["zone_violation"] for e in recent),
                "fall_count": sum(e["fall_detected"] for e in recent)}

    def _predict_risk(self, state):
        events, analysis = state["events"], state["analysis"]
        named = [event for event in events if event["zone"] != "Unspecified Zone"]
        if len(named) < 20 or not self.model_path.exists():
            return {"result": {"status": "insufficient_data", "prediction": None,
                               "historical_patterns": analysis["risk"], "zone_predictions": [],
                               "time_predictions": [], "evidence": {},
                               "explanation": "Not enough named-zone history is available for prediction."}}
        predictor = RiskPredictor(self.model_path)
        when = max(event["timestamp"] for event in named) + timedelta(days=1)
        zones = sorted({event["zone"] for event in named})
        matrix = []
        for zone in zones:
            for window in TIME_WINDOWS:
                level = predictor.predict(self._features(named, zone, window, when,
                                                         predictor.lookback_hours))
                matrix.append({"zone": zone, "time_window": window, "risk_level": level})
        zone_predictions = []
        for zone in zones:
            choices = [row for row in matrix if row["zone"] == zone]
            peak = max(choices, key=lambda row: RISK_ORDER[row["risk_level"]])
            zone_predictions.append({"zone": zone, "risk_level": peak["risk_level"]})
        time_predictions = []
        for window in TIME_WINDOWS:
            choices = [row for row in matrix if row["time_window"] == window]
            peak = max(choices, key=lambda row: RISK_ORDER[row["risk_level"]])
            time_predictions.append({"time_window": window, "risk_level": peak["risk_level"]})
        # Stable tie breakers use historical critical/incident evidence.
        zone_stats = {row["zone"]: row for row in analysis["zones"]}
        time_stats = {row["time_window"]: row for row in analysis["times"]}
        best = max(matrix, key=lambda row: (RISK_ORDER[row["risk_level"]],
                   zone_stats[row["zone"]]["critical_count"],
                   time_stats.get(row["time_window"], {}).get("critical_count", 0),
                   zone_stats[row["zone"]]["incident_count"]))
        evidence = zone_stats[best["zone"]]
        result = {
            "status": "ok",
            "training_mode": predictor.training_mode,
            "prediction": {"expected_risk_zone": best["zone"],
                           "critical_time_window": best["time_window"],
                           "likely_risk": evidence["dominant_violation"],
                           "predicted_risk_level": best["risk_level"]},
            "historical_patterns": {key: analysis["risk"][key] for key in
                                    ("most_common_violation", "most_affected_task", "incident_trend")},
            "zone_predictions": zone_predictions, "time_predictions": time_predictions,
            "evidence": {"historical_incidents_in_zone": evidence["incident_count"],
                         "critical_incidents_in_zone": evidence["critical_count"],
                         "dominant_violation": evidence["dominant_violation"]},
        }
        result["explanation"] = self._explain(result)
        return {"result": result}

    def _explain(self, facts):
        prediction, evidence = facts["prediction"], facts["evidence"]
        fallback = (f"Historical patterns and the demonstration model identify {prediction['expected_risk_zone']} "
                    f"during {prediction['critical_time_window']} as {prediction['predicted_risk_level']} risk; "
                    f"the recurring concern is {prediction['likely_risk']} ({evidence['historical_incidents_in_zone']} historical events).")
        if self.llm_client is None or not self.llm_model:
            return fallback
        try:
            response = self.llm_client.models.generate_content(
                model=self.llm_model,
                contents="Explain these immutable predictive safety facts in at most 2 sentences. Do not add or alter values:\n" + json.dumps(facts),
            )
            return (response.text or "").strip() or fallback
        except Exception as exc:
            LOG.warning("Prediction explanation unavailable: %s", exc)
            return fallback

    def run(self):
        result = self.graph.invoke({})["result"]
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
