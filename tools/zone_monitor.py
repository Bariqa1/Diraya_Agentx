"""Frame-local person detections and bottom-center polygon membership."""
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.engine.results import Results

from config import polygon_points, threshold


class ZoneMonitor:
    def __init__(self, model_name, polygon, confidence=0.25):
        self.polygon = polygon_points(polygon)
        self.confidence = threshold(confidence)
        self.model = YOLO(model_name)
        ids = [i for i, name in self.model.names.items() if name == "person"]
        if len(ids) != 1:
            raise ValueError("PERSON_MODEL must contain a person class")
        self.person_id = ids[0]

    def contains(self, bbox):
        x1, _, x2, y2 = bbox
        return cv2.pointPolygonTest(self.polygon, ((x1 + x2) / 2, y2), False) >= 0

    def detect(self, frame):
        result = self.model.predict(frame, classes=[self.person_id], conf=self.confidence, verbose=False)[0]
        persons = []
        for box in result.boxes:
            bbox = [float(v) for v in box.xyxy[0].tolist()]
            persons.append(dict(bbox=bbox, confidence=float(box.conf.item()),
                                inside_restricted_zone=self.contains(bbox)))
        return {"persons": persons, "violation": any(p["inside_restricted_zone"] for p in persons)}

    def annotate(self, frame, observation):
        """Use native person boxes and labels, plus zone geometry overlays."""
        cv2.polylines(frame, [self.polygon.astype(np.int32)], True, (0, 165, 255), 2)
        if observation["persons"]:
            boxes = torch.tensor([
                [*person["bbox"], person["confidence"], self.person_id]
                for person in observation["persons"]
            ], dtype=torch.float32)
            result = Results(orig_img=frame, path="", names=self.model.names, boxes=boxes)
            frame[:] = result.plot()
        for person in observation["persons"]:
            x1, y1, x2, y2 = map(int, person["bbox"])
            color = (0, 0, 255) if person["inside_restricted_zone"] else (255, 180, 0)
            cv2.circle(frame, ((x1 + x2) // 2, y2), 4, color, -1)
        return frame
