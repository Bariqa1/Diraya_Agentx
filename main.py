"""Run with python main.py from the repository root."""
import json
import logging
import math
import textwrap

import cv2

from agents import ContextAgent
from config import Config
from tools.gemini_context import GeminiContextTool
from tools.ppe_detector import PPEDetector
from tools.zone_monitor import ZoneMonitor

LOG = logging.getLogger(__name__)


def annotate(frame, observation, ppe_detector, zone_monitor):
    frame = frame.copy()
    ppe_detector.annotate(frame, observation["ppe"])
    zone_monitor.annotate(frame, observation["zone"])
    context = observation["context"]
    lines = [f"Task: {context['task']}",
             f"Zone Violation: {observation['zone']['violation']}"]
    y = 20
    for line in lines:
        for part in textwrap.wrap(line, max(15, int(frame.shape[1] / 8))):
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 0, 0), 3)
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1)
            y += 19
    return frame


def process_video(config, agent, ppe_detector, zone_monitor):
    capture = cv2.VideoCapture(str(config.input_video))
    writer = None
    count = 0
    try:
        if not capture.isOpened():
            raise ValueError(f"Cannot open video: {config.input_video}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        width, height = (int(capture.get(prop)) for prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT))
        if not math.isfinite(fps) or fps <= 0 or width <= 0 or height <= 0:
            raise ValueError("Video has invalid FPS or dimensions")
        if width % 2 or height % 2:
            raise ValueError("MP4 demo requires even video width and height to avoid codec cropping")
        if config.input_video.resolve() == config.output_video.resolve():
            raise ValueError("Output must not overwrite input video")
        config.output_video.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(config.output_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError("Cannot open MP4 writer; check codec and output path")
        LOG.info("Video: %.2f FPS, %dx%d", fps, width, height)
        next_json = 0.0
        with config.output_video.with_suffix(".jsonl").open("w", encoding="utf-8") as stream:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                timestamp = count / fps
                observation = agent.process_frame(frame, timestamp)
                stream.write(json.dumps(observation, ensure_ascii=False, allow_nan=False) + "\n")
                writer.write(annotate(frame, observation, ppe_detector, zone_monitor))
                if timestamp >= next_json:
                    LOG.info("Unified context: %s", json.dumps(observation, ensure_ascii=False, allow_nan=False))
                    next_json = timestamp + config.json_interval
                count += 1
        if not count:
            raise ValueError("Video contains no decodable frames")
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
        zone = ZoneMonitor(config.person_model, config.restricted_zone, config.person_threshold)
        context_tool = GeminiContextTool(config.api_key, config.gemini_model, config.max_retries)
        agent = ContextAgent(ppe, context_tool, zone, config.cache_ttl, config.failure_cooldown, config.log_interval)
        process_video(config, agent, ppe, zone)
    except (ValueError, RuntimeError, OSError) as exc:
        LOG.error("Cannot run demo: %s", exc)
        return 1
    finally:
        if context_tool is not None:
            context_tool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
