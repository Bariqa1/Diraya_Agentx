"""
Batch processor for 4 live monitoring cameras in Diraya.
Cam-01 has the Signboard & Demolition Perimeter (Video 7).
Cam-02, Cam-03, Cam-04 do NOT have signboards; they only show accurate person tracking & PPE detection.
"""
import json
import logging
import math
import os
import sys
import textwrap
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics.engine.results import Results

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.compliance_agent import ComplianceAgent
from config import Config, resolve
from tools.fall_detector import FallDetector
from tools.manual_rules import ManualRules
from tools.ppe_detector import PPEDetector
from tools.sign_hazard_monitor import SignHazardMonitor
from tools.zone_monitor import ZoneMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOG = logging.getLogger("process_cameras")

CAMERAS_CONFIG = [
    {
        "id": "cam-01",
        "name_ar": "الكاميرا 01 — ورشة اللحام والقص",
        "name_en": "Camera 01 — Welding & Cutting Bay",
        "zone": "ZONE_WELDING",
        "zone_title_ar": "ورشة اللحام",
        "zone_title_en": "Welding Bay",
        "input_video": "video_test/video_test7.mp4",
        "existing_output": "outputs/video_test7_output.mp4",
        "existing_jsonl": "outputs/video_test7_output.jsonl",
        "output_video": "frontend/public/videos/cam1.mp4",
        "output_jsonl": "outputs/video_test7_output.jsonl",
        "task_name": "welding",
        "fps_target": 30.0,
        "has_signs": True,
    },
    {
        "id": "cam-02",
        "name_ar": "الكاميرا 02 — منطقة العمل والارتفاعات",
        "name_en": "Camera 02 — Working at Height & Scaffold",
        "zone": "ZONE_HEIGHT",
        "zone_title_ar": "منطقة الارتفاعات",
        "zone_title_en": "Height Operations",
        "input_video": "video_test/video_test4.mp4",
        "output_video": "frontend/public/videos/cam2.mp4",
        "output_jsonl": "outputs/video_test4_output.jsonl",
        "task_name": "working_at_height",
        "fps_target": 30.0,
        "has_signs": False,
    },
    {
        "id": "cam-03",
        "name_ar": "الكاميرا 03 — مستودع التخزين ومحيط الخطر",
        "name_en": "Camera 03 — Chemical Storage & Hazard Zone",
        "zone": "ZONE_STORAGE",
        "zone_title_ar": "مستودع الكيماويات",
        "zone_title_en": "Chemical Storage",
        "input_video": "video_test/video_test5.mp4",
        "output_video": "frontend/public/videos/cam3.mp4",
        "output_jsonl": "outputs/video_test5_output.jsonl",
        "task_name": "operating_machinery",
        "fps_target": 25.0,
        "has_signs": False,
    },
    {
        "id": "cam-04",
        "name_ar": "الكاميرا 04 — محطة التشغيل والرافعات الثقيلة",
        "name_en": "Camera 04 — Crane Operations & Heavy Bay",
        "zone": "ZONE_CRANE",
        "zone_title_ar": "نطاق عمل الرافعة",
        "zone_title_en": "Heavy Crane Bay",
        "input_video": "video_test/video_test6.mp4",
        "output_video": "frontend/public/videos/cam4.mp4",
        "output_jsonl": "outputs/video_test6_output.jsonl",
        "task_name": "operating_machinery",
        "fps_target": 25.0,
        "frame_step": 2,  # sample 50fps down to 25fps for clean loop
        "has_signs": False,
    },
]


