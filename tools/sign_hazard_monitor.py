"""Safety Signboard Reader & Dynamic Hazard Zone Generator for DIRAYA.

Solves two core challenges:
  1. Token & Cost Efficiency: One-shot scan + local persistent caching (0 tokens on recurring frames).
  2. Text-to-Geometry Geofencing: Reads safety notices (e.g. "DANGER: HIGH VOLTAGE - KEEP 5M CLEAR"),
     extracts the buffer distance in meters, and dynamically projects a ground-plane hazard polygon
     using perspective depth scaling.
"""
import json
import logging
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIGNS_CACHE = ROOT / "data" / "safety_signs_cache.json"

# Industry standard signboard height in meters (standard OSHA/ANSI Z535 sign ~ 40cm - 50cm)
STANDARD_SIGN_HEIGHT_METERS = 0.45

# Standard hazard distance defaults if not explicitly written on the signboard
DEFAULT_HAZARD_DISTANCES = {
    "high_voltage": 5.0,
    "flammable_materials": 5.0,
    "chemical_hazard": 4.0,
    "radiation": 6.0,
    "toxic_gas": 5.0,
    "excavation": 3.5,
    "welding_arc": 4.0,
    "restricted_area": 3.0,
    "general_warning": 2.5,
}

VLM_SIGN_PROMPT = """You are an industrial safety vision specialist.
Analyze this image and identify all safety warning signboards, hazard placards, barricade signs, and restriction notices (such as DANGER, DO NOT ENTER, ممنوع الدخول, خطر, CAUTION).
For each sign found, return a JSON object containing a 'signs' array:
  - "sign_id": "SIGN-01", "SIGN-02", etc.
  - "text": Exact text written on the signboard (in English and/or Arabic).
  - "text_ar": Arabic translation or transcription of the sign text.
  - "hazard_type": One of ["restricted_area", "excavation", "high_voltage", "flammable_materials", "chemical_hazard", "radiation", "toxic_gas", "welding_arc", "general_warning"]
  - "safety_distance_meters": Float distance in meters explicitly mentioned or estimated based on hazard (3.0 to 5.0).
  - "required_ppe": Array of PPE required by this sign (e.g., ["Helmet", "Safety Boots", "Safety Vest"]).
  - "sign_bbox": [x1, y1, x2, y2] bounding box coordinates of the sign in pixel space.

Return ONLY valid JSON:
{
  "signs": [
    {
      "sign_id": "SIGN-01",
      "text": "DANGER DEMOLITION IN PROGRESS KEEP OUT",
      "text_ar": "خطر أعمال هدم جارية - ممنوع الاقتراب",
      "hazard_type": "restricted_area",
      "safety_distance_meters": 3.5,
      "required_ppe": ["Helmet", "Safety Boots"],
      "sign_bbox": [565, 130, 760, 320]
    }
  ]
}
"""


def compute_sign_hazard_polygon(
    sign_bbox: List[int],
    safety_distance_meters: float,
    standard_sign_height_m: float = STANDARD_SIGN_HEIGHT_METERS,
    perspective_ratio: float = 0.58,
    num_vertices: int = 16,
) -> np.ndarray:
    """
    Dynamically projects a ground-plane safety perimeter polygon around a signboard.

    Args:
        sign_bbox: [x1, y1, x2, y2] in pixels.
        safety_distance_meters: Radius in meters extracted from sign text.
        standard_sign_height_m: Known real-world physical height of industrial signs.
        perspective_ratio: Elliptical vertical compression factor for camera pitch perspective.
        num_vertices: Number of polygon vertices for smooth perimeter.

    Returns:
        np.ndarray of shape (num_vertices, 2) with int32 pixel coordinates.
    """
    x1, y1, x2, y2 = [int(v) for v in sign_bbox]
    sign_w = max(4, x2 - x1)
    sign_h = max(4, y2 - y1)

    # 1. Depth scale factor: pixels per meter at the sign's distance
    px_per_meter = max(8.0, sign_h / max(0.1, standard_sign_height_m))

    # 2. Safety radius in pixel space
    radius_x = max(20.0, float(safety_distance_meters) * px_per_meter)
    radius_y = max(12.0, radius_x * perspective_ratio)

    # 3. Ground plane anchor (projected directly beneath sign base)
    ground_anchor_x = (x1 + x2) // 2
    ground_anchor_y = y2 + int(sign_h * 0.45)

    # 4. Generate elliptical ground polygon
    polygon = []
    step = 2 * math.pi / num_vertices
    for i in range(num_vertices):
        angle = i * step
        px = int(ground_anchor_x + radius_x * math.cos(angle))
        py = int(ground_anchor_y + radius_y * math.sin(angle))
        polygon.append([px, py])

    return np.array(polygon, dtype=np.int32)


