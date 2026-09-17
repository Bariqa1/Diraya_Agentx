"""Compliance Agent: deterministic Rule Engine + LLM explanation layer.

Decision (alert, severity, missing_ppe, escalation) is fully deterministic.
The LLM only produces human-readable explanations — it CANNOT override the decision.
"""
import json as _json
import logging
from typing import Dict, List, Optional

from tools.manual_rules import ManualRules
from tools.ppe_analysis import analyze_ppe

try:
    from langsmith import traceable
except ImportError:
    def traceable(*args, **kwargs):
        def decorator(f):
            return f
        return decorator if not args or not callable(args[0]) else args[0]

LOG = logging.getLogger(__name__)

SEVERITY_ORDER = {"SAFE": 0, "WARNING": 1, "CRITICAL": 2}

EXPLANATION_PROMPT = """You explain a pre-computed safety decision to a human operator.

FACTS (do not change or contradict):
{decision_json}

Rules:
- Explain in ONE concise paragraph (max 3 sentences).
- Match the language of the citation if present; otherwise English.
- Do NOT invent PPE, do NOT change severity, do NOT invent tasks.
- If severity is SAFE, write a brief confirmation.
- If unknown_task is true, mention that the task could not be identified.
- If low_confidence is true, mention that confidence was low.
- Return ONLY the explanation text, no JSON, no markdown.

Explain this decision:
"""


