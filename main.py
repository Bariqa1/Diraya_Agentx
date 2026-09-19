"""Run with python main.py from the repository root."""
import json
import logging
import math
import os
import textwrap

import cv2

from agents import ComplianceAgent, ContextAgent
from config import Config
from tools.alert_handlers import beep_handler, console_handler
from tools.alert_manager import AlertManager
from tools.gemini_context import GeminiContextTool
from tools.fall_detector import FallDetector
from tools.manual_rules import ManualRules
from tools.ppe_detector import PPEDetector
from tools.zone_monitor import ZoneMonitor
from tools.sign_hazard_monitor import SignHazardMonitor

LOG = logging.getLogger(__name__)


def annotate(frame, observation, ppe_detector, zone_monitor, fall_detector, sign_monitor=None):
    frame = frame.copy()
    if sign_monitor is not None:
        sign_violations = observation.get("sign_violations", [])
        frame = sign_monitor.annotate(frame, violations=sign_violations)
    if observation["person_detected"]:
        ppe_detector.annotate(frame, observation["ppe"])
    zone_monitor.annotate(frame, observation["zone"])
    if observation["person_detected"]:
        fall_detector.annotate(frame, observation["fall"])
    context = observation["context"]
    compliance = observation.get("compliance", {})
    alert_sent = observation.get("alert_sent", False)
    severity = compliance.get("severity", "N/A")

    is_zone_violation = bool(observation.get("zone", {}).get("violation") or observation.get("sign_violations"))

    lines = [
        f"Person Detected: {observation['person_detected']}",
        f"Task: {context['task']}",
        f"Severity: {severity}",
        f"Missing PPE: {', '.join(compliance.get('missing_ppe', [])) or 'none'}",
        f"Zone Violation: {is_zone_violation}",
        f"Fall Detected: {observation['fall']['detected']}",
        f"Alert Sent: {alert_sent}",
    ]
    if observation.get("sign_violations"):
        lines.append(f"Sign Breaches: {len(observation['sign_violations'])} active")

    color = (0, 220, 0) if severity == "SAFE" else ((0, 165, 255) if severity == "WARNING" else (0, 0, 255))
    y = 20
    for line in lines:
        if "Zone Violation: True" in line:
            line_color = (0, 0, 255)
        elif any(k in line for k in ("Severity:", "Missing PPE:", "Alert Sent:", "Sign Breaches:")):
            line_color = color
        else:
            line_color = (255, 255, 255)
        for part in textwrap.wrap(line, max(15, int(frame.shape[1] / 8))):
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 0, 0), 3)
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, .45, line_color, 1)
            y += 19
    return frame


