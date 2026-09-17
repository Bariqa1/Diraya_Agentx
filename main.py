"""Run with python main.py from the repository root."""
import json
import logging
import math
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

LOG = logging.getLogger(__name__)


def annotate(frame, observation, ppe_detector, zone_monitor, fall_detector):
    frame = frame.copy()
    if observation["person_detected"]:
        ppe_detector.annotate(frame, observation["ppe"])
    zone_monitor.annotate(frame, observation["zone"])
    if observation["person_detected"]:
        fall_detector.annotate(frame, observation["fall"])
    context = observation["context"]
    compliance = observation.get("compliance", {})
    alert_sent = observation.get("alert_sent", False)
    severity = compliance.get("severity", "N/A")

    lines = [
        f"Person Detected: {observation['person_detected']}",
        f"Task: {context['task']}",
        f"Severity: {severity}",
        f"Missing PPE: {', '.join(compliance.get('missing_ppe', [])) or 'none'}",
        f"Zone Violation: {observation['zone']['violation']}",
        f"Fall Detected: {observation['fall']['detected']}",
        f"Alert Sent: {alert_sent}",
    ]

    color = (0, 220, 0) if severity == "SAFE" else ((0, 165, 255) if severity == "WARNING" else (0, 0, 255))
    y = 20
    for line in lines:
        line_color = color if any(k in line for k in ("Severity:", "Missing PPE:", "Alert Sent:")) else (255, 255, 255)
        for part in textwrap.wrap(line, max(15, int(frame.shape[1] / 8))):
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 0, 0), 3)
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, .45, line_color, 1)
            y += 19
    return frame


def process_video(config, agent, ppe_detector, zone_monitor, fall_detector, compliance, alert_manager):
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
                observation = agent.process_frame(frame, timestamp)
                decision = observation.get("compliance") or {"alert": False}
                if alert_manager.should_alert(decision):
                    decision = compliance.explain(decision)
                alert_event = alert_manager.process(
                    decision=decision, frame_id=f"f_{count:05d}")
                if observation["person_detected"]:
                    observation["compliance"] = decision
                observation["alert_sent"] = alert_event is not None

                # 5) Save
                stream.write(json.dumps(observation, ensure_ascii=False, allow_nan=False) + "\n")
                writer.write(annotate(frame, observation, ppe_detector, zone_monitor, fall_detector))

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
        ppe = PPEDetector(config.ppe_model, config.ppe_threshold)
        fall = FallDetector(config.fall_model, config.fall_threshold)
        zone = ZoneMonitor(config.person_model, config.restricted_zone, config.person_threshold)
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
        process_video(config, agent, ppe, zone, fall, compliance, alert_manager)
    except (ValueError, RuntimeError, OSError) as exc:
        LOG.error("Cannot run demo: %s", exc)
        return 1
    finally:
        if context_tool is not None:
            context_tool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
