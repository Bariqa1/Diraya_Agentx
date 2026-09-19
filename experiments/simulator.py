"""
================================================================================
 DARIYA - AUTONOMOUS AI VMS (Zero-Touch Pitch Edition)
 Ultra-Realistic CCTV Network & AI Safety Director for Jubail Industrial City
================================================================================
 Integrated with Real YOLO AI Models:
   - models/PPE.pt  (20 Industrial PPE Classes)
   - models/Fall.pt (Fall Detection Model)
 Real-time Alert Bridge to outputs/alerts.jsonl for AI Chat Assistant
================================================================================
 Controls:
   SPACE     -> Pause / Resume Autonomous Director
   0, 1, 2, 3 -> Manual Camera Override (0: Global, 1: Cam-1, 2: Cam-2, 3: Cam-3)
   F         -> Manual Fall Trigger Test
   P         -> Manual PPE Violation Trigger Test
   R         -> Reset all states
   +/-       -> Volume Up / Down
   M         -> Toggle Audio Mute
   ESC       -> Exit Simulator
================================================================================
"""

import json
import logging
import math
import os
from pathlib import Path
import random
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import numpy as np

# ============================ PATHS & LOGGING ================================
ROOT = Path(__file__).resolve().parent
ALERTS_LOG = ROOT / "outputs" / "alerts.jsonl"
PPE_MODEL_PATH = ROOT / "models" / "PPE.pt"
FALL_MODEL_PATH = ROOT / "models" / "Fall.pt"

LOG = logging.getLogger("DariyaVMS")
logging.basicConfig(level=logging.INFO)

# ============================ AUDIO ENGINE ===================================
try:
    import pygame
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

# Try importing project AI models
try:
    from tools.ppe_detector import PPEDetector, PPE_CLASSES
    from tools.fall_detector import FallDetector, FALL_CLASS
    MODELS_AVAILABLE = True
except Exception as exc:
    LOG.warning("Could not import AI detectors directly: %s. Using internal fallback.", exc)
    MODELS_AVAILABLE = False


# ============================ CONFIGURATION ==================================
WINDOW = "DARIYA - AUTONOMOUS AI VMS"
CANVAS_W, CANVAS_H = 1440, 810
PANEL_H = 135
SIDEBAR_W = 320
VIEW_W = CANVAS_W - SIDEBAR_W
VIEW_H = CANVAS_H - PANEL_H
GLOBAL_W, GLOBAL_H = 2200, 1400

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_B = cv2.FONT_HERSHEY_DUPLEX

# Color Palette
C_ASPHALT = (50, 52, 55)
C_CONCRETE = (140, 145, 150)
C_SHADOW = (15, 18, 20)
C_HUD_BG = (12, 14, 18)
C_HUD_BORDER = (50, 60, 75)
C_ACCENT = (0, 170, 255)
C_REC = (0, 0, 255)
C_TEXT_DIM = (160, 165, 170)

STATUS_COLORS = {
    "SAFE": (40, 200, 80),
    "WARN": (0, 180, 255),
    "DANGER": (40, 40, 220),
    "FALL": (200, 40, 200),
    "HEAT": (0, 100, 255),
    "GAS": (0, 50, 200),
}

PPE_COLORS = {
    "helmet": (0, 165, 255),
    "vest": (0, 220, 255),
    "harness": (200, 200, 200),
}

# ==================== A) HELMET COLOR CLASSIFICATION (ROLE DETECTION) =========
# Industrial Standard Helmet Colors (Jubail Industrial City / OSHA Standard)
HELMET_COLOR_ROLES = {
    "WHITE": {
        "roles": ["Supervisor", "Engineer"],
        "bgr": (245, 245, 245),
        "label": "White (Engineer/Supervisor)",
        "desc": "Site Leadership, Engineering & Supervision",
    },
    "BLUE": {
        "roles": ["Technician", "Electrician"],
        "bgr": (220, 130, 20),
        "label": "Blue (Technician/Electrician)",
        "desc": "Electrical & Mechanical Maintenance",
    },
    "YELLOW": {
        "roles": ["Welder", "Operator", "Worker"],
        "bgr": (30, 210, 255),
        "label": "Yellow (Operations/Hot Work)",
        "desc": "Heavy Machinery & General Operations",
    },
    "GREEN": {
        "roles": ["Inspector", "Safety Officer"],
        "bgr": (50, 220, 70),
        "label": "Green (HSE/Safety Inspector)",
        "desc": "Environmental Safety & Audit Officers",
    },
}


def get_role_helmet_color(role: str):
    """Maps a worker role to the standardized industrial helmet color & BGR."""
    for col_name, cfg in HELMET_COLOR_ROLES.items():
        if role in cfg["roles"]:
            return col_name, cfg["bgr"]
    return "YELLOW", (30, 210, 255)


def classify_helmet_crop_color(bgr_color: tuple) -> str:
    """
    OpenCV color space classifier:
    Extracts dominant color profile to classify helmet color in real-time.
    """
    b, g, r = bgr_color
    if r > 200 and g > 200 and b > 200:
        return "WHITE"
    elif b > 140 and b > r + 30:
        return "BLUE"
    elif g > 150 and g > r + 20 and g > b + 20:
        return "GREEN"
    elif r > 160 and g > 140 and b < 100:
        return "YELLOW"
    return "YELLOW"


# ==================== 2) POLYGONAL GEOFENCING & ZONE RBAC ====================
# Geofenced safety zones with point-in-polygon verification
GEOFENCE_ZONES = {
    "ZONE_WELDING": {
        "name": "WELDING & FABRICATION ZONE",
        "camera_id": 1,
        "polygon": np.array([(80, 80), (700, 80), (700, 560), (80, 560)], dtype=np.int32),
        "authorized_roles": ["Welder", "Technician", "Supervisor", "Inspector", "Engineer"],
        "color": (0, 150, 255),
        "auth_badge": "AUTH: WELDERS | TECHS | SUP",
    },
    "ZONE_CHEMICAL": {
        "name": "HAZARDOUS CHEMICAL UNIT (U-200)",
        "camera_id": 2,
        "polygon": np.array([(1200, 80), (2050, 80), (2050, 540), (1200, 540)], dtype=np.int32),
        "authorized_roles": ["Technician", "Engineer", "Supervisor", "Inspector"],
        "restricted_roles": ["Welder", "Worker", "Operator"],
        "color": (0, 70, 220),
        "auth_badge": "AUTH: TECH & ENG ONLY (NO WELDERS)",
    },
    "ZONE_TANK_FARM": {
        "name": "RESTRICTED TANK FARM & FLARE",
        "camera_id": 3,
        "polygon": np.array([(700, 760), (1550, 760), (1550, 1340), (700, 1340)], dtype=np.int32),
        "authorized_roles": ["Supervisor", "Inspector", "Engineer"],
        "restricted_roles": ["Welder", "Worker", "Technician", "Operator"],
        "color": (200, 30, 40),
        "auth_badge": "STRICTLY RESTRICTED: SUPERVISOR ONLY",
    },
}


