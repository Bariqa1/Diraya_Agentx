"""Environment configuration; relative paths resolve from the repository root."""
import json
import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def threshold(value):
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Detection thresholds must be between 0 and 1")
    return value


def polygon_points(value):
    points = np.asarray(value, dtype=np.float32)
    if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 3
            or not np.isfinite(points).all() or cv2.contourArea(points) <= 0):
        raise ValueError("RESTRICTED_ZONE must contain at least 3 finite, non-collinear [x,y] points")
    return points


def resolve(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def get_optimal_device(requested_device=None):
    """Auto-detects fastest hardware: MPS (Apple Silicon GPU), CUDA (NVIDIA GPU), or CPU."""
    if requested_device and requested_device != "auto":
        return requested_device
    env_device = os.getenv("DEVICE", "auto").strip().lower()
    if env_device and env_device != "auto":
        return env_device
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


_DEVICE_LOCK = threading.Lock()


class _DeviceLockContext:
    def __init__(self, device: str):
        self.device = str(device).lower()

    def __enter__(self):
        if self.device == "mps":
            _DEVICE_LOCK.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.device == "mps":
            try:
                import torch
                if torch.backends.mps.is_available():
                    torch.mps.synchronize()
            except Exception:
                pass
            finally:
                _DEVICE_LOCK.release()


def device_inference_lock(device: str = "cpu"):
    """Thread-safe context manager for MPS inference to prevent Metal command buffer race conditions."""
    return _DeviceLockContext(device)


@dataclass
class Config:
    api_key: str
    gemini_model: str
    ppe_model: Path
    fall_model: Path
    person_model: str
    ppe_threshold: float
    fall_threshold: float
    person_threshold: float
    cache_ttl: float
    failure_cooldown: float
    max_retries: int
    input_video: Path
    output_video: Path
    processing_width: int
    processing_height: int
    restricted_zone: np.ndarray
    log_interval: float
    json_interval: float
    facility_zone: str
    device: str = "auto"

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env")
        retries = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
        if not 0 <= retries <= 5:
            raise ValueError("GEMINI_MAX_RETRIES must be between 0 and 5")
        person = os.getenv("PERSON_MODEL", "models/yolo11n.pt").strip()
        if Path(person).parent != Path("."):
            person = str(resolve(person))
        elif (ROOT / "models" / person).exists():
            person = str(resolve(f"models/{person}"))
        processing_width = int(os.getenv("PROCESSING_WIDTH", "1280"))
        processing_height = int(os.getenv("PROCESSING_HEIGHT", "720"))
        if (processing_width <= 0 or processing_height <= 0
                or processing_width % 2 or processing_height % 2):
            raise ValueError("PROCESSING_WIDTH and PROCESSING_HEIGHT must be positive even integers")
        vlm_provider = os.getenv("VLM_PROVIDER", "").strip().lower()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "").strip()

        if vlm_provider == "openai" or (openai_key and not gemini_key):
            api_key = openai_key
            model = openai_model
        else:
            api_key = gemini_key or openai_key
            model = gemini_model or openai_model

        return cls(
            api_key,
            model,
            resolve(os.getenv("PPE_MODEL_PATH", "models/PPE.pt")),
            resolve(os.getenv("FALL_MODEL_PATH", "models/Fall.pt")), person,
            threshold(os.getenv("PPE_CONFIDENCE_THRESHOLD", "0.25")),
            threshold(os.getenv("FALL_CONFIDENCE_THRESHOLD", "0.40")),
            threshold(os.getenv("PERSON_CONFIDENCE_THRESHOLD", "0.25")),
            positive(os.getenv("VLM_CACHE_TTL", "30"), "VLM_CACHE_TTL"),
            positive(os.getenv("VLM_FAILURE_COOLDOWN", "5"), "VLM_FAILURE_COOLDOWN"),
            retries, resolve(os.getenv("INPUT_VIDEO", "video_test/video_test2.mp4")),
            resolve(os.getenv("OUTPUT_VIDEO", "outputs/context_agent_output.mp4")),
            processing_width, processing_height,
            polygon_points(json.loads(os.getenv("RESTRICTED_ZONE", "[[100,100],[500,100],[550,400],[80,400]]"))),
            positive(os.getenv("LOG_INTERVAL", "1"), "LOG_INTERVAL"),
            positive(os.getenv("JSON_LOG_INTERVAL", "10"), "JSON_LOG_INTERVAL"),
            os.getenv("FACILITY_ZONE", "Welding Area").strip() or "Welding Area",
            os.getenv("DEVICE", "auto").strip() or "auto",
        )

    def validate_inputs(self):
        for name, path in (("PPE_MODEL_PATH", self.ppe_model),
                           ("FALL_MODEL_PATH", self.fall_model),
                           ("INPUT_VIDEO", self.input_video)):
            if not path.is_file():
                raise ValueError(f"{name} file does not exist: {path}")
        if not self.api_key or not self.gemini_model:
            raise ValueError("Set OPENAI_API_KEY or GEMINI_API_KEY in .env")
        if self.input_video.resolve() == self.output_video.resolve():
            raise ValueError("OUTPUT_VIDEO must differ from INPUT_VIDEO")

