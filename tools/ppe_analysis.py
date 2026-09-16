"""PPE Analysis tool: transforms raw YOLO detections into categorized PPE state.

Extracts detected, missing, and uncertain PPE items based on detection confidence.
"""
from typing import Any, Dict, List, Set

KNOWN_PPE = (
    "Helmet",
    "Gloves",
    "Face Shield",
    "Safety Shoes",
    "Safety Glasses",
    "Coverall",
    "Safety Harness",
    "Safety Vest",
    "Ear Protectors",
    "Mask",
)


def analyze_ppe(ppe_observation: Dict[str, Any], conf_threshold: float = 0.25) -> Dict[str, List[str]]:
    """
    Analyze raw YOLO PPE detections into:
      - detected: PPE items positively detected with confidence >= conf_threshold.
      - missing: PPE items negatively detected ("No <Item>") with confidence >= conf_threshold.
      - uncertain: PPE items that were observed with low confidence or not visually confirmed.
    """
    detections = []
    if isinstance(ppe_observation, dict):
        detections = ppe_observation.get("detections", []) or []

    best_positive: Dict[str, float] = {}
    best_negative: Dict[str, float] = {}

    for det in detections:
        cls_name = det.get("class", "").strip()
        conf = float(det.get("confidence", 0.0) or 0.0)

        if cls_name.startswith("No "):
            item = cls_name[3:].strip()
            if item in KNOWN_PPE or item:
                best_negative[item] = max(best_negative.get(item, 0.0), conf)
        else:
            item = cls_name
            if item in KNOWN_PPE or item:
                best_positive[item] = max(best_positive.get(item, 0.0), conf)

    detected: Set[str] = set()
    missing: Set[str] = set()
    uncertain: Set[str] = set()

    all_observed_items = set(best_positive.keys()) | set(best_negative.keys())

    for item in all_observed_items:
        pos_conf = best_positive.get(item, 0.0)
        neg_conf = best_negative.get(item, 0.0)

        pos_valid = pos_conf >= conf_threshold
        neg_valid = neg_conf >= conf_threshold

        if pos_valid and neg_valid:
            # If both detected above threshold (e.g. multiple persons/boxes), higher confidence wins
            if pos_conf >= neg_conf:
                detected.add(item)
            else:
                missing.add(item)
        elif pos_valid:
            detected.add(item)
        elif neg_valid:
            missing.add(item)
        else:
            uncertain.add(item)

    # Any standard PPE item that was not positively or negatively confirmed is uncertain
    for item in KNOWN_PPE:
        if item not in detected and item not in missing:
            uncertain.add(item)

    return {
        "detected": sorted(detected),
        "missing": sorted(missing),
        "uncertain": sorted(uncertain),
    }