def annotate_camera(frame, observation, ppe_detector, zone_monitor, fall_detector, sign_monitor=None):
    """
    Renders clean, camera-specific annotations.
    Does NOT draw artificial fixed polygons from other clips.
    """
    frame = frame.copy()

    # 1. Sign hazard monitor (ONLY if present on this specific camera)
    if sign_monitor is not None and getattr(sign_monitor, "signs", None):
        sign_violations = observation.get("sign_violations", [])
        frame = sign_monitor.annotate(frame, violations=sign_violations)

    # 2. PPE detections (Helmet, Vest, Gloves, etc.)
    if observation.get("person_detected") and observation.get("ppe"):
        frame = ppe_detector.annotate(frame, observation["ppe"])

    # 3. Person tracking bounding boxes (without fixed arbitrary polygon)
    persons = observation.get("zone", {}).get("persons", [])
    if persons:
        try:
            boxes = torch.tensor([
                [*p["bbox"], p.get("confidence", 0.85), zone_monitor.person_id]
                for p in persons
            ], dtype=torch.float32)
            res = Results(orig_img=frame, path="", names=zone_monitor.model.names, boxes=boxes)
            frame[:] = res.plot()
        except Exception:
            pass

    # 4. Fall detection
    if observation.get("person_detected") and observation.get("fall"):
        frame = fall_detector.annotate(frame, observation["fall"])

    # 5. Top-left HUD status lines
    context = observation.get("context", {})
    compliance = observation.get("compliance", {})
    severity = compliance.get("severity", "SAFE")
    alert_sent = observation.get("alert_sent", False)
    missing_ppe = compliance.get("missing_ppe", [])

    lines = [
        f"Person Detected: {observation.get('person_detected', False)}",
        f"Task: {context.get('task', 'N/A')}",
        f"Severity: {severity}",
        f"Missing PPE: {', '.join(missing_ppe) or 'none'}",
        f"Fall Detected: {observation.get('fall', {}).get('detected', False)}",
        f"Alert Sent: {alert_sent}",
    ]
    if observation.get("sign_violations"):
        lines.append(f"Sign Breaches: {len(observation['sign_violations'])} active")

    color = (0, 220, 0) if severity == "SAFE" else ((0, 165, 255) if severity == "WARNING" else (0, 0, 255))
    y = 20
    for line in lines:
        line_color = color if any(k in line for k in ("Severity:", "Missing PPE:", "Alert Sent:", "Sign Breaches:")) else (255, 255, 255)
        for part in textwrap.wrap(line, max(15, int(frame.shape[1] / 8))):
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
            cv2.putText(frame, part, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, line_color, 1)
            y += 19

    return frame


def process_camera_stream(
    cam_cfg: dict,
    ppe_detector: PPEDetector,
    zone_monitor: ZoneMonitor,
    fall_detector: FallDetector,
    compliance_agent: ComplianceAgent,
    sign_monitor: SignHazardMonitor,
):
    target_mp4 = ROOT / cam_cfg["output_video"]
    target_jsonl = ROOT / cam_cfg["output_jsonl"]
    target_mp4.parent.mkdir(parents=True, exist_ok=True)
    target_jsonl.parent.mkdir(parents=True, exist_ok=True)

    # If this camera doesn't have signs, do not pass sign_monitor
    effective_sign_monitor = sign_monitor if cam_cfg.get("has_signs") else None

    # Cam 1 is already pre-processed
    if cam_cfg.get("existing_output") and (ROOT / cam_cfg["existing_output"]).exists() and target_mp4.exists():
        LOG.info("%s is ready using pre-processed source.", cam_cfg["id"])
        return

    input_path = ROOT / cam_cfg["input_video"]
    if not input_path.exists():
        LOG.error("Input video not found: %s", input_path)
        return

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        LOG.error("Cannot open %s", input_path)
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    source_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_step = cam_cfg.get("frame_step", 1)
    target_fps = fps / frame_step

    out_w, out_h = 1280, 720
    writer = cv2.VideoWriter(str(target_mp4), cv2.VideoWriter_fourcc(*"avc1"), target_fps, (out_w, out_h))
    if not writer.isOpened():
        writer = cv2.VideoWriter(str(target_mp4), cv2.VideoWriter_fourcc(*"mp4v"), target_fps, (out_w, out_h))

    LOG.info("Processing %s without extraneous signs: %s (fps=%.1f -> %.1f, %dx%d -> %dx%d)",
             cam_cfg["id"], input_path.name, fps, target_fps, source_w, source_h, out_w, out_h)

    task_name = cam_cfg["task_name"]
    raw_idx = 0
    written_count = 0

    with target_jsonl.open("w", encoding="utf-8") as stream:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            raw_idx += 1
            if raw_idx % frame_step != 0:
                continue

            frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
            timestamp = written_count / target_fps

            # 1) People detection & tracking
            persons_list = zone_monitor.detect_people(frame)
            person_detected = bool(persons_list)

            # 2) PPE detection
            ppe_result = ppe_detector.detect(frame)

            # 3) Fall detection
            fall_result = fall_detector.detect(frame) if person_detected else {"detected": False, "score": 0.0, "detections": []}

            # 4) Zone evaluation (no artificial violation if has_signs is False)
            zone_result = {"persons": persons_list, "violation": False}

            # 5) Sign hazard evaluation (only for Cam 1)
            sign_violations = []
            if effective_sign_monitor and persons_list:
                sign_violations = effective_sign_monitor.evaluate_persons(persons_list)
                if sign_violations:
                    zone_result["violation"] = True

            # 6) Compliance determination
            compliance_input = {
                "context": {"task": task_name, "confidence": 0.95},
                "person_detected": person_detected,
                "ppe": ppe_result,
                "fall": fall_result,
                "zone": zone_result,
            }
            compliance_decision = compliance_agent.evaluate(compliance_input)

            # Build observation
            observation = {
                "timestamp": round(timestamp, 3),
                "camera_id": cam_cfg["id"],
                "zone": cam_cfg["zone"],
                "person_detected": person_detected,
                "ppe": ppe_result,
                "zone_info": zone_result,
                "fall": fall_result,
                "sign_violations": sign_violations,
                "context": {"task": task_name},
                "compliance": compliance_decision,
                "alert_sent": compliance_decision.get("alert", False),
            }

            stream.write(json.dumps(observation, ensure_ascii=False) + "\n")

            # Annotate visually WITHOUT the fixed signboard from other clips
            annotated_frame = annotate_camera(
                frame,
                {
                    "person_detected": person_detected,
                    "ppe": ppe_result,
                    "zone": zone_result,
                    "fall": fall_result,
                    "sign_violations": sign_violations,
                    "context": {"task": task_name},
                    "compliance": compliance_decision,
                    "alert_sent": compliance_decision.get("alert", False),
                },
                ppe_detector,
                zone_monitor,
                fall_detector,
                effective_sign_monitor,
            )
            writer.write(annotated_frame)
            written_count += 1

    cap.release()
    writer.release()
    LOG.info("Completed %s: %d clean frames written to %s", cam_cfg["id"], written_count, target_mp4)


