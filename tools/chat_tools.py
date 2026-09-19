"""Chat tools for the Safety Assistant.

Each tool reads from a specific data source in the system:
  1. get_required_ppe     -> ManualRules
  2. get_incident_stats   -> alerts.jsonl
  3. get_recent_incidents -> alerts.jsonl
  4. get_rule_metadata    -> manual_rules.json
  5. explain_violation    -> alerts.jsonl + ManualRules
"""
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Optional, List

from tools.manual_rules import ManualRules, normalize_task

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
ALERTS_LOG = ROOT / "outputs" / "alerts.jsonl"
FRAMES_LOG = ROOT / "outputs" / "context_agent_output.jsonl"
MANUAL_CACHE = ROOT / "data" / "manual_rules.json"


# ===========================================================
# Singletons
# ===========================================================

_rules: Optional[ManualRules] = None


def _get_rules() -> ManualRules:
    global _rules
    if _rules is None:
        _rules = ManualRules()
    return _rules


# ===========================================================
# Helpers
# ===========================================================

def _load_jsonl(path: Path, limit: Optional[int] = None) -> List[dict]:
    """Load rows from a JSONL file handling optional UTF-8 BOM."""
    if not path.exists():
        LOG.warning("JSONL not found: %s", path)
        return []

    rows = []
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        LOG.error("Failed to read %s: %s", path, exc)
        return []

    return rows[-limit:] if limit else rows


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


# ===========================================================
# Tool 1: get_required_ppe
# ===========================================================

