"""Incident Aggregator and Alert Dispatcher.

Debounces frame-by-frame compliance alerts into coherent, timed incidents.
Prevents alert fatigue and compiles an executive safety audit log.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

LOG = logging.getLogger(__name__)


@dataclass
class Incident:
    incident_id: str
    incident_type: str
    start_time: float
    end_time: float
    peak_severity: str
    escalation: str
    task: str
    details: Dict[str, Any] = field(default_factory=dict)
    active: bool = True

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


class AlertDispatcher:
    """Aggregates continuous frame alerts into discrete safety incidents."""

    def __init__(self, debounce_seconds: float = 1.5):
        self.debounce_seconds = debounce_seconds
        self.incidents: List[Incident] = []
        self._active_incidents: Dict[str, Incident] = {}
        self._incident_counter = 0

    def process(self, compliance_decision: Dict[str, Any], timestamp: float) -> Optional[Incident]:
        alert = compliance_decision.get("alert", False)
        severity = compliance_decision.get("severity", "SAFE")
        zone_violation = compliance_decision.get("zone_violation", False)
        missing_ppe = compliance_decision.get("missing_ppe", [])
        task = compliance_decision.get("task", "unknown")
        escalation = compliance_decision.get("escalation", "none")

        active_keys = set()

        if zone_violation:
            key = "zone_violation"
            active_keys.add(key)
            self._update_incident(
                key=key,
                incident_type="Restricted Zone Breach",
                timestamp=timestamp,
                severity=severity,
                escalation=escalation,
                task=task,
                details={"zone_violation": True},
            )

        if missing_ppe:
            for item in missing_ppe:
                key = f"missing_ppe_{item}"
                active_keys.add(key)
                self._update_incident(
                    key=key,
                    incident_type=f"Missing PPE ({item})",
                    timestamp=timestamp,
                    severity=severity,
                    escalation=escalation,
                    task=task,
                    details={"missing_item": item},
                )

        # Close incidents that are no longer active after debounce window
        to_remove = []
        for key, inc in self._active_incidents.items():
            if key not in active_keys:
                if (timestamp - inc.end_time) >= self.debounce_seconds:
                    inc.active = False
                    to_remove.append(key)

        for k in to_remove:
            closed_inc = self._active_incidents.pop(k)
            LOG.info(
                "Incident CLOSED: %s (Duration: %.1fs, Peak: %s, Escalation: %s)",
                closed_inc.incident_type,
                closed_inc.duration,
                closed_inc.peak_severity,
                closed_inc.escalation,
            )

        return None

    def _update_incident(
        self,
        key: str,
        incident_type: str,
        timestamp: float,
        severity: str,
        escalation: str,
        task: str,
        details: dict,
    ):
        if key in self._active_incidents:
            inc = self._active_incidents[key]
            inc.end_time = timestamp
            # Update peak severity if higher
            if severity == "CRITICAL" and inc.peak_severity != "CRITICAL":
                inc.peak_severity = "CRITICAL"
                inc.escalation = escalation
        else:
            self._incident_counter += 1
            inc = Incident(
                incident_id=f"INC-{self._incident_counter:03d}",
                incident_type=incident_type,
                start_time=timestamp,
                end_time=timestamp,
                peak_severity=severity,
                escalation=escalation,
                task=task,
                details=details,
                active=True,
            )
            self._active_incidents[key] = inc
            self.incidents.append(inc)
            LOG.warning(
                "New Incident TRIGGERED: %s [%s] -> Escalated to %s (Task: %s)",
                inc.incident_id,
                inc.incident_type,
                inc.escalation,
                inc.task,
            )

    def close_all(self, final_timestamp: float):
        for inc in self._active_incidents.values():
            inc.end_time = max(inc.end_time, final_timestamp)
            inc.active = False
        self._active_incidents.clear()

    def get_summary(self) -> Dict[str, Any]:
        critical_count = sum(1 for i in self.incidents if i.peak_severity == "CRITICAL")
        warning_count = sum(1 for i in self.incidents if i.peak_severity == "WARNING")
        return {
            "total_incidents": len(self.incidents),
            "critical_incidents": critical_count,
            "warning_incidents": warning_count,
            "incidents": [
                {
                    "id": i.incident_id,
                    "type": i.incident_type,
                    "start": round(i.start_time, 2),
                    "end": round(i.end_time, 2),
                    "duration_s": round(i.duration, 2),
                    "peak_severity": i.peak_severity,
                    "escalation": i.escalation,
                    "task": i.task,
                }
                for i in self.incidents
            ],
        }