def build_unified_telemetry():
    """Build unified JSON telemetry file for the frontend live monitoring ticker."""
    all_events = []

    for cam in CAMERAS_CONFIG:
        jsonl_path = ROOT / cam["output_jsonl"]
        if not jsonl_path.exists():
            continue

        with jsonl_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                compliance = data.get("compliance", {})
                severity = compliance.get("severity", "SAFE")
                missing_ppe = compliance.get("missing_ppe", [])
                is_fall = data.get("fall", {}).get("detected", False)
                is_zone = bool(data.get("zone_info", {}).get("violation") or data.get("sign_violations"))

                if idx % 15 == 0 or severity in ("CRITICAL", "WARNING"):
                    event_ar = "المنطقة آمنة ومطابقة"
                    event_en = "Zone compliant & safe"
                    if is_fall:
                        event_ar = "🚨 رصد حالة سقوط محتملة لعامل!"
                        event_en = "🚨 Potential worker fall detected!"
                    elif is_zone:
                        event_ar = "⚠️ تجاوز واختراق لمحيط منطقة الخطر!"
                        event_en = "⚠️ Perimeter breach in hazard zone!"
                    elif missing_ppe:
                        event_ar = f"⚠️ عدم ارتداء معدات وقاية: {', '.join(missing_ppe)}"
                        event_en = f"⚠️ Missing PPE: {', '.join(missing_ppe)}"

                    all_events.append({
                        "id": f"{cam['id']}-{idx}",
                        "cameraId": cam["id"],
                        "cameraName": {
                            "ar": cam["name_ar"],
                            "en": cam["name_en"],
                        },
                        "zone": cam["zone"],
                        "zoneTitle": {
                            "ar": cam["zone_title_ar"],
                            "en": cam["zone_title_en"],
                        },
                        "timestamp": data.get("timestamp", idx * 0.033),
                        "severity": severity.lower(),
                        "missingPpe": missing_ppe,
                        "personDetected": data.get("person_detected", False),
                        "fallDetected": is_fall,
                        "zoneViolation": is_zone,
                        "message": {
                            "ar": event_ar,
                            "en": event_en,
                        },
                    })

    all_events.sort(key=lambda x: x["timestamp"])

    out_file = ROOT / "frontend" / "src" / "data" / "camera-telemetry.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(all_events, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.info("Saved %d unified telemetry events to %s", len(all_events), out_file)


def main():
    LOG.info("Initializing models for clean camera processing...")
    config = Config.from_env()
    ppe = PPEDetector(config.ppe_model, config.ppe_threshold, device=config.device)
    fall = FallDetector(config.fall_model, config.fall_threshold, device=config.device)
    zone = ZoneMonitor(config.person_model, config.restricted_zone, config.person_threshold, device=config.device)
    rules = ManualRules()
    compliance = ComplianceAgent(rules=rules, ppe_conf_threshold=config.ppe_threshold)
    sign_monitor = SignHazardMonitor()

    # Re-process cameras 2, 3, 4 without the extraneous signs
    for cam in CAMERAS_CONFIG:
        if cam["id"] == "cam-01":
            LOG.info("Cam-01 already has genuine signboards.")
            continue
        LOG.info("=== Processing Clean %s ===", cam["id"])
        process_camera_stream(cam, ppe, zone, fall, compliance, sign_monitor)

    build_unified_telemetry()
    LOG.info("All cameras cleaned and updated successfully!")


if __name__ == "__main__":
    main()
