from copy import deepcopy
import logging
import math
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from config import positive
from tools.gemini_context import unknown_context

LOG = logging.getLogger(__name__)


class ContextState(TypedDict, total=False):
    frame: Any
    timestamp: float
    ppe: dict
    zone: dict
    context: dict
    cached_context: dict | None
    cache_timestamp: float | None
    retry_after: float | None
    gemini_called: bool
    force_vlm: bool
    route: str
    errors: list[str]
    status: str
    observation: dict


class ContextAgent:
    def __init__(self, ppe_detector, context_tool, zone_monitor, cache_ttl=30,
                 failure_cooldown=5, log_interval=1):
        self.ppe_detector, self.context_tool, self.zone_monitor = ppe_detector, context_tool, zone_monitor
        self.cache_ttl = positive(cache_ttl, "cache_ttl")
        self.failure_cooldown = positive(failure_cooldown, "failure_cooldown")
        self.log_interval = positive(log_interval, "log_interval")
        self.reset_cache()
        graph = StateGraph(ContextState)
        for name, node in (("ppe_detection", self._ppe), ("zone_monitoring", self._zone),
                           ("check_cache", self._check), ("use_cache", self._cached),
                           ("gemini", self._gemini), ("fusion", self._fuse)):
            graph.add_node(name, node)
        graph.add_edge(START, "check_cache")
        graph.add_conditional_edges("check_cache", lambda s: s["route"],
                                    {"cache": "use_cache", "vlm": "gemini"})
        graph.add_edge("use_cache", "ppe_detection")
        graph.add_edge("gemini", "ppe_detection")
        graph.add_edge("ppe_detection", "zone_monitoring")
        graph.add_edge("zone_monitoring", "fusion")
        graph.add_edge("fusion", END)
        self.graph = graph.compile()

    def reset_cache(self):
        self._memory = dict(cached_context=None, cache_timestamp=None, retry_after=None)
        self._last_timestamp = None
        self._last_log = -math.inf
        self._was_in_violation = False
        self._pending_force_vlm = False

    def _ppe(self, state):
        try:
            return {"ppe": self.ppe_detector.detect(state["frame"])}
        except Exception as exc:
            return {"ppe": {"detections": [], "confidence": None},
                    "errors": state["errors"] + [f"ppe:{type(exc).__name__}"]}

    def _zone(self, state):
        try:
            return {"zone": self.zone_monitor.detect(state["frame"])}
        except Exception as exc:
            return {"zone": {"persons": [], "violation": None},
                    "errors": state["errors"] + [f"zone:{type(exc).__name__}"]}

    def _check(self, state):
        valid = (state["cached_context"] is not None and state["cache_timestamp"] is not None
                 and state["timestamp"] - state["cache_timestamp"] < self.cache_ttl)
        cooling = state["retry_after"] is not None and state["timestamp"] < state["retry_after"]
        force = state.get("force_vlm", False)
        if cooling:
            return {"route": "cache"}
        if force or not valid:
            reason = ("VLM forced by zone violation" if force else
                      ("No VLM cache" if state["cached_context"] is None else "VLM cache expired"))
            LOG.info("[%s] %s -> calling Gemini", self._stamp(state["timestamp"]), reason)
            return {"route": "vlm"}
        return {"route": "cache"}

    def _cached(self, state):
        failed = state["retry_after"] is not None and state["timestamp"] < state["retry_after"]
        context = deepcopy(state["cached_context"]) if state["cached_context"] is not None else unknown_context()
        if state["cached_context"] is None:
            source = "unavailable"
        elif failed:
            source = "cache_after_vlm_failure"
        else:
            source = "cache"
        errors = state["errors"] + (["gemini:failure_cooldown"] if failed else [])
        return {"context": {**context, "source": source}, "errors": errors}

    def _gemini(self, state):
        try:
            context = self.context_tool.analyze(state["frame"])
            LOG.info("[%s] Gemini context: %s", self._stamp(state["timestamp"]), context["task"])
            return {"context": {**context, "source": "gemini"}, "cached_context": deepcopy(context),
                    "cache_timestamp": state["timestamp"], "retry_after": None, "gemini_called": True}
        except Exception as exc:
            code = getattr(exc, "code", None)
            hints = {400: "Check the Gemini model ID and request configuration.",
                     401: "Check GEMINI_API_KEY.", 403: "Check API key permissions and API access.",
                     404: "Check GEMINI_MODEL: use an API model ID, not a display name.",
                     429: "Gemini quota or rate limit reached.", 503: "Gemini temporarily unavailable."}
            LOG.warning("[%s] Gemini unavailable (%s, HTTP %s). %s", self._stamp(state["timestamp"]),
                        type(exc).__name__, code, hints.get(code, "Check Gemini connectivity and configuration."))
            context = deepcopy(state["cached_context"]) if state["cached_context"] is not None else unknown_context()
            source = "cache_after_vlm_failure" if state["cached_context"] is not None else "unavailable"
            return {"context": {**context, "source": source}, "gemini_called": True,
                    "retry_after": state["timestamp"] + self.failure_cooldown,
                    "errors": state["errors"] + [f"gemini:{type(exc).__name__}"]}

    def _fuse(self, state):
        status = "degraded" if state["errors"] else "ok"
        observation = {
            "timestamp": state["timestamp"], "ppe": state["ppe"],
            "context": state["context"], "zone": state["zone"],
            "confidence": {"ppe": state["ppe"]["confidence"], "context": state["context"]["confidence"],
                           "zone": None, "overall": None},
            "status": status, "errors": state["errors"], "gemini_called": state["gemini_called"],
            "context_timestamp": state["cache_timestamp"],
        }
        return {"observation": observation, "status": status}

    @staticmethod
    def _stamp(timestamp):
        return f"{int(timestamp) // 60:02d}:{int(timestamp) % 60:02d}"

    def process_frame(self, frame, timestamp):
        timestamp = float(timestamp)
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("timestamp must be finite, non-negative seconds")
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
            raise ValueError("Expected a non-empty BGR OpenCV frame")
        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            self.reset_cache()

        cooling = (self._memory["retry_after"] is not None
                   and timestamp < self._memory["retry_after"])
        force_vlm = self._pending_force_vlm and not cooling
        if force_vlm:
            self._pending_force_vlm = False
        was_in_violation = self._was_in_violation

        state = self.graph.invoke({
            **deepcopy(self._memory),
            "frame": frame,
            "timestamp": timestamp,
            "errors": [],
            "gemini_called": False,
            "force_vlm": force_vlm,
        })
        self._memory = {key: deepcopy(state[key]) for key in self._memory}
        self._last_timestamp = timestamp

        current_violation = bool(state.get("zone", {}).get("violation"))
        if not current_violation:
            self._pending_force_vlm = False
        elif not was_in_violation:
            LOG.info("[%s] Zone violation STARTED - forcing VLM refresh next frame",
                     self._stamp(timestamp))
            self._pending_force_vlm = True
        self._was_in_violation = current_violation

        if timestamp - self._last_log >= self.log_interval:
            LOG.info("[%s] PPE %s; context=%s; zone=%s; status=%s", self._stamp(timestamp),
                     "failed" if any(e.startswith("ppe:") for e in state["errors"]) else "detection complete",
                     state["context"]["source"], state["zone"]["violation"], state["status"])
            self._last_log = timestamp

        return state["observation"]