def process_video(config, agent, ppe_detector, zone_monitor, fall_detector, compliance, alert_manager, sign_monitor=None):
    capture = cv2.VideoCapture(str(config.input_video))
    writer = None
    count = 0
    try:
        if not capture.isOpened():

            raise ValueError(f"Cannot open video: {config.input_video}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        source_width, source_height = (
            int(capture.get(prop))
            for prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT)
        )
        width, height = config.processing_width, config.processing_height
        if not math.isfinite(fps) or fps <= 0 or source_width <= 0 or source_height <= 0:
            raise ValueError("Video has invalid FPS or dimensions")
        if config.input_video.resolve() == config.output_video.resolve():
            raise ValueError("Output must not overwrite input video")
        config.output_video.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(config.output_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError("Cannot open MP4 writer; check codec and output path")
        LOG.info("Video: %.2f FPS, source=%dx%d, processing=%dx%d",
                 fps, source_width, source_height, width, height)
        next_json = 0.0
        with config.output_video.with_suffix(".jsonl").open("w", encoding="utf-8") as stream:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                timestamp = count / fps

                # Auto-scan signs on frame 0 if requested or signs cache is empty
                if count == 0 and sign_monitor is not None:
                    if os.getenv("RESCAN_SIGNS", "false").lower() == "true" or not sign_monitor.signs:
                        try:
                            sign_monitor.scan_frame_with_vlm(frame, force_rescan=True)
                        except Exception as exc:
                            LOG.warning("Signboard initial scan error: %s", exc)
                    if sign_monitor.signs and hasattr(zone_monitor, "set_dynamic_polygons"):
                        zone_monitor.set_dynamic_polygons([
                            s["hazard_polygon"] for s in sign_monitor.signs if s.get("hazard_polygon") is not None
                        ])

                observation = agent.process_frame(frame, timestamp)

                # 4) Sign Hazard & RBAC perimeter check
                if sign_monitor is not None and observation.get("zone", {}).get("persons"):
                    observation["sign_violations"] = sign_monitor.evaluate_persons(observation["zone"]["persons"])
                else:
                    observation["sign_violations"] = []

                # Unify sign hazard breaches into Zone Violation
                if observation.get("sign_violations"):
                    observation.setdefault("zone", {})["violation"] = True
                    breached_pids = {v["person_id"] for v in observation["sign_violations"]}
                    for p in observation["zone"].get("persons", []):
                        if p.get("track_id") in breached_pids:
                            p["inside_restricted_zone"] = True
                    for p in observation.get("persons", []):
                        if p.get("track_id") in breached_pids:
                            p["inside_restricted_zone"] = True

                decision = observation.get("compliance") or {"alert": False}

                # Escalate compliance alert if sign perimeter breached
                if observation.get("sign_violations"):
                    decision["alert"] = True
                    decision["zone_violation"] = True
                    if decision.get("severity") != "CRITICAL":
                        has_critical = any(v.get("severity") == "CRITICAL" for v in observation["sign_violations"])
                        if has_critical:
                            decision["severity"] = "CRITICAL"
                    reasons = decision.setdefault("reasons", [])
                    if not any(r.get("code") == "zone_violation" for r in reasons):
                        reasons.insert(0, {
                            "code": "zone_violation",
                            "text": "Worker inside restricted safety perimeter (Sign Hazard Zone)",
                            "severity": "CRITICAL",
                        })
                    for v in observation["sign_violations"]:
                        reasons.append({
                            "code": "signboard_perimeter_breach",
                            "text": v["alert_message"],
                            "severity": v["severity"],
                            "sign_id": v["sign_id"],
                            "sign_text": v["sign_text"],
                        })

                if alert_manager.should_alert(decision):
                    decision = compliance.explain(decision)
                alert_event = alert_manager.process(
                    decision=decision, frame_id=f"f_{count:05d}")
                if observation["person_detected"]:
                    observation["compliance"] = decision
                observation["alert_sent"] = alert_event is not None

                # 5) Save
                stream.write(json.dumps(observation, ensure_ascii=False, allow_nan=False) + "\n")
                writer.write(annotate(frame, observation, ppe_detector, zone_monitor, fall_detector, sign_monitor))

                if timestamp >= next_json:
                    LOG.info("Unified compliance state: %s", json.dumps(observation, ensure_ascii=False, allow_nan=False))
                    next_json = timestamp + config.json_interval
                count += 1
        if not count:
            raise ValueError("Video contains no decodable frames")

        # Summary stats
        stats = alert_manager.stats()
        LOG.info("=== ALERT MANAGER STATS ===")
        LOG.info("Total Alerts Sent: %d | Unique Signatures: %d",
                 stats["total_alerts_sent"], stats["unique_signatures"])
    finally:
        capture.release()
        if writer is not None:
            writer.release()
    check = cv2.VideoCapture(str(config.output_video))
    try:
        ok, _ = check.read()
        if not ok:
            raise RuntimeError("Output video could not be decoded")
    finally:
        check.release()
    LOG.info("Saved %d frames to %s and %s", count, config.output_video, config.output_video.with_suffix(".jsonl"))
    return count


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    context_tool = None
    try:
        config = Config.from_env()
        config.validate_inputs()
        ppe = PPEDetector(config.ppe_model, config.ppe_threshold, device=config.device)
        fall = FallDetector(config.fall_model, config.fall_threshold, device=config.device)
        zone = ZoneMonitor(config.person_model, config.restricted_zone, config.person_threshold, device=config.device)
        context_tool = GeminiContextTool(config.api_key, config.gemini_model, config.max_retries)
        rules = ManualRules()
        compliance = ComplianceAgent(
            rules=rules,
            ppe_conf_threshold=config.ppe_threshold,
            llm_client=context_tool.client if context_tool else None,
            llm_model=config.gemini_model,
        )
        agent = ContextAgent(ppe, context_tool, zone, fall, compliance,
                             config.cache_ttl, config.failure_cooldown, config.log_interval)
        alert_manager = AlertManager(
            dedup_window_sec=30.0,
            throttle_window_sec=60.0,
            max_alerts_per_window=5,
            alerts_log_path=config.output_video.parent / "alerts.jsonl",
            handlers={
                "console": console_handler,
                "beep": beep_handler,
            },
            zone=config.facility_zone,
        )
        sign_monitor = SignHazardMonitor()
        if sign_monitor.signs and hasattr(zone, "set_dynamic_polygons"):
            zone.set_dynamic_polygons([s["hazard_polygon"] for s in sign_monitor.signs if s.get("hazard_polygon") is not None])
        process_video(config, agent, ppe, zone, fall, compliance, alert_manager, sign_monitor=sign_monitor)

    except (ValueError, RuntimeError, OSError) as exc:
        LOG.error("Cannot run demo: %s", exc)
        return 1
    finally:
        if context_tool is not None:
            context_tool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
