"""PPE detections use checkpoint labels, never assumed numeric class ordering."""
from pathlib import Path

import torch
from ultralytics import YOLO
from ultralytics.engine.results import Results

from config import threshold

PPE_CLASSES = [
    "Coverall", "No Coverall", "Ear Protectors", "No Ear Protectors",
    "Face Shield", "No Face Shield", "Gloves", "No Gloves", "Helmet",
    "No Helmet", "Mask", "No Mask", "Safety Glasses", "No Safety Glasses",
    "Safety Harness", "No Safety Harness", "Safety Shoes", "No Safety Shoes",
    "Safety Vest", "No Safety Vest",
]


class PPEDetector:
    def __init__(self, model_path, confidence=0.25):
        self.confidence = threshold(confidence)
        if not Path(model_path).is_file():
            raise ValueError(f"PPE checkpoint not found: {model_path}")
        self.model = YOLO(str(model_path))
        names = list(self.model.names.values())
        if len(names) != 20 or set(names) != set(PPE_CLASSES):
            raise ValueError(f"PPE checkpoint must have the specified 20 classes; found {names}")

    def detect(self, frame):
        result = self.model.predict(frame, conf=self.confidence, verbose=False)[0]
        detections = []
        for box in result.boxes:
            detections.append({
                "class": result.names[int(box.cls.item())],
                "confidence": float(box.conf.item()),
                "bbox": [float(v) for v in box.xyxy[0].tolist()],
            })
        return {"detections": detections, "confidence": (
            sum(d["confidence"] for d in detections) / len(detections) if detections else None
        )}

    def annotate(self, frame, observation):
        """Draw with Ultralytics' native styling, using the existing detections."""
        if not observation["detections"]:
            return frame
        names = self.model.names
        class_ids = {name: index for index, name in names.items()}
        boxes = torch.tensor([
            [*d["bbox"], d["confidence"], class_ids[d["class"]]]
            for d in observation["detections"]
        ], dtype=torch.float32)
        result = Results(orig_img=frame, path="", names=names, boxes=boxes)
        frame[:] = result.plot()
        return frame
