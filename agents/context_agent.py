from copy import deepcopy
import logging
import math
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from config import positive
from tools.gemini_context import unknown_context

LOG = logging.getLogger(__name__)


class ContextState(TypedDict, total=False):
    frame: Any
    timestamp: float
    persons: list[dict]
    person_detected: bool
    ppe: dict
    fall: dict
    zone: dict
    context: dict
    cached_context: dict | None
    cache_timestamp: float | None
    retry_after: float | None
    gemini_called: bool
    force_vlm: bool
    route: str
    errors: Annotated[list[str], operator.add]
    status: str
    observation: dict


class ContextAgent:
    """Tracked-person-gated LangGraph perception and compliance workflow."""

    def __init__(self, ppe_detector, context_tool, zone_monitor, fall_detector=None,
                 compliance_agent=None, cache_ttl=30, failure_cooldown=5, log_interval=1):
        self.ppe_detector = ppe_detector
        self.context_tool = context_tool
        self.zone_monitor = zone_monitor
        self.fall_detector = fall_detector
        self.compliance_agent = compliance_agent
        self.cache_ttl = positive(cache_ttl, "cache_ttl")
        self.failure_cooldown = positive(failure_cooldown, "failure_cooldown")
        self.log_interval = positive(log_interval, "log_interval")
        self.reset_cache()

        context_graph = StateGraph(ContextState)
        context_graph.add_node("check_cache", self._check)
        context_graph.add_node("use_cache", self._cached)
        context_graph.add_node("gemini", self._gemini)
        context_graph.add_edge(START, "check_cache")
        context_graph.add_conditional_edges(
            "check_cache", lambda state: state["route"],
            {"cache": "use_cache", "vlm": "gemini"},
        )
        context_graph.add_edge("use_cache", END)
        context_graph.add_edge("gemini", END)
        self.context_graph = context_graph.compile()

        graph = StateGraph(ContextState)
        for name, node in (
            ("person_tracking", self._persons), ("no_person", self._no_person),
            ("context_resolution", self.context_graph),
            ("ppe_detection", self._ppe),
            ("fall_detection", self._fall), ("zone_monitoring", self._zone),
            ("fusion", self._fuse), ("compliance", self._compliance),
        ):
            graph.add_node(name, node)

        graph.add_edge(START, "person_tracking")
        graph.add_conditional_edges(
            "person_tracking",
            self._route_after_person_tracking,
            {"context": "context_resolution", "ppe": "ppe_detection",
             "fall": "fall_detection", "zone": "zone_monitoring",
             "empty": "no_person"},
        )
        graph.add_edge("no_person", END)
        graph.add_edge(
            ["context_resolution", "ppe_detection", "fall_detection", "zone_monitoring"],
            "fusion",
        )
        graph.add_edge("fusion", "compliance")
        graph.add_edge("compliance", END)
        self.graph = graph.compile()

    def reset_cache(self):
        self._memory = dict(cached_context=None, cache_timestamp=None, retry_after=None)
        self._last_timestamp = None
        self._last_log = -math.inf
        self._was_in_violation = False
        self._pending_force_vlm = False

    def _persons(self, state):
        try:
            persons = self.zone_monitor.detect_people(state["frame"])
            return {"persons": persons, "person_detected": bool(persons)}
        except Exception as exc:
            return {"persons": [], "person_detected": False,
                    "errors": [f"person:{type(exc).__name__}"]}

    @staticmethod
    def _route_after_person_tracking(state):
        """Fan out four branches for a tracked person, or skip the frame."""
        if not state["person_detected"]:
            return "empty"
        return ["context", "ppe", "fall", "zone"]

    def _no_person(self, state):
        status = "degraded" if state["errors"] else "no_person"
        observation = {
            "timestamp": state["timestamp"], "person_detected": False, "persons": [],
            "ppe": {"detections": [], "confidence": None},
            "fall": {"detected": False, "detections": [], "confidence": None},
            "context": {**unknown_context(), "source": "skipped_no_person"},
            "zone": {"persons": [], "violation": False},
            "confidence": {"ppe": None, "fall": None, "context": 0.0,
                           "zone": None, "overall": None},
            "status": status, "errors": state["errors"], "gemini_called": False,
            "context_timestamp": state["cache_timestamp"], "compliance": None,
        }
        return {"observation": observation, "status": status}

    def _ppe(self, state):
        try:
            return {"ppe": self.ppe_detector.detect(state["frame"])}
        except Exception as exc:
            return {"ppe": {"detections": [], "confidence": None},
                    "errors": [f"ppe:{type(exc).__name__}"]}

    def _fall(self, state):
        if self.fall_detector is None:
            return {"fall": {"detected": False, "detections": [], "confidence": None}}
        try:
            return {"fall": self.fall_detector.detect(state["frame"])}
        except Exception as exc:
            return {"fall": {"detected": False, "detections": [], "confidence": None},
                    "errors": [f"fall:{type(exc).__name__}"]}

    def _zone(self, state):
        try:
            return {"zone": self.zone_monitor.evaluate_zone(state["persons"])}
        except Exception as exc:
            return {"zone": {"persons": state["persons"], "violation": None},
                    "errors": [f"zone:{type(exc).__name__}"]}

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
        source = ("unavailable" if state["cached_context"] is None else
                  "cache_after_vlm_failure" if failed else "cache")
        result = {"context": {**context, "source": source}}
        if failed:
            result["errors"] = ["gemini:failure_cooldown"]
        return result

    def _gemini(self, state):
        try:
            context = self.context_tool.analyze(state["frame"])
            LOG.info("[%s] Gemini context: %s", self._stamp(state["timestamp"]), context["task"])
            return {"context": {**context, "source": "gemini"},
                    "cached_context": deepcopy(context), "cache_timestamp": state["timestamp"],
                    "retry_after": None, "gemini_called": True}
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
                    "errors": [f"gemini:{type(exc).__name__}"]}

    def _fuse(self, state):
        status = "degraded" if state["errors"] else "ok"
        observation = {
            "timestamp": state["timestamp"], "person_detected": True,
            "persons": state["persons"], "ppe": state["ppe"], "fall": state["fall"],
            "context": state["context"], "zone": state["zone"],
            "confidence": {"ppe": state["ppe"]["confidence"],
                           "fall": state["fall"]["confidence"],
                           "context": state["context"]["confidence"],
                           "zone": None, "overall": None},
            "status": status, "errors": state["errors"],
            "gemini_called": state["gemini_called"],
            "context_timestamp": state["cache_timestamp"],
        }
        return {"observation": observation, "status": status}

    def _compliance(self, state):
        observation = state["observation"]
        if self.compliance_agent is not None:
            observation = {**observation, "compliance": self.compliance_agent.evaluate(observation)}
        return {"observation": observation}

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

        cooling = self._memory["retry_after"] is not None and timestamp < self._memory["retry_after"]
        force_vlm = self._pending_force_vlm and not cooling
        if force_vlm:
            self._pending_force_vlm = False
        was_in_violation = self._was_in_violation
        state = self.graph.invoke({**deepcopy(self._memory), "frame": frame,
                                   "timestamp": timestamp, "errors": [],
                                   "gemini_called": False, "force_vlm": force_vlm})
        self._memory = {key: deepcopy(state[key]) for key in self._memory}
        self._last_timestamp = timestamp

        current_violation = bool(state.get("zone", {}).get("violation"))
        if not current_violation:
            self._pending_force_vlm = False
        elif not was_in_violation:
            LOG.info("[%s] Zone violation STARTED - forcing VLM refresh next frame", self._stamp(timestamp))
            self._pending_force_vlm = True
        self._was_in_violation = current_violation

        if timestamp - self._last_log >= self.log_interval:
            if state["person_detected"]:
                LOG.info("[%s] persons=%d; PPE complete; fall=%s; context=%s; zone=%s; status=%s",
                         self._stamp(timestamp), len(state["persons"]), state["fall"]["detected"],
                         state["context"]["source"], state["zone"]["violation"], state["status"])
            else:
                LOG.info("[%s] no person detected; remaining graph skipped", self._stamp(timestamp))
            self._last_log = timestamp
        return state["observation"]