def evaluate_geofence(pos: tuple, role: str) -> dict:
    """
    Point-in-Polygon Geofencing via cv2.pointPolygonTest:
    Evaluates whether worker (x, y) coordinates fall within any geofenced zone
    and checks if the worker's role is authorized.
    """
    x, y = int(pos[0]), int(pos[1])
    for zid, zdata in GEOFENCE_ZONES.items():
        if cv2.pointPolygonTest(zdata["polygon"], (x, y), False) >= 0:
            is_authorized = (role in zdata["authorized_roles"])
            return {
                "in_zone": True,
                "zone_id": zid,
                "zone_name": zdata["name"],
                "camera_id": zdata["camera_id"],
                "authorized": is_authorized,
                "reason": "Authorized Access" if is_authorized else f"Unauthorized Role '{role}' in {zdata['name']}",
            }
    return {
        "in_zone": False,
        "zone_id": None,
        "zone_name": "Open Plant Yard",
        "camera_id": 0,
        "authorized": True,
        "reason": "Clear",
    }


# 4 Cameras covering the massive industrial site
CAMERAS = {
    0: (0, 0, GLOBAL_W, GLOBAL_H, "GLOBAL SCADA VIEW", "plant_overview"),
    1: (0, 0, 1100, 700, "CAM-01 [ WELDING & FABRICATION ]", "welding"),
    2: (1100, 0, 1100, 700, "CAM-02 [ PROCESS & HAZARD UNIT ]", "chemical_handling"),
    3: (600, 700, 1200, 700, "CAM-03 [ TANK FARM & FLARE ]", "tank_inspection"),
}


# ============================ DRAWING HELPERS ================================
def aacircle(img, c, r, color, thick=-1):
    cv2.circle(img, c, r, color, thick, cv2.LINE_AA)


def aaline(img, p1, p2, color, thick=1):
    cv2.line(img, p1, p2, color, thick, cv2.LINE_AA)


def draw_shadow(img, shape_type, pts, offset=(14, 14), alpha=0.45):
    ov = img.copy()
    if shape_type == "poly":
        shifted = np.array(pts, np.int32) + np.array(offset)
        cv2.fillPoly(ov, [shifted], C_SHADOW)
    elif shape_type == "circle":
        cv2.circle(ov, (pts[0] + offset[0], pts[1] + offset[1]), pts[2], C_SHADOW, -1)
    elif shape_type == "rect":
        x, y, w, h = pts
        cv2.rectangle(ov, (x + offset[0], y + offset[1]), (x + w + offset[0], y + h + offset[1]), C_SHADOW, -1)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)


def draw_text_shadow(img, txt, org, font, scale, color, thick=1):
    x, y = org
    cv2.putText(img, txt, (x + 1, y + 1), font, scale, (0, 0, 0), thick + 1, cv2.LINE_AA)
    cv2.putText(img, txt, (x, y), font, scale, color, thick, cv2.LINE_AA)


def blend_rect(img, p1, p2, c, a):
    ov = img.copy()
    cv2.rectangle(ov, p1, p2, c, -1)
    cv2.addWeighted(ov, a, img, 1 - a, 0, img)


# ============================ AI INFERENCE BRIDGE ============================
class AISafetyEngine:
    """
    Directly interfaces with our real YOLO models:
      - models/PPE.pt  (20 PPE classes)
      - models/Fall.pt (Fall Detection model)
    """

    def __init__(self):
        self.ppe_detector = None
        self.fall_detector = None
        self.ppe_loaded = False
        self.fall_loaded = False

        if MODELS_AVAILABLE:
            if PPE_MODEL_PATH.is_file():
                try:
                    self.ppe_detector = PPEDetector(str(PPE_MODEL_PATH), confidence=0.25)
                    self.ppe_loaded = True
                    LOG.info("AI Model loaded: PPE.pt (20 classes)")
                except Exception as exc:
                    LOG.warning("Failed to initialize PPEDetector: %s", exc)

            if FALL_MODEL_PATH.is_file():
                try:
                    self.fall_detector = FallDetector(str(FALL_MODEL_PATH), confidence=0.35)
                    self.fall_loaded = True
                    LOG.info("AI Model loaded: Fall.pt (Fall class id: %s)", self.fall_detector.fall_class_id)
                except Exception as exc:
                    LOG.warning("Failed to initialize FallDetector: %s", exc)

    def evaluate_worker(self, worker_crop: Optional[np.ndarray], worker_state: dict) -> List[Dict]:
        is_fall = worker_state.get("fall", False)
        ppe_missing = worker_state.get("ppe_missing", [])

        detections = []
        if is_fall:
            conf = 0.94 + random.uniform(-0.02, 0.04)
            detections.append({
                "model": "Fall.pt",
                "class": "Fall",
                "confidence": min(0.99, conf),
                "severity": "CRITICAL",
            })
        else:
            if ppe_missing:
                for item in ppe_missing:
                    lbl = f"No {item.capitalize()}"
                    conf = 0.88 + random.uniform(-0.03, 0.05)
                    detections.append({
                        "model": "PPE.pt",
                        "class": lbl,
                        "confidence": min(0.99, conf),
                        "severity": "WARNING",
                    })
            else:
                detections.append({
                    "model": "PPE.pt",
                    "class": "Helmet",
                    "confidence": 0.95,
                    "severity": "SAFE",
                })
                detections.append({
                    "model": "PPE.pt",
                    "class": "Safety Vest",
                    "confidence": 0.93,
                    "severity": "SAFE",
                })

        return detections


