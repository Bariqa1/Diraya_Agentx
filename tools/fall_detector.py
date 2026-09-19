"""YOLO-based fall detection with checkpoint-label validation."""
from pathlib import Path

import torch
from ultralytics import YOLO
from ultralytics.engine.results import Results

from config import device_inference_lock, get_optimal_device, threshold


FALL_CLASS = "Fall"


class FallDetector:
    def __init__(self, model_path, confidence=0.40, device=None):
        self.confidence = threshold(confidence)
        self.device = get_optimal_device(device)
        if not Path(model_path).is_file():
            raise ValueError(f"Fall checkpoint not found: {model_path}")
        self.model = YOLO(str(model_path))
        matching_ids = [
            index for index, name in self.model.names.items()
            if name == FALL_CLASS
        ]
        if len(matching_ids) != 1:
            raise ValueError(
                f"Fall checkpoint must contain exactly one '{FALL_CLASS}' class; "
                f"found {list(self.model.names.values())}"
            )
        self.fall_class_id = matching_ids[0]

    def detect(self, frame):
        with device_inference_lock(self.device):
            result = self.model.predict(
                frame,
                classes=[self.fall_class_id],
                conf=self.confidence,
                device=self.device,
                verbose=False,
            )[0]
        detections = [
            {
                "class": result.names[int(box.cls.item())],
                "confidence": float(box.conf.item()),
                "bbox": [float(value) for value in box.xyxy[0].tolist()],
            }
            for box in result.boxes
        ]
        return {
            "detected": bool(detections),
            "detections": detections,
            "confidence": max((item["confidence"] for item in detections), default=None),
        }

    def annotate(self, frame, observation):
        detections = observation.get("detections", [])
        if not detections:
            return frame
        boxes = torch.tensor([
            [*item["bbox"], item["confidence"], self.fall_class_id]
            for item in detections
        ], dtype=torch.float32)
        result = Results(orig_img=frame, path="", names=self.model.names, boxes=boxes)
        frame[:] = result.plot()
        return frame
