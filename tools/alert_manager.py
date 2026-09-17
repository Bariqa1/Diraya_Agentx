"""Alert Manager: deduplication, throttling, routing, dispatch."""
import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

LOG = logging.getLogger(__name__)

DEFAULT_ALERTS_LOG = Path("outputs/alerts.jsonl")


@dataclass
class AlertEvent:
    timestamp: float
    severity: str
    escalation: str
    task: str
    missing_ppe: List[str]
    zone_violation: bool
    fall_detected: bool
    reason_codes: List[str]
    explanation: Optional[str] = None
    frame_id: Optional[str] = None
    incident_id: Optional[str] = None
    zone: str = "Unspecified Zone"


class AlertManager:
    """Decides when to fire an alert, deduplicates, throttles, dispatches."""

    def __init__(
        self,
        dedup_window_sec: float = 30.0,
        throttle_window_sec: float = 60.0,
        max_alerts_per_window: int = 5,
        alerts_log_path: Path = DEFAULT_ALERTS_LOG,
        handlers: Optional[Dict[str, Callable]] = None,
        zone: str = "Unspecified Zone",
    ):
        self.dedup_window_sec = dedup_window_sec
        self.throttle_window_sec = throttle_window_sec
        self.max_alerts_per_window = max_alerts_per_window
        self.alerts_log_path = Path(alerts_log_path)
        self.handlers = handlers or {}
        self.zone = zone

        # state
        self._last_sent: Dict[str, float] = {}
        self._recent_times: List[float] = []
        self._counter = 0

    def should_alert(self, decision: dict) -> bool:
        """Check whether this decision will actually trigger an alert without updating state."""
        if not decision.get("alert"):
            return False
        signature = self._signature(decision)
        now = time.time()
        return self._should_dedupe(signature, now) and self._should_throttle(now)

    def process(self, decision: dict, frame_id: Optional[str] = None) -> Optional[AlertEvent]:
        """
        Decide if an alert should be sent.
        Returns AlertEvent if dispatched, None if suppressed.
        """
        if not decision.get("alert"):
            return None

        signature = self._signature(decision)
        now = time.time()

        # 1) Dedup
        if not self._should_dedupe(signature, now):
            LOG.debug("Alert suppressed (dedup): %s", signature)
            return None

        # 2) Throttle
        if not self._should_throttle(now):
            LOG.warning("Alert suppressed (throttle): %s", signature)
            return None

        # 3) Build event
        self._counter += 1
        event = AlertEvent(
            timestamp=now,
            severity=decision.get("severity", "UNKNOWN"),
            escalation=decision.get("escalation", "none"),
            task=decision.get("task", "unknown"),
            missing_ppe=decision.get("missing_ppe", []),
            zone_violation=bool(decision.get("zone_violation", False)),
            fall_detected=bool(decision.get("fall_detected", False)),
            reason_codes=[r.get("code", "") for r in decision.get("reasons", [])],
            explanation=decision.get("explanation"),
            frame_id=frame_id,
            incident_id=f"ALT-{self._counter:04d}",
            zone=self.zone,
        )

        # 4) Update state
        self._last_sent[signature] = now
        self._recent_times.append(now)

        # 5) Dispatch
        self._dispatch(event)

        # 6) Log
        self._log_event(event)

        return event

    @staticmethod
    def _signature(decision: dict) -> str:
        """Unique signature for dedup."""
        return "|".join([
            decision.get("severity", ""),
            decision.get("task", ""),
            ",".join(sorted(decision.get("missing_ppe", []))),
            "zone" if decision.get("zone_violation") else "nozone",
            "fall" if decision.get("fall_detected") else "nofall",
        ])

    def _should_dedupe(self, signature: str, now: float) -> bool:
        last = self._last_sent.get(signature)
        if last is None:
            return True
        return (now - last) >= self.dedup_window_sec

    def _should_throttle(self, now: float) -> bool:
        cutoff = now - self.throttle_window_sec
        self._recent_times = [t for t in self._recent_times if t >= cutoff]
        return len(self._recent_times) < self.max_alerts_per_window

    def _dispatch(self, event: AlertEvent) -> None:
        for name, handler in self.handlers.items():
            try:
                handler(event)
                LOG.info("Alert dispatched via '%s' (%s)", name, event.severity)
            except Exception as exc:
                LOG.error("Handler '%s' failed: %s", name, exc)

    def _log_event(self, event: AlertEvent) -> None:
        try:
            self.alerts_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.alerts_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        except Exception as exc:
            LOG.warning("Alert log write failed: %s", exc)

    def stats(self) -> dict:
        return {
            "total_alerts_sent": self._counter,
            "unique_signatures": len(self._last_sent),
            "recent_window_count": len(self._recent_times),
        }