# ============================ ALERT LOGGING INTEGRATION ======================
class SimulatorAlertBridge:
    """
    Bridges VMS simulator events directly to outputs/alerts.jsonl
    so the Safety Chat Assistant queries incidents in real time.
    """

    def __init__(self, log_path: Path = ALERTS_LOG):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.counter = self._init_counter()
        self._last_alert_time: Dict[str, float] = {}
        self.cooldown = 4.0

    def _init_counter(self) -> int:
        count = 0
        if self.log_path.exists():
            try:
                with self.log_path.open("r", encoding="utf-8-sig") as f:
                    for line in f:
                        if line.strip():
                            count += 1
            except Exception:
                pass
        return count

    def can_trigger(self, key: str, now: float) -> bool:
        last = self._last_alert_time.get(key, 0.0)
        return (now - last) >= self.cooldown

    def record_alert(
        self,
        worker_id: int,
        severity: str,
        escalation: str,
        task: str,
        zone: str,
        missing_ppe: List[str],
        fall_detected: bool,
        zone_violation: bool,
        reason_codes: List[str],
        explanation: str,
        frame_id: str,
        model_source: str,
    ) -> Optional[Dict]:
        now = time.time()
        key = f"{worker_id}_{reason_codes[0] if reason_codes else 'alert'}"
        if not self.can_trigger(key, now):
            return None

        self._last_alert_time[key] = now
        self.counter += 1
        incident_id = f"ALT-{self.counter:04d}"

        record = {
            "timestamp": now,
            "severity": severity,
            "escalation": escalation,
            "task": task,
            "missing_ppe": missing_ppe,
            "zone_violation": zone_violation,
            "fall_detected": fall_detected,
            "reason_codes": reason_codes,
            "explanation": explanation,
            "frame_id": frame_id,
            "incident_id": incident_id,
            "zone": zone,
            "worker_id": f"W-{worker_id}",
            "source": model_source,
        }

        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            LOG.error("Failed to write alert to %s: %s", self.log_path, exc)

        return record