class SignHazardMonitor:
    """
    Manages safety signboard detection, VLM text parsing, ground zone projection,
    and worker perimeter intrusion monitoring.
    """

    def __init__(
        self,
        cache_path: Path = DEFAULT_SIGNS_CACHE,
        standard_sign_height_m: float = STANDARD_SIGN_HEIGHT_METERS,
    ):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.standard_sign_height_m = standard_sign_height_m
        self.signs: List[Dict] = []
        self.load_cache()

    def load_cache(self) -> List[Dict]:
        """Loads verified signboards from persistent JSON cache (0 tokens)."""
        if self.cache_path.exists():
            try:
                with self.cache_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    signs = data.get("signs", [])
                    for s in signs:
                        # Recompute numpy polygon from bbox & distance
                        s["hazard_polygon"] = compute_sign_hazard_polygon(
                            s["sign_bbox"],
                            s["safety_distance_meters"],
                            self.standard_sign_height_m,
                        )
                    self.signs = signs
                    LOG.info("Loaded %d safety signs from cache: %s", len(self.signs), self.cache_path)
                    return self.signs
            except Exception as exc:
                LOG.warning("Failed to load signs cache (%s); using default baseline.", exc)

        # Baseline seed signs representing standard Jubail industrial zones
        self.signs = self._get_default_seed_signs()
        self.save_cache()
        return self.signs

    def save_cache(self) -> None:
        """Saves current signboards to JSON cache without numpy arrays."""
        serializable = []
        for s in self.signs:
            item = {k: v for k, v in s.items() if k != "hazard_polygon"}
            if isinstance(item.get("sign_bbox"), (np.ndarray, list)):
                item["sign_bbox"] = [int(x) for x in item["sign_bbox"]]
            serializable.append(item)

        try:
            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump({"signs": serializable}, f, indent=2, ensure_ascii=False)
            LOG.info("Saved %d safety signs to cache: %s", len(serializable), self.cache_path)
        except Exception as exc:
            LOG.error("Failed to write signs cache: %s", exc)

    def _get_default_seed_signs(self) -> List[Dict]:
        """Realistic industrial safety signs with coordinates and calculated perimeters."""
        seeds = [
            {
                "sign_id": "SIGN-01",
                "text": "DANGER: HIGH VOLTAGE SUBSTATION - KEEP 5M CLEAR",
                "text_ar": "خطر: محطة ضغط عالي - ممنوع الاقتراب أقل من 5 أمتار",
                "hazard_type": "high_voltage",
                "safety_distance_meters": 5.0,
                "required_ppe": ["Insulated Gloves", "Safety Boots", "Helmet"],
                "sign_bbox": [180, 130, 245, 185],
            },
            {
                "sign_id": "SIGN-02",
                "text": "WARNING: FLAMMABLE CHEMICALS (METHANOL) - KEEP 4M CLEAR",
                "text_ar": "تحذير: مواد كيميائية سريعة الاشتعال - منطقة أمان 4 أمتار",
                "hazard_type": "flammable_materials",
                "safety_distance_meters": 4.0,
                "required_ppe": ["Face Shield", "Chemical Gloves", "Coverall"],
                "sign_bbox": [920, 140, 990, 195],
            },
            {
                "sign_id": "SIGN-03",
                "text": "CAUTION: OVERHEAD HOT WORK & WELDING ARC - 3.5M BUFFER",
                "text_ar": "انتباه: أعمال لحام علوية وإشعاع حراري - مسافة أمان 3.5 متر",
                "hazard_type": "welding_arc",
                "safety_distance_meters": 3.5,
                "required_ppe": ["Welding Helmet", "Leather Gloves"],
                "sign_bbox": [420, 110, 480, 160],
            },
        ]
        for s in seeds:
            s["hazard_polygon"] = compute_sign_hazard_polygon(
                s["sign_bbox"],
                s["safety_distance_meters"],
                self.standard_sign_height_m,
            )
        return seeds

    def scan_frame_with_vlm(self, frame: np.ndarray, force_rescan: bool = False) -> List[Dict]:
        """
        One-shot VLM scan of an initial scene frame to discover and read signs.
        If cache exists and force_rescan is False, returns cache immediately (0 tokens).
        """
        if self.signs and not force_rescan:
            return self.signs

        # Check for Gemini or OpenAI API keys
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if not gemini_key and not openai_key:
            LOG.info("No VLM API key configured; keeping verified signboard cache.")
            return self.signs

        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            return self.signs

        vlm_provider = os.getenv("VLM_PROVIDER", "openai").strip().lower()
        providers = ["openai", "gemini"] if vlm_provider == "openai" else ["gemini", "openai"]

        for provider in providers:
            if provider == "openai" and openai_key:
                try:
                    import base64
                    from openai import OpenAI
                    client = OpenAI(api_key=openai_key)
                    model_name = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
                    b64_img = base64.b64encode(encoded.tobytes()).decode("utf-8")

                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an industrial safety vision specialist. Output only valid json.",
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": VLM_SIGN_PROMPT},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                                ],
                            },
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                    )
                    content = response.choices[0].message.content
                    if content:
                        raw_json = json.loads(content)
                        extracted_signs = raw_json.get("signs", [])
                        if extracted_signs:
                            for s in extracted_signs:
                                s["hazard_polygon"] = compute_sign_hazard_polygon(
                                    s["sign_bbox"],
                                    s.get("safety_distance_meters", DEFAULT_HAZARD_DISTANCES.get(s.get("hazard_type"), 3.0)),
                                    self.standard_sign_height_m,
                                )
                            self.signs = extracted_signs
                            self.save_cache()
                            LOG.info("OpenAI VLM (%s) extracted %d signs from camera frame.", model_name, len(self.signs))
                            return self.signs
                except Exception as exc:
                    LOG.warning("OpenAI sign scanning failed (%s); trying fallback if available.", exc)

            elif provider == "gemini" and gemini_key:
                try:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=gemini_key)
                    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
                    response = client.models.generate_content(
                        model=gemini_model,
                        contents=[
                            VLM_SIGN_PROMPT,
                            types.Part.from_bytes(data=encoded.tobytes(), mime_type="image/jpeg"),
                        ],
                        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
                    )
                    raw_json = json.loads(response.text)
                    extracted_signs = raw_json.get("signs", [])
                    if extracted_signs:
                        for s in extracted_signs:
                            s["hazard_polygon"] = compute_sign_hazard_polygon(
                                s["sign_bbox"],
                                s.get("safety_distance_meters", DEFAULT_HAZARD_DISTANCES.get(s.get("hazard_type"), 3.5)),
                                self.standard_sign_height_m,
                            )
                        self.signs = extracted_signs
                        self.save_cache()
                        LOG.info("Gemini VLM (%s) extracted %d signs from camera frame.", gemini_model, len(self.signs))
                        return self.signs
                except Exception as exc:
                    LOG.warning("Gemini sign scanning failed (%s); keeping current signs.", exc)

        return self.signs

    def evaluate_persons(self, persons: List[Dict]) -> List[Dict]:
        """
        Checks if any person's foot-point breaches the calculated hazard polygon of any sign.

        Args:
            persons: List of tracked person dicts containing 'bbox' [x1, y1, x2, y2].

        Returns:
            List of detected sign perimeter violations.
        """
        violations = []
        for p in persons:
            bbox = p.get("bbox")
            if not bbox or len(bbox) != 4:
                continue

            # Bottom-center contact point on ground plane
            foot_x = int((bbox[0] + bbox[2]) / 2)
            foot_y = int(bbox[3])

            for sign in self.signs:
                poly = sign.get("hazard_polygon")
                if poly is None:
                    continue

                # Point-in-polygon test: >= 0 means inside or on edge
                if cv2.pointPolygonTest(poly, (foot_x, foot_y), False) >= 0:
                    hazard = sign.get("hazard_type", "general_warning")
                    is_critical = hazard in ("high_voltage", "flammable_materials", "toxic_gas", "radiation", "restricted_area")

                    role = p.get("role") or p.get("helmet_color") or "general_laborer"
                    carried_tools = p.get("carried_tools", [])
                    ppe_worn = p.get("ppe_worn", [])

                    zone_map = {
                        "high_voltage": "ZONE_SUBSTATION",
                        "flammable_materials": "ZONE_CHEMICAL",
                        "chemical_hazard": "ZONE_CHEMICAL",
                        "welding_arc": "ZONE_WELDING_BAY",
                        "restricted_area": "ZONE_SUPERVISED",
                        "excavation": "ZONE_SUPERVISED",
                    }
                    zone_id = zone_map.get(hazard, "ZONE_SUPERVISED")

                    try:
                        from tools.zone_access_matrix import ZoneAccessEngine
                        access_eval = ZoneAccessEngine().evaluate_access(
                            worker_role=role,
                            zone_id=zone_id,
                            carried_tools=carried_tools,
                            ppe_worn=ppe_worn,
                            worker_id=p.get("track_id"),
                        )
                        risk_score = access_eval.get("risk_score", 85.0 if is_critical else 60.0)
                        access_granted = access_eval.get("access_granted", False)
                        role_title = access_eval.get("role_title_en", "Worker")
                        role_title_ar = access_eval.get("role_title_ar", "عامل")
                    except Exception:
                        risk_score = 85.0 if is_critical else 60.0
                        access_granted = False
                        role_title = "Worker"
                        role_title_ar = "عامل"

                    violations.append({
                        "person_id": p.get("track_id"),
                        "person_bbox": bbox,
                        "sign_id": sign.get("sign_id"),
                        "sign_text": sign.get("text"),
                        "text_ar": sign.get("text_ar", sign.get("text")),
                        "hazard_type": hazard,
                        "safety_distance_meters": sign.get("safety_distance_meters"),
                        "required_ppe": sign.get("required_ppe", []),
                        "severity": "CRITICAL" if (is_critical or risk_score >= 75) else "WARNING",
                        "risk_score": risk_score,
                        "access_granted": access_granted,
                        "role": role_title,
                        "role_ar": role_title_ar,
                        "foot_point": [foot_x, foot_y],
                        "alert_message": (
                            f"{role_title} W-{p.get('track_id', '?')} breached {sign.get('safety_distance_meters')}m "
                            f"perimeter of sign [{sign.get('sign_id')}]: {sign.get('text')} (Risk: {risk_score}%)"
                        ),
                    })

        return violations

    def annotate(self, frame: np.ndarray, violations: Optional[List[Dict]] = None) -> np.ndarray:
        """
        Renders signboard bounding boxes, ground hazard polygons, and active breach alerts.
        """
        breached_sign_ids = {v["sign_id"] for v in (violations or [])}

        overlay = frame.copy()
        for sign in self.signs:
            poly = sign.get("hazard_polygon")
            sign_id = sign.get("sign_id", "")
            is_breached = sign_id in breached_sign_ids

            color = (0, 0, 255) if is_breached else (0, 165, 255)  # Red if breached, orange if safe

            # 1. Fill ground hazard polygon
            if poly is not None:
                cv2.fillPoly(overlay, [poly], color)
                cv2.polylines(frame, [poly], True, color, 2, cv2.LINE_AA)

            # 2. Draw signboard rectangle
            bbox = sign.get("sign_bbox")
            if bbox and len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (50, 220, 255), 2)
                # Label tag
                dist = sign.get("safety_distance_meters", 0)
                tag = f"{sign_id} [{dist}m BUFFER]"
                (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 6, y1), (20, 20, 25), -1)
                cv2.putText(frame, tag, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (50, 220, 255), 1, cv2.LINE_AA)

        # Blend ground overlay
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        # 3. Draw active breach badges (top-right corner)
        if violations:
            unique_breaches = {}
            for v in violations:
                if v["sign_id"] not in unique_breaches:
                    unique_breaches[v["sign_id"]] = v

            by = 30
            for s_id, v in list(unique_breaches.items())[:3]:
                tag = f"! BREACH: {s_id} ({v.get('safety_distance_meters')}m BUFFER) !"
                (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_DUPLEX, 0.46, 1)
                bx = frame.shape[1] - tw - 24
                # Red badge with border
                cv2.rectangle(frame, (bx - 8, by - th - 6), (bx + tw + 8, by + 6), (0, 0, 190), -1)
                cv2.rectangle(frame, (bx - 8, by - th - 6), (bx + tw + 8, by + 6), (255, 255, 255), 1)
                cv2.putText(frame, tag, (bx, by), cv2.FONT_HERSHEY_DUPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
                by += th + 16

        return frame

    def get_summary(self) -> Dict:
        """Returns JSON-serializable overview of all registered signs and their dynamic zones."""
        return {
            "total_signs": len(self.signs),
            "signs": [
                {
                    "sign_id": s.get("sign_id"),
                    "text": s.get("text"),
                    "text_ar": s.get("text_ar"),
                    "hazard_type": s.get("hazard_type"),
                    "safety_distance_meters": s.get("safety_distance_meters"),
                    "required_ppe": s.get("required_ppe", []),
                    "sign_bbox": [int(v) for v in s.get("sign_bbox", [])],
                    "polygon_vertices_count": len(s.get("hazard_polygon", [])),
                }
                for s in self.signs
            ],
            "standard_sign_height_m": self.standard_sign_height_m,
            "caching_strategy": "One-shot VLM scan + persistent local cache (0 token recurring cost)",
        }