class ComplianceAgent:
    """Deterministic compliance evaluator backed by ManualRules."""

    def __init__(
        self,
        rules: ManualRules,
        ppe_conf_threshold: float = 0.25,
        low_confidence_threshold: float = 0.5,
        escalate_on_unknown_task: bool = True,
        escalate_on_low_confidence: bool = True,
        llm_client=None,
        llm_model: Optional[str] = None,
    ):
        self.rules = rules
        self.ppe_conf_threshold = ppe_conf_threshold
        self.low_confidence_threshold = low_confidence_threshold
        self.escalate_on_unknown_task = escalate_on_unknown_task
        self.escalate_on_low_confidence = escalate_on_low_confidence
        self.llm_client = llm_client
        self.llm_model = llm_model

    # ══════════════════════════════════════════════════════════
    # DETERMINISTIC LAYER
    # ══════════════════════════════════════════════════════════

    @traceable(name="compliance_evaluate", run_type="chain")
    def evaluate(self, observation: dict) -> dict:
        context = observation.get("context", {})
        zone = observation.get("zone", {})
        fall = observation.get("fall", {})
        ppe = observation.get("ppe", {})

        task = (context.get("task") or "unknown").strip().lower()
        task_source = context.get("source", "unknown")

        try:
            context_confidence = float(context.get("confidence") or 0.0)
        except (TypeError, ValueError):
            context_confidence = 0.0

        # ── Required PPE (via ManualRules) ──
        req = self.rules.get_required_ppe(task)
        critical_ppe = req.get("critical_ppe", []) or []
        recommended_ppe = req.get("recommended_ppe", []) or []
        rule_source = req.get("source", "unknown")
        rule_confidence = float(req.get("confidence", 0.0) or 0.0)
        citation = req.get("citation", "") or ""
        requires_review = bool(req.get("requires_manual_review", False))

        # ── Detected PPE ──
        ppe_state = analyze_ppe(ppe, conf_threshold=self.ppe_conf_threshold)
        detected = ppe_state["detected"]
        missing_from_vision = set(ppe_state["missing"])
        uncertain = ppe_state["uncertain"]

        # ── Deterministic flags ──
        unknown_task = (rule_source == "conservative_default")
        low_confidence = (context_confidence < self.low_confidence_threshold)
        zone_violation = bool(zone.get("violation", False))
        fall_detected = bool(fall.get("detected", False))

        # ── Compare ──
        missing_critical = [p for p in critical_ppe if p in missing_from_vision]
        missing_recommended = [p for p in recommended_ppe if p in missing_from_vision]

        # ── Deterministic severity (policy explicit) ──
        severity = "SAFE"
        reasons: List[dict] = []

        if fall_detected:
            severity = "CRITICAL"
            reasons.append({
                "code": "fall_detected",
                "text": "Possible worker fall detected",
                "severity": "CRITICAL",
            })

        if zone_violation:
            severity = "CRITICAL"
            reasons.append({
                "code": "zone_violation",
                "text": "Worker inside restricted zone",
                "severity": "CRITICAL",
            })

        if missing_critical:
            if rule_source == "conservative_default":
                if SEVERITY_ORDER[severity] < SEVERITY_ORDER["WARNING"]:
                    severity = "WARNING"
                reasons.append({
                    "code": "missing_critical_ppe_unverified",
                    "text": f"Potential missing critical PPE (unverified task): "
                            f"{', '.join(missing_critical)}",
                    "severity": "WARNING",
                    "ppe": missing_critical,
                })
            else:
                severity = "CRITICAL"
                reasons.append({
                    "code": "missing_critical_ppe",
                    "text": f"Missing critical PPE: {', '.join(missing_critical)}",
                    "severity": "CRITICAL",
                    "ppe": missing_critical,
                })

        if missing_recommended:
            if SEVERITY_ORDER[severity] < SEVERITY_ORDER["WARNING"]:
                severity = "WARNING"
            reasons.append({
                "code": "missing_recommended_ppe",
                "text": f"Missing recommended PPE: {', '.join(missing_recommended)}",
                "severity": "WARNING",
                "ppe": missing_recommended,
            })

        if low_confidence and self.escalate_on_low_confidence:
            if SEVERITY_ORDER[severity] < SEVERITY_ORDER["WARNING"]:
                severity = "WARNING"
            reasons.append({
                "code": "low_confidence",
                "text": f"Low task confidence ({context_confidence:.2f})",
                "severity": "WARNING",
            })

        if unknown_task and self.escalate_on_unknown_task:
            if SEVERITY_ORDER[severity] < SEVERITY_ORDER["WARNING"]:
                severity = "WARNING"
            reasons.append({
                "code": "unknown_task",
                "text": "Task rule not found; manual review needed",
                "severity": "WARNING",
            })

        if requires_review and severity == "SAFE":
            severity = "WARNING"
            reasons.append({
                "code": "rule_pending_review",
                "text": f"Rule for '{task}' not yet reviewed by a human",
                "severity": "WARNING",
            })

        if uncertain and severity == "SAFE":
            reasons.append({
                "code": "ppe_uncertain",
                "text": f"PPE not visually confirmed: {', '.join(uncertain)}",
                "severity": "SAFE",
            })

        alert = severity in ("WARNING", "CRITICAL")

        escalation = self._escalation_for(severity, zone_violation, fall_detected)

        return {
            "alert": alert,
            "severity": severity,
            "task": task,
            "task_source": task_source,
            "task_confidence": round(context_confidence, 2),
            "required_ppe": list(critical_ppe) + list(recommended_ppe),
            "critical_ppe": list(critical_ppe),
            "recommended_ppe": list(recommended_ppe),
            "detected_ppe": detected,
            "missing_ppe": sorted(set(missing_critical + missing_recommended)),
            "missing_critical_ppe": missing_critical,
            "missing_recommended_ppe": missing_recommended,
            "zone_violation": zone_violation,
            "fall_detected": fall_detected,
            "unknown_task": unknown_task,
            "low_confidence": low_confidence,
            "reasons": reasons,
            "rule_source": rule_source,
            "rule_confidence": round(rule_confidence, 2),
            "citation": citation,
            "requires_manual_review": requires_review,
            "escalation": escalation,
            "explanation": None,
        }

    @staticmethod
    def _escalation_for(severity: str, zone_violation: bool, fall_detected: bool = False) -> str:
        """Deterministic escalation policy. Documented & auditable."""
        if severity == "SAFE":
            return "none"
        if severity == "WARNING":
            return "supervisor"
        return "emergency" if zone_violation or fall_detected else "safety_officer"

    # ══════════════════════════════════════════════════════════
    # LLM EXPLANATION LAYER (does NOT change the decision)
    # ══════════════════════════════════════════════════════════

    @traceable(name="compliance_explain", run_type="llm")
    def explain(self, decision: dict) -> dict:
        """
        Add a human-readable explanation to an existing decision.

        Reads only facts from `decision`.
        Writes only `explanation`.
        Never touches alert/severity/missing_ppe/reasons/escalation.
        """
        if self.llm_client is None or not self.llm_model:
            return {**decision, "explanation": None}

        facts = {
            "task": decision.get("task"),
            "severity": decision.get("severity"),
            "alert": decision.get("alert"),
            "missing_ppe": decision.get("missing_ppe"),
            "detected_ppe": decision.get("detected_ppe"),
            "required_ppe": decision.get("required_ppe"),
            "zone_violation": decision.get("zone_violation"),
            "fall_detected": decision.get("fall_detected"),
            "unknown_task": decision.get("unknown_task"),
            "low_confidence": decision.get("low_confidence"),
            "task_confidence": decision.get("task_confidence"),
            "citation": decision.get("citation"),
            "escalation": decision.get("escalation"),
        }

        try:
            from google.genai import types
            response = self.llm_client.models.generate_content(
                model=self.llm_model,
                contents=EXPLANATION_PROMPT.format(
                    decision_json=_json.dumps(facts, ensure_ascii=False, indent=2)
                ),
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            )
            text = (response.text or "").strip()
        except Exception as exc:
            LOG.warning("Explanation layer failed: %s", exc)
            text = None

        return {**decision, "explanation": text}