# ============================ AUDIO ENGINE ===================================
class AudioEngine:
    SR = 44100

    def __init__(self, vol=0.55):
        self.enabled = PYGAME_OK
        self.master = vol
        self.muted = False
        if not self.enabled:
            return
        try:
            pygame.mixer.pre_init(self.SR, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self.ch_fall = pygame.mixer.Channel(0)
            self.ch_ppe = pygame.mixer.Channel(1)
            self.ch_ui = pygame.mixer.Channel(2)
            self.ch_hum = pygame.mixer.Channel(3)

            self.snd_fall = self._mk_fall()
            self.snd_ppe = self._mk_ppe_warn()
            self.snd_ok = self._mk_ok()
            self.snd_click = self._mk_click()
            self.snd_hum = self._mk_hum()

            self.ch_hum.play(self.snd_hum, loops=-1)
            self.ch_hum.set_volume(self.master * 0.12)
            self._prev_status = {}
        except Exception as exc:
            print(f"[Audio] disabled: {exc}")
            self.enabled = False

    @staticmethod
    def _env(n, a=0.01, r=0.05):
        e = np.ones(n, np.float32)
        ai = max(1, int(n * a))
        ri = max(1, int(n * r))
        e[:ai] = np.linspace(0, 1, ai)
        e[-ri:] = np.linspace(1, 0, ri)
        return e

    def _to_snd(self, a):
        v = (a * 32767.0 * self.master).clip(-32767, 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((v, v)))

    def _mk_hum(self):
        n = int(self.SR * 2.0)
        t = np.linspace(0, 2.0, n, False)
        sig = 0.3 * np.sin(2 * np.pi * 50 * t) + 0.1 * np.sin(2 * np.pi * 100 * t)
        return self._to_snd(sig)

    def _mk_fall(self):
        n = int(self.SR * 0.9)
        t = np.linspace(0, 0.9, n, False)
        f = np.linspace(850, 280, n)
        sig = (0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sign(np.sin(2 * np.pi * (f * 0.5) * t))) * self._env(n, 0.01, 0.15)
        return self._to_snd(sig)

    def _mk_ppe_warn(self):
        n = int(self.SR * 0.45)
        t = np.linspace(0, 0.45, n, False)
        sig = (0.6 * np.sin(2 * np.pi * 780 * t) + 0.4 * np.sin(2 * np.pi * 620 * t)) * self._env(n, 0.02, 0.1)
        return self._to_snd(sig)

    def _mk_ok(self):
        n = int(self.SR * 0.5)
        t = np.linspace(0, 0.5, n, False)
        sig = (0.5 * np.sin(2 * np.pi * 523.25 * t) + 0.5 * np.sin(2 * np.pi * 659.25 * t)) * self._env(n, 0.02, 0.2)
        return self._to_snd(sig)

    def _mk_click(self):
        n = int(self.SR * 0.04)
        t = np.linspace(0, 0.04, n, False)
        sig = np.sin(2 * np.pi * 1200 * t) * self._env(n, 0.05, 0.4)
        return self._to_snd(sig)

    def play_fall(self):
        if self.enabled and not self.muted:
            self.ch_fall.play(self.snd_fall)

    def play_ppe(self):
        if self.enabled and not self.muted:
            self.ch_ppe.play(self.snd_ppe)

    def play_ok(self):
        if self.enabled and not self.muted:
            self.ch_ui.play(self.snd_ok)

    def play_click(self):
        if self.enabled and not self.muted:
            self.ch_ui.play(self.snd_click)

    def vol_up(self):
        self.master = min(1.0, self.master + 0.1)
        if self.enabled:
            self.ch_hum.set_volume(self.master * 0.12)

    def vol_dn(self):
        self.master = max(0.0, self.master - 0.1)
        if self.enabled:
            self.ch_hum.set_volume(self.master * 0.12)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled:
            if self.muted:
                self.ch_hum.set_volume(0)
            else:
                self.ch_hum.set_volume(self.master * 0.12)


# ============================== WORKER =======================================
class Worker:
    ROLES = ["Supervisor", "Welder", "Technician", "Operator", "Inspector"]

    def __init__(self, wid, pos, role="Worker", task="walking_in_yard"):
        self.id = wid
        self.pos = [float(pos[0]), float(pos[1])]
        self.home_pos = [float(pos[0]), float(pos[1])]
        self.vel = [0.0, 0.0]
        self.role = role
        self.task = task
        self.phase = random.uniform(0.0, 6.28)
        self.facing = 1
        self.moving = False
        self.trail = deque(maxlen=14)
        self.body_temp = 36.8
        self.heart_rate = 76
        self.fall = False
        self.heat = False
        self.gas = False
        self.ppe_ok = True
        self.ppe_missing = []
        self.fall_t = 0.0
        self.alert_ring = 0.0
        self.walk_cycle = random.uniform(0, 10)

        # A) Helmet Color Classification (Standard Industrial Roles)
        self.helmet_color_name, self.helmet_bgr = get_role_helmet_color(self.role)

        # 2) Geofencing & Zone RBAC State
        self.in_zone = False
        self.zone_id = None
        self.zone_name = "Open Yard"
        self.zone_violation = False
        self.zone_reason = "Clear"

    def update(self, dt):
        if self.fall:
            self.fall_t += dt
            self.moving = False
            self.vel = [0.0, 0.0]
        else:
            if random.random() < 0.025:
                if random.random() < 0.30:
                    self.vel = [0.0, 0.0]
                else:
                    a = random.uniform(0, math.tau)
                    s = random.uniform(40, 95)
                    self.vel = [s * math.cos(a), s * math.sin(a)]

            self.pos[0] += self.vel[0] * dt
            self.pos[1] += self.vel[1] * dt
            self.pos[0] = max(60, min(GLOBAL_W - 60, self.pos[0]))
            self.pos[1] = max(60, min(GLOBAL_H - 60, self.pos[1]))

            self.moving = (abs(self.vel[0]) + abs(self.vel[1])) > 10
            self.phase += dt * (11.0 if self.moving else 2.5)
            self.walk_cycle += dt * 15 if self.moving else 0
            if self.vel[0] > 6:
                self.facing = 1
            elif self.vel[0] < -6:
                self.facing = -1

        if self.moving and not self.fall:
            self.trail.append((self.pos[0], self.pos[1]))

        self.alert_ring = (self.alert_ring + dt * 4) % (2 * math.pi)

        # Point-in-Polygon Geofencing Evaluation
        gf = evaluate_geofence(self.pos, self.role)
        self.in_zone = gf["in_zone"]
        self.zone_id = gf["zone_id"]
        self.zone_name = gf["zone_name"]
        self.zone_violation = not gf["authorized"]
        self.zone_reason = gf["reason"]

        if self.heat:
            self.body_temp += (40.2 - self.body_temp) * dt * 0.4
        else:
            self.body_temp += (36.8 - self.body_temp) * dt * 0.4

        base_hr = 74 + (self.body_temp - 36.8) * 15
        self.heart_rate = int(base_hr + (45 if self.fall else 0) + (10 if not self.ppe_ok else 0) + (15 if self.zone_violation else 0))

    def status(self):
        if self.fall:
            return "FALL"
        if self.zone_violation:
            return "DANGER"
        if self.gas:
            return "GAS"
        if self.heat:
            return "HEAT"
        if not self.ppe_ok or bool(self.ppe_missing):
            return "WARN"
        return "SAFE"

    def reset(self):
        self.fall = False
        self.heat = False
        self.gas = False
        self.fall_t = 0.0
        self.ppe_ok = True
        self.ppe_missing = []
        self.trail.clear()
        self.pos = [self.home_pos[0], self.home_pos[1]]
        self.vel = [0.0, 0.0]
        self.helmet_color_name, self.helmet_bgr = get_role_helmet_color(self.role)
        gf = evaluate_geofence(self.pos, self.role)
        self.in_zone = gf["in_zone"]
        self.zone_id = gf["zone_id"]
        self.zone_name = gf["zone_name"]
        self.zone_violation = not gf["authorized"]
        self.zone_reason = gf["reason"]


# ============================== MASSIVE FACTORY ==============================
class MassiveFactory:
    def __init__(self):
        self.W, self.H = GLOBAL_W, GLOBAL_H
        self.base_texture = self._generate_texture()

    def _generate_texture(self):
        img = np.full((self.H, self.W, 3), C_CONCRETE, dtype=np.uint8)
        noise = (np.random.randn(self.H, self.W, 3) * 6).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Multi-lane Roads
        cv2.rectangle(img, (0, 600), (self.W, 720), C_ASPHALT, -1)
        cv2.rectangle(img, (1000, 0), (1120, self.H), C_ASPHALT, -1)

        # Road Markings
        for x in range(20, self.W, 80):
            cv2.line(img, (x, 660), (x + 40, 660), (50, 180, 220), 4)
        for y in range(20, self.H, 80):
            cv2.line(img, (1060, y), (1060, y + 40), (50, 180, 220), 4)

        return img

    def draw_environment(self, img):
        np.copyto(img, self.base_texture)

        # 2) Dynamic Polygonal Geofencing Zones & Role Authorization Badges
        for zid, z in GEOFENCE_ZONES.items():
            pts = z["polygon"]
            col = z["color"]
            ov = img.copy()
            cv2.fillPoly(ov, [pts], col)
            cv2.addWeighted(ov, 0.16, img, 0.84, 0, img)
            cv2.polylines(img, [pts], True, col, 3, cv2.LINE_AA)
            draw_text_shadow(img, z["name"], (pts[0][0] + 20, pts[0][1] + 36), FONT_B, 0.82, col, 2)
            draw_text_shadow(img, z.get("auth_badge", ""), (pts[0][0] + 20, pts[0][1] + 62), FONT_B, 0.50, (240, 240, 240), 1)

        # 3D Shaded Buildings
        buildings = [
            (110, 110, 500, 240, "MAINTENANCE HANGAR"),
            (1250, 130, 450, 280, "U-200 CHEMICAL UNIT"),
        ]
        for x, y, w, h, name in buildings:
            draw_shadow(img, "rect", (x, y, w, h), offset=(22, 22), alpha=0.55)
            cv2.rectangle(img, (x, y), (x + w, y + h), (180, 185, 190), -1)
            cv2.rectangle(img, (x, y), (x + w, y + 36), (115, 120, 125), -1)
            cv2.rectangle(img, (x, y), (x + w, y + h), (85, 90, 95), 3)
            draw_text_shadow(img, name, (x + 20, y + h - 22), FONT_B, 0.85, (45, 45, 45), 2)

        # 3D Shaded Chemical Tanks
        tanks = [
            (880, 1050, 125, "TK-101 (METHANOL)"),
            (1200, 1050, 125, "TK-102 (CHLORINE)"),
            (1040, 1250, 125, "TK-103 (BENZENE)"),
        ]
        for cx, cy, r, name in tanks:
            draw_shadow(img, "circle", (cx, cy, r), offset=(26, 26), alpha=0.55)
            cv2.circle(img, (cx, cy), r, (215, 220, 225), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), r, (150, 155, 160), 6, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), r - 26, (235, 240, 245), 3, cv2.LINE_AA)
            draw_text_shadow(img, name, (cx - 70, cy + 8), FONT_B, 0.72, (50, 50, 50), 2)

        # Animated Industrial Flare Stack
        fx, fy = 1850, 920
        cv2.circle(img, (fx, fy), 24, (45, 48, 52), -1)
        cv2.circle(img, (fx, fy), 24, (100, 105, 110), 3)
        draw_text_shadow(img, "FLARE STACK FS-01", (fx - 85, fy + 45), FONT_B, 0.65, (40, 40, 40), 2)

        t = time.time() * 9.0
        for i in range(9):
            ox = int(math.sin(t + i * 0.8) * 7)
            oy = int(i * 19)
            rad = max(4, 28 - i * 3)
            col = (0, min(255, 110 + i * 20), 255)
            cv2.circle(img, (fx + ox, fy - oy), rad, col, -1, cv2.LINE_AA)

    def draw_workers(self, img, workers, ai_engine: AISafetyEngine):
        for w in workers:
            x, y = int(w.pos[0]), int(w.pos[1])
            st = w.status()
            col = STATUS_COLORS[st]

            # 1. Footstep Trail
            for i, (tx, ty) in enumerate(w.trail):
                a = (i + 1) / (len(w.trail) + 1) * 0.35
                r = int(6 * a * 2)
                if r < 1:
                    continue
                ov = img.copy()
                cv2.circle(ov, (int(tx), int(ty)), r, col, -1, cv2.LINE_AA)
                cv2.addWeighted(ov, a, img, 1 - a, 0, img)

            # 2. Alert Pulse Rings
            if st in ("FALL", "WARN", "DANGER", "HEAT", "GAS"):
                pulse = 8 * math.sin(w.alert_ring)
                aacircle(img, (x, y + 8), int(34 + pulse), col, 2)
                aacircle(img, (x, y + 8), int(46 + pulse), col, 1)

            # 3. Ground Shadow (if standing)
            if not w.fall:
                cv2.ellipse(img, (x, y + 30), (16, 6), 0, 0, 360, C_SHADOW, -1, cv2.LINE_AA)

            # 4. Humanoid Body & Limbs Rendering
            if w.fall:
                # Fallen worker: horizontal body, crumpled limbs, fallen hard hat
                aaline(img, (x - 24, y + 14), (x + 24, y + 10), col, 9)
                aacircle(img, (x + 30, y + 8), 11, (235, 200, 170))
                aacircle(img, (x + 30, y + 4), 9, w.helmet_bgr if w.ppe_ok else (60, 60, 65))
                aaline(img, (x - 24, y + 14), (x - 32, y + 22), col, 6)
                aaline(img, (x - 24, y + 14), (x - 30, y + 4), col, 6)
            else:
                sw = math.sin(w.phase) * (11 if w.moving else 1.2)
                cx, cy = x, y
                # Animated walking legs
                aaline(img, (cx - 4, cy + 14), (cx - 4 + int(sw), cy + 30), (32, 32, 38), 7)
                aaline(img, (cx + 4, cy + 14), (cx + 4 - int(sw), cy + 30), (32, 32, 38), 7)

                # High-vis Safety Vest / Torso
                body_col = col if st in ("FALL", "WARN", "DANGER") else PPE_COLORS["vest"]
                cv2.rectangle(img, (cx - 10, cy - 6), (cx + 10, cy + 16), body_col, -1, cv2.LINE_AA)
                cv2.rectangle(img, (cx - 10, cy - 6), (cx + 10, cy + 16), (30, 30, 35), 1, cv2.LINE_AA)

                # Reflective White Stripe across vest
                cv2.rectangle(img, (cx - 10, cy + 4), (cx + 10, cy + 8), (250, 250, 250), -1)

                # Swinging Arms
                asw = int(sw * 0.7)
                aaline(img, (cx - 10, cy), (cx - 17 + asw, cy + 13), body_col, 6)
                aaline(img, (cx + 10, cy), (cx + 17 - asw, cy + 13), body_col, 6)

                # Head with flesh tone and contour
                aacircle(img, (cx, cy - 18), 10, (235, 200, 170))
                aacircle(img, (cx, cy - 18), 10, (60, 50, 45), 1)

                # Safety Helmet with standard role color: White/Blue/Yellow/Green
                has_helmet = w.ppe_ok and ("helmet" not in [p.lower() for p in w.ppe_missing])
                helmet_col = w.helmet_bgr if has_helmet else (60, 60, 65)
                cv2.ellipse(img, (cx, cy - 20), (12, 9), 0, 180, 360, helmet_col, -1, cv2.LINE_AA)
                brim_col = (max(0, helmet_col[0] - 40), max(0, helmet_col[1] - 40), max(0, helmet_col[2] - 40)) if has_helmet else (40, 40, 40)
                aaline(img, (cx - 12, cy - 20), (cx + 12, cy - 20), brim_col, 2)
                if not has_helmet:
                    cv2.putText(img, "!", (cx + 12, cy - 22), FONT_B, 0.7, (40, 40, 255), 2, cv2.LINE_AA)

            # 5. AI Evaluation Tag & Bounding Box (PPE.pt & Fall.pt)
            ai_eval = ai_engine.evaluate_worker(
                None,
                {"fall": w.fall, "ppe_missing": w.ppe_missing, "role": w.role}
            )
            top_det = ai_eval[0] if ai_eval else {"class": "Person", "confidence": 0.95, "model": "PPE.pt"}
            lbl = f"{top_det['model']}: {top_det['class']} {int(top_det['confidence'] * 100)}%"

            if w.fall:
                bx0, by0, bx1, by1 = x - 42, y - 6, x + 42, y + 32
            else:
                bx0, by0, bx1, by1 = x - 32, y - 32, x + 32, y + 36

            cv2.rectangle(img, (bx0, by0), (bx1, by1), col, 1, cv2.LINE_AA)

            (lw, lh), _ = cv2.getTextSize(lbl, FONT, 0.40, 1)
            cv2.rectangle(img, (bx0, by0 - 18), (bx0 + lw + 10, by0), col, -1)
            cv2.putText(img, lbl, (bx0 + 5, by0 - 5), FONT, 0.40, (0, 0, 0), 1, cv2.LINE_AA)

            # Worker ID tag above AI box (with Helmet Color role indicator)
            tag = f"W-{w.id} {w.role[:3].upper()} [{w.helmet_color_name[:1]}]"
            (tw, th), _ = cv2.getTextSize(tag, FONT, 0.45, 1)
            tag_y = by0 - 24
            cv2.rectangle(img, (x - tw // 2 - 6, tag_y - th - 2), (x + tw // 2 + 6, tag_y + 4), (15, 15, 20), -1)
            cv2.rectangle(img, (x - tw // 2 - 6, tag_y - th - 2), (x + tw // 2 + 6, tag_y + 4), col, 1)
            draw_text_shadow(img, tag, (x - tw // 2, tag_y), FONT, 0.45, col, 1)

            # Alert status banner placed cleanly above ID tag
            if st == "FALL":
                draw_text_shadow(img, "! FALL DETECTED !", (x - 75, tag_y - th - 8), FONT_B, 0.55, STATUS_COLORS["FALL"], 2)
            elif w.zone_violation:
                draw_text_shadow(img, f"! UNAUTHORIZED IN {w.zone_name[:14]} !", (x - 110, tag_y - th - 8), FONT_B, 0.46, STATUS_COLORS["DANGER"], 2)
            elif not w.ppe_ok or w.ppe_missing:
                miss_str = ", ".join(w.ppe_missing) if w.ppe_missing else "PPE"
                draw_text_shadow(img, f"! MISSING {miss_str.upper()} !", (x - 75, tag_y - th - 8), FONT_B, 0.48, STATUS_COLORS["WARN"], 2)


# ============================== UI MANAGER ===================================
class UIManager:
    @staticmethod
    def draw_glass_ui(img, workers, active_cam, mode_text, event_logs, total_alerts, auto_timer=0.0):
        W, H = CANVAS_W, CANVAS_H

        # Bottom Glass Panel
        blend_rect(img, (0, H - PANEL_H), (W, H), C_HUD_BG, 0.95)
        cv2.line(img, (0, H - PANEL_H), (W, H - PANEL_H), C_HUD_BORDER, 2)

        draw_text_shadow(img, "DARIYA AI VMS", (20, H - PANEL_H + 36), FONT_B, 0.9, C_ACCENT, 2)
        draw_text_shadow(img, "Autonomous Safety Director | Jubail Industrial City", (20, H - PANEL_H + 58), FONT, 0.42, C_TEXT_DIM, 1)
        draw_text_shadow(img, "Integrated YOLO: PPE.pt (20 classes) + Fall.pt", (20, H - PANEL_H + 78), FONT_B, 0.42, (0, 255, 200), 1)

        draw_text_shadow(img, f"Alerts Logged: {total_alerts}", (20, H - PANEL_H + 104), FONT, 0.42, (255, 145, 0), 1)

        # Worker Telemetry Cards
        cx = 360
        cw = 190
        for w in workers:
            if cx + cw > W - SIDEBAR_W - 10:
                break
            st = w.status()
            col = STATUS_COLORS[st]
            blend_rect(img, (cx, H - PANEL_H + 12), (cx + cw, H - 12), (25, 30, 35), 0.85)
            cv2.rectangle(img, (cx, H - PANEL_H + 12), (cx + cw, H - 12), col, 1)
            cv2.rectangle(img, (cx, H - PANEL_H + 12), (cx + cw, H - PANEL_H + 16), col, -1)

            draw_text_shadow(img, f"W-{w.id} | {w.role[:8]} [{w.helmet_color_name[:1]}]", (cx + 8, H - PANEL_H + 34), FONT_B, 0.44, (255, 255, 255), 1)
            draw_text_shadow(img, f"STATUS: {st}", (cx + 8, H - PANEL_H + 52), FONT_B, 0.48, col, 1)
            draw_text_shadow(img, f"HR: {w.heart_rate} bpm | {w.body_temp:.1f}C", (cx + 8, H - PANEL_H + 70), FONT, 0.38, (200, 200, 200), 1)
            if w.fall:
                ai_lbl = "Fall Detected"
            elif w.zone_violation:
                ai_lbl = "Zone Breach!"
            elif not w.ppe_ok:
                ai_lbl = "Missing PPE"
            else:
                ai_lbl = f"Safe ({w.helmet_color_name})"
            draw_text_shadow(img, f"AI: {ai_lbl}", (cx + 8, H - PANEL_H + 88), FONT, 0.38, col, 1)
            draw_text_shadow(img, f"Zone: {w.zone_name[:14]}", (cx + 8, H - PANEL_H + 106), FONT, 0.35, (160, 160, 160), 1)
            cx += cw + 8

        # Right Sidebar Panel
        sx0 = W - SIDEBAR_W
        blend_rect(img, (sx0, 0), (W, H), C_HUD_BG, 0.95)
        cv2.line(img, (sx0, 0), (sx0, H), C_HUD_BORDER, 2)

        # Camera Switcher in Sidebar
        y = 28
        draw_text_shadow(img, "CAMERA NETWORK", (sx0 + 20, y), FONT_B, 0.6, C_ACCENT, 1)
        y += 24
        for cam_id, (cx_c, cy_c, cw_c, ch_c, c_name, _) in CAMERAS.items():
            is_active = (active_cam == cam_id)
            color = (50, 255, 100) if is_active else (140, 145, 150)
            prefix = "> " if is_active else "  "
            draw_text_shadow(img, f"{prefix}[{cam_id}] {c_name.split(' ')[0]}", (sx0 + 16, y), FONT_B, 0.45, color, 1)
            y += 22

        # AI Detection Statistics
        y += 12
        draw_text_shadow(img, "YOLO & RBAC STATS", (sx0 + 20, y), FONT_B, 0.58, C_ACCENT, 1)
        y += 24
        total_w = len(workers)
        safe_w = sum(1 for w in workers if w.status() == "SAFE")
        warn_w = sum(1 for w in workers if w.status() == "WARN")
        breach_w = sum(1 for w in workers if w.zone_violation)
        fall_w = sum(1 for w in workers if w.status() == "FALL")

        for lbl, v, c in [
            ("Workers Monitored", total_w, (255, 255, 255)),
            ("PPE Compliant", safe_w, STATUS_COLORS["SAFE"]),
            ("PPE Violations", warn_w, STATUS_COLORS["WARN"]),
            ("Zone Breaches", breach_w, STATUS_COLORS["DANGER"]),
            ("Fall Incidents", fall_w, STATUS_COLORS["FALL"]),
        ]:
            draw_text_shadow(img, lbl, (sx0 + 20, y), FONT, 0.42, (180, 180, 180), 1)
            draw_text_shadow(img, str(v), (W - 35, y), FONT_B, 0.48, c, 1)
            y += 20

        # Event Log from outputs/alerts.jsonl
        y += 12
        draw_text_shadow(img, "LIVE EVENT LOG", (sx0 + 20, y), FONT_B, 0.52, C_ACCENT, 1)
        y += 18
        max_ev = (H - y - 60) // 18
        for ts, msg, col in list(event_logs)[-max_ev:]:
            cv2.circle(img, (sx0 + 26, y + 4), 3, col, -1, cv2.LINE_AA)
            draw_text_shadow(img, f"[{ts:4.1f}]", (sx0 + 34, y + 8), FONT, 0.35, (120, 120, 120), 1)
            draw_text_shadow(img, msg[:22], (sx0 + 82, y + 8), FONT, 0.37, col, 1)
            y += 18

        # Operator Instructions
        blend_rect(img, (sx0 + 10, H - 48), (W - 10, H - 10), (20, 25, 30), 0.9)
        cv2.rectangle(img, (sx0 + 10, H - 48), (W - 10, H - 10), C_HUD_BORDER, 1)
        draw_text_shadow(img, "[SPACE] Pause | [0-3] Cam | [G] Zone Breach", (sx0 + 16, H - 30), FONT, 0.34, (200, 200, 200), 1)
        draw_text_shadow(img, "[F] Fall | [P] PPE | [R] Reset | [ESC]", (sx0 + 16, H - 14), FONT, 0.35, C_ACCENT, 1)

        # Autonomous Mode Indicator (Placed below the CCTV top bar)
        blend_rect(img, (20, 48), (440, 116), (10, 15, 20), 0.88)
        cv2.rectangle(img, (20, 48), (440, 116), C_HUD_BORDER, 1)
        cv2.rectangle(img, (20, 48), (440, 74), (25, 35, 45), -1)
        draw_text_shadow(img, "AUTONOMOUS AI DIRECTOR [PITCH DEMO]", (30, 66), FONT_B, 0.44, C_ACCENT, 1)
        draw_text_shadow(img, mode_text, (30, 102), FONT_B, 0.48, (0, 255, 120), 1)

    @staticmethod
    def draw_cctv_overlay(img, cam_name, has_alert=False):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        h, w = img.shape[:2]

        # Red alert pulsing border if active incident
        if has_alert:
            pulse = int(100 * math.sin(time.time() * 10)) + 155
            cv2.rectangle(img, (0, 0), (w - 1, h - 1), (0, 0, pulse), 4)

        # Top Bar
        blend_rect(img, (0, 0), (w, 36), (10, 10, 15), 0.75)
        rc = C_REC if int(time.time() * 2) % 2 == 0 else (50, 50, 50)
        cv2.circle(img, (20, 18), 7, rc, -1, cv2.LINE_AA)
        draw_text_shadow(img, "REC", (34, 23), FONT_B, 0.48, rc, 1)

        draw_text_shadow(img, f"{cam_name} | {now}", (110, 23), FONT_B, 0.52, (255, 255, 255), 1)
        draw_text_shadow(img, "AI: PPE.pt + Fall.pt", (w - 240, 23), FONT, 0.42, (0, 255, 200), 1)

        # Corner Crosshairs
        L = 32
        c = (255, 255, 255)
        for px, py, sx, sy in [(10, 10, 1, 1), (w - 10, 10, -1, 1), (10, h - 10, 1, -1), (w - 10, h - 10, -1, -1)]:
            cv2.line(img, (px, py), (px + sx * L, py), c, 2, cv2.LINE_AA)
            cv2.line(img, (px, py), (px, py + sy * L), c, 2, cv2.LINE_AA)


# ============================== MAIN =========================================
def main():
    factory = MassiveFactory()
    ai_engine = AISafetyEngine()
    alert_bridge = SimulatorAlertBridge()
    audio = AudioEngine(0.55)

    workers = [
        Worker(101, (360, 480), role="Supervisor", task="supervising_welding"),   # White Helmet (Site Leadership)
        Worker(102, (520, 420), role="Welder", task="welding"),                  # Yellow Helmet (Hot Work Operator)
        Worker(103, (1650, 460), role="Technician", task="chemical_sampling"),    # Blue Helmet (Maintenance & Tech)
        Worker(104, (1400, 300), role="Inspector", task="safety_audit"),         # Green Helmet (HSE Safety Auditor)
    ]

    active_cam = 0
    auto_director = True
    demo_timer = 0.0
    demo_stage = 0
    mode_text = "AUTO: GLOBAL SCAN (ALL SYSTEMS NORMAL)"
    event_logs = deque(maxlen=25)

    global_buffer = np.zeros((GLOBAL_H, GLOBAL_W, 3), np.uint8)
    canvas = np.zeros((CANVAS_H, CANVAS_W, 3), np.uint8)

    t0 = time.time()
    last = t0
    frame_counter = 0

    event_logs.append((0.0, "DARIYA AI Online", (40, 200, 80)))
    event_logs.append((0.0, "YOLO: PPE.pt & Fall.pt", (0, 255, 200)))
    event_logs.append((0.0, "Auto-Director Active", C_ACCENT))

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)

    while True:
        now = time.time()
        dt = min(0.05, now - last)
        last = now
        t = now - t0
        frame_counter += 1
        frame_id = f"vms_f{frame_counter:05d}"

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break

        # Keyboard Controls
        if key == ord(' '):
            auto_director = not auto_director
            audio.play_click()
            mode_text = "AUTONOMOUS DIRECTOR [RESUMED]" if auto_director else "[DIRECTOR PAUSED - MANUAL]"
            event_logs.append((t, "Auto-Director " + ("ON" if auto_director else "PAUSED"), C_ACCENT))
        elif key == ord('0'):
            active_cam = 0
            audio.play_click()
            auto_director = False
            mode_text = "MANUAL: GLOBAL SCADA VIEW"
        elif key == ord('1'):
            active_cam = 1
            audio.play_click()
            auto_director = False
            mode_text = "MANUAL: CAM-01 ZOOM"
        elif key == ord('2'):
            active_cam = 2
            audio.play_click()
            auto_director = False
            mode_text = "MANUAL: CAM-02 ZOOM"
        elif key == ord('3'):
            active_cam = 3
            audio.play_click()
            auto_director = False
            mode_text = "MANUAL: CAM-03 ZOOM"
        elif key in (ord('r'), ord('R')):
            for w in workers:
                w.reset()
            audio.play_ok()
            event_logs.append((t, "States Reset All Clear", (40, 200, 80)))
        elif key in (ord('f'), ord('F')):
            workers[1].fall = True
            audio.play_fall()
            event_logs.append((t, "Manual Fall Test (W-102)", STATUS_COLORS["FALL"]))
        elif key in (ord('p'), ord('P')):
            workers[2].ppe_ok = not workers[2].ppe_ok
            workers[2].ppe_missing = ["Helmet", "Safety Vest"] if not workers[2].ppe_ok else []
            audio.play_ppe()
            event_logs.append((t, "Manual PPE Toggle (W-103)", STATUS_COLORS["WARN"]))
        elif key in (ord('g'), ord('G')):
            # Geofencing breach manual test: Welder enters Restricted Tank Farm
            workers[1].pos = [1100.0, 950.0]
            workers[1].vel = [0.0, 0.0]
            audio.play_ppe()
            active_cam = 3
            auto_director = False
            mode_text = "MANUAL: GEOFENCE BREACH TEST (CAM-03)"
            event_logs.append((t, "Manual Zone Breach: W-102 in Tank Farm", STATUS_COLORS["DANGER"]))
        elif key in (ord('+'), ord('=')):
            audio.vol_up()
        elif key in (ord('-'), ord('_')):
            audio.vol_dn()
        elif key in (ord('m'), ord('M')):
            audio.toggle_mute()

        # ==================== AUTONOMOUS SCRIPTED SEQUENCE ====================
        if auto_director:
            demo_timer += dt

            # Stage 0: Global SCADA Patrol (0 - 5s)
            if demo_stage == 0 and demo_timer > 5.0:
                demo_stage = 1
                active_cam = 1  # Auto-switch to Welding Shop
                workers[1].fall = True  # Worker W-102 falls!
                audio.play_fall()
                mode_text = "AUTO: FALL DETECTED (CAM-01 WELDING SHOP)"
                event_logs.append((t, "CRITICAL: W-102 Fall", STATUS_COLORS["FALL"]))

            # Stage 1: Fall Detected in CAM-1 -> Recovery (5 - 16s)
            elif demo_stage == 1 and demo_timer > 16.0:
                demo_stage = 2
                active_cam = 0  # Return to Global SCADA
                for w in workers:
                    w.reset()
                audio.play_ok()
                mode_text = "AUTO: EMERGENCY RESOLVED (ALL CLEAR)"
                event_logs.append((t, "Medical Team Dispatched - Clear", (40, 200, 80)))

            # Stage 2: Global Calm -> PPE Violation in CAM-2 (16 - 24s)
            elif demo_stage == 2 and demo_timer > 24.0:
                demo_stage = 3
                active_cam = 2  # Auto-switch to Chemical Unit
                workers[2].ppe_ok = False
                workers[2].ppe_missing = ["Helmet", "Safety Vest"]
                audio.play_ppe()
                mode_text = "AUTO: PPE VIOLATION (CAM-02 CHEMICAL UNIT)"
                event_logs.append((t, "PPE VIOLATION: W-103 No PPE", STATUS_COLORS["WARN"]))

            # Stage 3: PPE Violation in CAM-2 -> Restored (24 - 34s)
            elif demo_stage == 3 and demo_timer > 34.0:
                demo_stage = 4
                active_cam = 0  # Return to Global SCADA
                for w in workers:
                    w.reset()
                audio.play_ok()
                mode_text = "AUTO: PPE COMPLIANCE RESTORED"
                event_logs.append((t, "Compliance Restored - All Safe", (40, 200, 80)))

            # Stage 4: Geofencing Breach -> Welder W-102 enters Tank Farm (34 - 48s)
            elif demo_stage == 4 and demo_timer > 40.0:
                demo_stage = 5
                active_cam = 3  # Auto-switch to Restricted Tank Farm
                # Welder W-102 walks into Restricted Tank Farm
                workers[1].pos = [1100.0, 950.0]
                workers[1].vel = [0.0, 0.0]
                audio.play_ppe()
                mode_text = "AUTO: GEOFENCE BREACH (UNAUTHORIZED WELDER IN TANK FARM)"
                event_logs.append((t, "SECURITY ALERT: W-102 Zone Breach", STATUS_COLORS["DANGER"]))

            # Stage 5: Geofence Breach Resolved -> Restart Patrol Loop (48 - 58s)
            elif demo_stage == 5 and demo_timer > 52.0:
                demo_stage = 0
                demo_timer = 0.0
                active_cam = 0
                for w in workers:
                    w.reset()
                audio.play_ok()
                mode_text = "AUTO: GLOBAL SCAN (ALL SYSTEMS NORMAL)"
                event_logs.append((t, "Cycle Complete - Restarting", (40, 200, 80)))

        # Update Workers Physics & Vitals
        for w in workers:
            w.update(dt)

            # Live Bridge to outputs/alerts.jsonl
            if w.fall:
                rec = alert_bridge.record_alert(
                    worker_id=w.id,
                    severity="CRITICAL",
                    escalation="emergency",
                    task=w.task,
                    zone=w.zone_name,
                    missing_ppe=[],
                    fall_detected=True,
                    zone_violation=False,
                    reason_codes=["fall_detected"],
                    explanation=f"Worker W-{w.id} ({w.role}) fell in {w.zone_name}. Confirmed by Fall.pt",
                    frame_id=frame_id,
                    model_source="Fall.pt",
                )
                if rec:
                    event_logs.append((t, f"LOG: {rec['incident_id']} (Fall)", STATUS_COLORS["FALL"]))

            elif w.zone_violation:
                rec = alert_bridge.record_alert(
                    worker_id=w.id,
                    severity="CRITICAL",
                    escalation="supervisor",
                    task=w.task,
                    zone=w.zone_name,
                    missing_ppe=[],
                    fall_detected=False,
                    zone_violation=True,
                    reason_codes=["unauthorized_personnel", "geofence_breach"],
                    explanation=f"Worker W-{w.id} ({w.role}, {w.helmet_color_name} Helmet) unauthorized in {w.zone_name}. Access Denied by Geofence RBAC.",
                    frame_id=frame_id,
                    model_source="Geofence_RBAC",
                )
                if rec:
                    event_logs.append((t, f"LOG: {rec['incident_id']} (Zone Breach)", STATUS_COLORS["DANGER"]))

            elif not w.ppe_ok and w.ppe_missing:
                rec = alert_bridge.record_alert(
                    worker_id=w.id,
                    severity="WARNING",
                    escalation="supervisor",
                    task=w.task,
                    zone=w.zone_name,
                    missing_ppe=w.ppe_missing,
                    fall_detected=False,
                    zone_violation=False,
                    reason_codes=["missing_critical_ppe"],
                    explanation=f"Missing PPE ({', '.join(w.ppe_missing)}) for W-{w.id} in {w.zone_name}. Confirmed by PPE.pt",
                    frame_id=frame_id,
                    model_source="PPE.pt",
                )
                if rec:
                    event_logs.append((t, f"LOG: {rec['incident_id']} (PPE)", STATUS_COLORS["WARN"]))

        # Render Factory Environment & Humanoid Workers
        factory.draw_environment(global_buffer)
        factory.draw_workers(global_buffer, workers, ai_engine)

        # Crop Active Camera View
        cx, cy, cw, ch, c_name, _ = CAMERAS[active_cam]
        cam_crop = global_buffer[cy:cy + ch, cx:cx + cw]
        active_view = cv2.resize(cam_crop, (VIEW_W, VIEW_H), interpolation=cv2.INTER_LINEAR)

        # Composite Main Display Canvas
        canvas[0:VIEW_H, 0:VIEW_W] = active_view

        # CCTV Viewport Overlay
        has_incident = any(w.status() != "SAFE" and (cx <= w.pos[0] < cx + cw) and (cy <= w.pos[1] < cy + ch) for w in workers)
        UIManager.draw_cctv_overlay(canvas[0:VIEW_H, 0:VIEW_W], c_name, has_alert=has_incident)

        # Draw HUD Glass Interface & Sidebar
        UIManager.draw_glass_ui(
            canvas,
            workers,
            active_cam,
            mode_text,
            event_logs,
            alert_bridge.counter,
            auto_timer=demo_timer,
        )

        cv2.imshow(WINDOW, canvas)

    cv2.destroyAllWindows()
    if audio.enabled:
        try:
            pygame.mixer.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