def get_required_ppe(task: str) -> str:
    """
    Return the required PPE for a given industrial task from the safety manual.

    Args:
        task: Task name (e.g., "welding", "grinding", "working_at_height").

    Returns:
        JSON with critical_ppe, recommended_ppe, source, confidence, citation.
    """
    try:
        rules = _get_rules()
        result = rules.get_required_ppe(task)

        return _json({
            "task": task,
            "critical_ppe": result.get("critical_ppe", []),
            "recommended_ppe": result.get("recommended_ppe", []),
            "source": result.get("source", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "citation": result.get("citation", ""),
            "requires_manual_review": result.get("requires_manual_review", False),
        })
    except Exception as exc:
        LOG.error("get_required_ppe failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 2: get_incident_stats
# ===========================================================

def get_incident_stats(severity: Optional[str] = None) -> str:
    """
    Return incident statistics from alerts.jsonl.

    Args:
        severity: Optional filter ("CRITICAL", "WARNING", "SAFE").

    Returns:
        JSON with total count and breakdown by severity, task, escalation, zone, and falls.
    """
    try:
        rows = _load_jsonl(ALERTS_LOG)

        if severity:
            severity = severity.upper()
            rows = [r for r in rows if r.get("severity") == severity]

        by_severity = Counter(r.get("severity", "UNKNOWN") for r in rows)
        by_escalation = Counter(r.get("escalation", "unknown") for r in rows)
        by_task = Counter(r.get("task", "unknown") for r in rows)
        by_zone = Counter(r.get("zone", "unknown") for r in rows if r.get("zone"))
        fall_count = sum(1 for r in rows if r.get("fall_detected"))

        return _json({
            "total": len(rows),
            "filter": severity or "all",
            "by_severity": dict(by_severity),
            "by_escalation": dict(by_escalation),
            "by_task": dict(by_task.most_common(10)),
            "by_zone": dict(by_zone),
            "fall_incidents": fall_count,
            "source_file": str(ALERTS_LOG.name),
        })
    except Exception as exc:
        LOG.error("get_incident_stats failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 3: get_recent_incidents
# ===========================================================

def get_recent_incidents(n: int = 5, severity: Optional[str] = None) -> str:
    """
    Return the most recent incidents from alerts.jsonl.

    Args:
        n: Number of incidents to return (default 5, max 50).
        severity: Optional severity filter.

    Returns:
        JSON list of incidents (most recent first).
    """
    try:
        n = max(1, min(int(n), 50))
        rows = _load_jsonl(ALERTS_LOG)

        if severity:
            severity = severity.upper()
            rows = [r for r in rows if r.get("severity") == severity]

        recent = list(reversed(rows[-n:]))

        formatted = [{
            "incident_id": r.get("incident_id"),
            "severity": r.get("severity"),
            "task": r.get("task"),
            "missing_ppe": r.get("missing_ppe", []),
            "escalation": r.get("escalation"),
            "zone_violation": r.get("zone_violation", False),
            "fall_detected": r.get("fall_detected", False),
            "zone": r.get("zone", "unknown"),
            "frame_id": r.get("frame_id"),
            "timestamp": r.get("timestamp"),
            "reason_codes": r.get("reason_codes", []),
            "explanation": r.get("explanation"),
        } for r in recent]

        return _json({
            "count": len(formatted),
            "filter": severity or "all",
            "incidents": formatted,
        })
    except Exception as exc:
        LOG.error("get_recent_incidents failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 4: get_rule_metadata
# ===========================================================

def get_rule_metadata(task: str) -> str:
    """
    Return approval metadata for a specific rule.

    Args:
        task: Task name.

    Returns:
        JSON with approved_by, approved_at, source, confidence, etc.
    """
    try:
        if not MANUAL_CACHE.exists():
            return _json({
                "error": f"manual_rules.json not found at {MANUAL_CACHE}"
            })

        data = json.loads(MANUAL_CACHE.read_text(encoding="utf-8-sig"))
        tasks = data.get("tasks", {})

        key = normalize_task(task)

        # Direct match
        rule = tasks.get(key)

        # Fuzzy fallback via ManualRules resolver
        if not rule:
            rules = _get_rules()
            resolved = rules._resolve_task(key)
            if resolved:
                rule = tasks.get(resolved)
                key = resolved

        if not rule:
            return _json({
                "error": f"No rule found for task: {task}",
                "available_tasks": list(tasks.keys()),
            })

        return _json({
            "task": key,
            "approved_by": rule.get("approved_by"),
            "approved_at": rule.get("approved_at"),
            "source": rule.get("source"),
            "confidence": rule.get("confidence"),
            "requires_manual_review": rule.get("requires_manual_review"),
            "critical_ppe": rule.get("critical_ppe", []),
            "recommended_ppe": rule.get("recommended_ppe", []),
            "citation": rule.get("citation", ""),
        })
    except Exception as exc:
        LOG.error("get_rule_metadata failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 5: explain_violation
# ===========================================================

def explain_violation(incident_id: str) -> str:
    """
    Explain WHY a specific incident is a violation.

    Combines incident data (JSONL) with rule data (ManualRules).

    Args:
        incident_id: e.g., "ALT-0001" or "INC-001".

    Returns:
        JSON with incident details + applicable rule + reasoning.
    """
    try:
        rows = _load_jsonl(ALERTS_LOG)

        query_id = incident_id.strip()
        incident = next(
            (r for r in rows if str(r.get("incident_id")).upper() == query_id.upper()),
            None,
        )

        if not incident:
            return _json({
                "error": f"Incident {incident_id} not found",
                "hint": "Available incidents are in outputs/alerts.jsonl",
            })

        task = incident.get("task", "unknown")
        missing = incident.get("missing_ppe", [])

        rules = _get_rules()
        rule = rules.get_required_ppe(task)

        reasoning_parts = []
        if incident.get("fall_detected"):
            reasoning_parts.append("Fall hazard detected on worker")
        if incident.get("zone_violation"):
            reasoning_parts.append(f"Worker entered restricted zone: {incident.get('zone', 'Restricted Zone')}")
        if missing:
            reasoning_parts.append(f"Missing PPE: {', '.join(missing)}")
        if incident.get("severity") == "CRITICAL":
            reasoning_parts.append("Severity is CRITICAL")

        return _json({
            "incident": {
                "id": incident.get("incident_id"),
                "severity": incident.get("severity"),
                "task": task,
                "missing_ppe": missing,
                "zone_violation": incident.get("zone_violation", False),
                "fall_detected": incident.get("fall_detected", False),
                "zone": incident.get("zone", "unknown"),
                "escalation": incident.get("escalation"),
                "frame_id": incident.get("frame_id"),
                "timestamp": incident.get("timestamp"),
                "reason_codes": incident.get("reason_codes", []),
            },
            "applicable_rule": {
                "task": task,
                "critical_ppe": rule.get("critical_ppe", []),
                "recommended_ppe": rule.get("recommended_ppe", []),
                "source": rule.get("source"),
                "confidence": rule.get("confidence"),
                "citation": rule.get("citation", ""),
            },
            "reasoning": " | ".join(reasoning_parts) or "No clear reason",
        })
    except Exception as exc:
        LOG.error("explain_violation failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 6: get_environment_assessment
# ===========================================================

def get_environment_assessment(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    workload: str = "moderate",
) -> str:
    """
    Get real-time weather and heat stress (WBGT) assessment for the industrial facility.
    Includes Saudi Ministry of Human Resources (MHRSD) Midday Work Ban verification.

    Args:
        latitude: Optional GPS latitude (defaults to Jubail Industrial City).
        longitude: Optional GPS longitude (defaults to Jubail Industrial City).
        workload: Workload level ('light', 'moderate', 'heavy', 'very_heavy').

    Returns:
        JSON with location, live weather, WBGT, heat exposure, and safety recommendations.
    """
    try:
        from agents.environment_agent import EnvironmentAgent
        env_agent = EnvironmentAgent()
        result = env_agent.assess_current_facility(
            latitude=latitude,
            longitude=longitude,
            workload=workload,
        )
        return _json(result)
    except Exception as exc:
        LOG.error("get_environment_assessment failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 7: get_sign_hazard_zones
# ===========================================================

def get_sign_hazard_zones(sign_id: Optional[str] = None) -> str:
    """
    Get dynamic safety hazard perimeters defined by site signboards (e.g., High Voltage, Flammable Chemicals).
    Safety signs are read via VLM once and projected into dynamic ground-plane buffer zones.

    Args:
        sign_id: Optional sign identifier (e.g., 'SIGN-01', 'SIGN-02') to inspect a specific sign.

    Returns:
        JSON with signboards, text, hazard types, buffer radius in meters, required PPE, and caching status.
    """
    try:
        from tools.sign_hazard_monitor import SignHazardMonitor
        monitor = SignHazardMonitor()
        summary = monitor.get_summary()

        if sign_id:
            target = sign_id.strip().upper()
            filtered = [s for s in summary.get("signs", []) if s.get("sign_id", "").upper() == target]
            if not filtered:
                return _json({
                    "error": f"Sign '{sign_id}' not found.",
                    "available_signs": [s.get("sign_id") for s in summary.get("signs", [])],
                })
            return _json({
                "sign": filtered[0],
                "caching_strategy": summary.get("caching_strategy"),
            })

        return _json(summary)
    except Exception as exc:
        LOG.error("get_sign_hazard_zones failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 8: evaluate_zone_access
# ===========================================================

def evaluate_zone_access(
    worker_role: str,
    zone_id: str,
    carried_tools: Optional[List[str]] = None,
    ppe_worn: Optional[List[str]] = None,
) -> str:
    """
    Evaluate worker authorization and physical access into a hazardous facility zone.
    Computes a dynamic risk score (0-100%), authorization verdict, and alert escalation.

    Args:
        worker_role: Role name, title, or helmet color (e.g., 'White', 'Blue', 'electrician', 'engineer', 'laborer').
        zone_id: Zone ID (e.g., 'ZONE_SUBSTATION', 'ZONE_NO_GO_CRANE', 'ZONE_CHEMICAL', 'ZONE_WELDING_BAY').
        carried_tools: Optional list of tools carried (e.g. ['insulated_toolkit', 'gas_cylinder']).
        ppe_worn: Optional list of PPE currently worn (e.g. ['Hard Hat', 'Insulated Gloves']).

    Returns:
        JSON with access_granted (bool), risk_score (0-100), severity, action_required, and explanation.
    """
    try:
        from tools.zone_access_matrix import ZoneAccessEngine
        engine = ZoneAccessEngine()
        result = engine.evaluate_access(
            worker_role=worker_role,
            zone_id=zone_id,
            carried_tools=carried_tools,
            ppe_worn=ppe_worn,
        )
        return _json(result)
    except Exception as exc:
        LOG.error("evaluate_zone_access failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 9: get_zone_access_matrix
# ===========================================================

def get_zone_access_matrix(zone_id: Optional[str] = None) -> str:
    """
    Get the physical RBAC clearance matrix for facility zones and standard helmet roles.

    Args:
        zone_id: Optional zone ID (e.g., 'ZONE_SUBSTATION') to inspect a specific zone.

    Returns:
        JSON with authorized roles, forbidden roles, required PPE, required tools, and base hazard risk.
    """
    try:
        from tools.zone_access_matrix import ZoneAccessEngine
        engine = ZoneAccessEngine()
        summary = engine.get_matrix_summary()

        if zone_id:
            target = zone_id.strip().upper()
            filtered = [z for z in summary.get("zones", []) if z.get("zone_id", "").upper() == target]
            if not filtered:
                return _json({
                    "error": f"Zone '{zone_id}' not found.",
                    "available_zones": [z.get("zone_id") for z in summary.get("zones", [])],
                })
            return _json(filtered[0])

        return _json(summary)
    except Exception as exc:
        LOG.error("get_zone_access_matrix failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Tool 10: get_heat_stress_guidelines
# ===========================================================

def get_heat_stress_guidelines(topic: Optional[str] = "all") -> str:
    """
    Get official occupational safety guidelines and prevention procedures for heat stress,
    work/rest cycles, hydration protocols, and compliance with the Saudi MHRSD Midday Sun Work Ban.

    Args:
        topic: Optional topic filter ('prevention', 'hydration', 'symptoms_and_first_aid', 'saudi_regulations', 'all').

    Returns:
        JSON with comprehensive Arabic prevention procedures, regulatory mandates, and emergency actions.
    """
    try:
        guidelines = {
            "title": "إجراءات الوقاية من الإجهاد الحراري والسلامة المهنية في الأجواء الحارة",
            "regulatory_basis": [
                "قرار وزارة الموارد البشرية والتنمية الاجتماعية رقم 3337 (حظر العمل تحت أشعة الشمس)",
                "معايير إدارة السلامة والصحة المهنية الأمريكية (OSHA) للإجهاد الحراري",
                "المواصفة القياسية الدولية ISO 7243 (تقييم الإجهاد الحراري باستخدام معامل WBGT)",
            ],
            "core_prevention_procedures": [
                {
                    "id": "hydration",
                    "title": "بروتوكول الترطيب وشرب السوائل",
                    "action": "شرب كوب ماء بارد (250 مل) كل 15-20 دقيقة بانتظام دون انتظار الشعور بالعطش، وتوفير محاليل كهرلية (Electrolytes) لتعويض الأملاح المفقودة بالتعرق.",
                },
                {
                    "id": "work_rest_cycles",
                    "title": "فترات الراحة وجداول التناوب (Work/Rest Cycles)",
                    "action": "تطبيق دورات عمل وراحة في أماكن مبردة ومظللة بناءً على مؤشر WBGT وشدة المجهود البدني (مثال: 45 دقيقة عمل / 15 دقيقة راحة في درجات الحرارة المتوسطة، و 15 دقيقة عمل / 45 دقيقة راحة في مستويات الخطر العالية).",
                },
                {
                    "id": "saudi_midday_ban",
                    "title": "قرار حظر العمل وقت الظهيرة (وزارة الموارد البشرية والتنمية الاجتماعية)",
                    "action": "يحظر حظرًا تامًا تشغيل العامل تحت أشعة الشمس المباشرة من الساعة 12:00 ظهرًا إلى الساعة 3:00 عصرًا خلال الفترة من 15 يونيو إلى 15 سبتمبر من كل عام، مع فرض غرامات نظامية على المنشآت المخالفة.",
                },
                {
                    "id": "acclimatization",
                    "title": "التأقلم والتدرج الحراري (Acclimatization)",
                    "action": "إلزام العمال الجدد أو العائدين من إجازات بفترة تأقلم تمتد من 7 إلى 14 يومًا، تبدأ بـ 20% إلى 50% من الجهد البدني في اليوم الأول وتزداد تدريجيًا بنسبة لا تتجاوز 10-20% يوميًا.",
                },
                {
                    "id": "ppe_and_clothing",
                    "title": "الملابس ومعدات الوقاية الشخصية المناسبة للحرارة",
                    "action": "ارتداء ملابس خفيفة فضفاضة قطنية ذات ألوان فاتحة تعكس أشعة الشمس، واستخدام أغطية للرأس ذات حواف واقية أو بطانات مبردة تحت الخوذة (Hard Hat Sun Shades).",
                },
                {
                    "id": "monitoring_and_buddy_system",
                    "title": "المراقبة ونظام الزميل (Buddy System)",
                    "action": "تطبيق نظام الزميل لملاحظة أي علامات إعياء مبكرة مثل الدوخة، الصداع، الارتباك، التعرق الغزير أو انقطاعه، شحوب الوجه، أو الغثيان، والتبليغ الفوري لمشرف السلامة.",
                },
                {
                    "id": "emergency_first_aid",
                    "title": "إجراءات الطوارئ والإسعافات الأولية",
                    "action": "عند ظهور أعراض الإجهاد الحراري: نقل المصاب فورًا لمكان بارد ومظلل، رفع القدمين قليلًا، تبريد الجسم برذاذ الماء البارد أو كمادات الثلج على الرقبة والإبطين والفخذين، وطلب الإسعاف فورًا (الهلال الأحمر 997) في حال الاشتباه بضربة شمس (فقدان وعي، جلد ساخن وجاف).",
                },
            ],
            "source": "Diraya Industrial Safety Manual & Saudi MHRSD Decision 3337",
        }
        return _json(guidelines)
    except Exception as exc:
        LOG.error("get_heat_stress_guidelines failed: %s", exc)
        return _json({"error": str(exc)})


# ===========================================================
# Registry (used by agent)
# ===========================================================

CHAT_TOOL_REGISTRY = {
    "get_required_ppe": get_required_ppe,
    "get_incident_stats": get_incident_stats,
    "get_recent_incidents": get_recent_incidents,
    "get_rule_metadata": get_rule_metadata,
    "explain_violation": explain_violation,
    "get_environment_assessment": get_environment_assessment,
    "get_sign_hazard_zones": get_sign_hazard_zones,
    "evaluate_zone_access": evaluate_zone_access,
    "get_zone_access_matrix": get_zone_access_matrix,
    "get_heat_stress_guidelines": get_heat_stress_guidelines,
}



