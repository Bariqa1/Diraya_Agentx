"""Role-Based Zone Access Control & Dynamic Risk Scoring Engine for DIRAYA.

Implements industrial physical RBAC (Role-Based Access Control):
1. Role classification via standard helmet colors (OSHA / Saudi Aramco / SABIC standards).
2. Carried equipment & tools safety profiling.
3. Physical zone clearance policies (No-Go / Red Zones, Restricted Qualified, Supervised).
4. Dynamic risk scoring engine (0% to 100%) with severity grading and alert dispatch actions.
"""
import logging
from typing import Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

LOG = logging.getLogger(__name__)

# ==============================================================================
# 1. STANDARDIZED INDUSTRIAL HELMET COLORS & ROLES
# ==============================================================================

HELMET_ROLES = {
    "WHITE": {
        "role_id": "engineer_supervisor",
        "title_en": "Site Engineer / Supervisor",
        "title_ar": "مهندس موقع / مشرف",
        "clearance_level": 4,
        "default_allowed_zones": ["ZONE_SUPERVISED", "ZONE_CHEMICAL", "ZONE_SUBSTATION", "ZONE_GENERAL"],
        "description": "Authorized for inspection, oversight, and project management.",
    },
    "BLUE": {
        "role_id": "technician_electrician",
        "title_en": "Certified Technician / Electrician",
        "title_ar": "فني متخصص / كهربائي",
        "clearance_level": 3,
        "default_allowed_zones": ["ZONE_SUBSTATION", "ZONE_CHEMICAL", "ZONE_SUPERVISED", "ZONE_GENERAL"],
        "description": "Authorized for technical maintenance, electrical isolation, and machinery repairs.",
    },
    "YELLOW": {
        "role_id": "general_laborer",
        "title_en": "General Laborer / Operator",
        "title_ar": "عامل تشييد / مشغل معدات",
        "clearance_level": 1,
        "default_allowed_zones": ["ZONE_GENERAL", "ZONE_SUPERVISED"],
        "description": "General construction, material handling, and equipment operation under supervision.",
    },
    "RED": {
        "role_id": "safety_fire_officer",
        "title_en": "HSE / Fire Safety Officer",
        "title_ar": "مسؤول سلامة / إطفاء وطوارئ",
        "clearance_level": 5,
        "default_allowed_zones": ["ZONE_SUPERVISED", "ZONE_CHEMICAL", "ZONE_SUBSTATION", "ZONE_GENERAL"],
        "description": "Emergency response, safety compliance audit, and fire watch oversight.",
    },
    "GREEN": {
        "role_id": "safety_inspector_trainee",
        "title_en": "Safety Inspector / Trainee",
        "title_ar": "مفتش جودة وسلامة / متدرب",
        "clearance_level": 2,
        "default_allowed_zones": ["ZONE_GENERAL", "ZONE_SUPERVISED"],
        "description": "Environmental safety inspection and site walk-through audits.",
    },
    "UNKNOWN": {
        "role_id": "unidentified_visitor",
        "title_en": "Unidentified Worker / Visitor",
        "title_ar": "عامل غير معروف / زائر",
        "clearance_level": 0,
        "default_allowed_zones": ["ZONE_GENERAL"],
        "description": "Restricted to general visitor areas; prohibited from hazardous work zones.",
    },
}


def classify_helmet_color(image_or_bgr: Union[np.ndarray, Tuple[int, int, int], List[int]]) -> str:
    """
    Classifies helmet color using dominant RGB/HSV color profile.
    Accepts either an image crop (np.ndarray of shape HxWx3) or an average BGR tuple.

    Returns:
        One of ["WHITE", "BLUE", "YELLOW", "RED", "GREEN", "UNKNOWN"].
    """
    if isinstance(image_or_bgr, np.ndarray) and image_or_bgr.ndim == 3 and image_or_bgr.size > 0:
        # Calculate mean BGR from non-zero / valid pixels
        mean_bgr = cv2.mean(image_or_bgr)[:3]
        b, g, r = mean_bgr
        hsv = cv2.cvtColor(np.uint8([[mean_bgr]]), cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
    elif isinstance(image_or_bgr, (list, tuple)) and len(image_or_bgr) >= 3:
        b, g, r = float(image_or_bgr[0]), float(image_or_bgr[1]), float(image_or_bgr[2])
        mean_bgr = (b, g, r)
        hsv = cv2.cvtColor(np.uint8([[mean_bgr]]), cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
    else:
        return "UNKNOWN"

    # White: High brightness (V), very low saturation (S)
    if v > 185 and s < 50:
        return "WHITE"

    # Red: Hue near 0-10 or 170-180 with moderate-high saturation
    if (h < 12 or h > 165) and s > 80 and v > 60:
        return "RED"

    # Yellow: Hue around 18-38 with high brightness and saturation
    if 15 <= h <= 42 and s > 70 and v > 100:
        return "YELLOW"

    # Green: Hue around 40-85
    if 43 <= h <= 88 and s > 50 and v > 50:
        return "GREEN"

    # Blue: Hue around 90-135 with good saturation
    if 90 <= h <= 135 and s > 60 and v > 50:
        return "BLUE"

    # Fallback heuristic using raw BGR ratios
    if r > 190 and g > 190 and b > 190:
        return "WHITE"
    if b > 130 and b > r + 30:
        return "BLUE"
    if r > 160 and g > 130 and b < 100:
        return "YELLOW"
    if r > 160 and r > g + 40 and r > b + 40:
        return "RED"
    if g > 140 and g > r + 20 and g > b + 20:
        return "GREEN"

    return "UNKNOWN"


def get_role_from_helmet_color(color_name: str) -> Dict:
    """Returns standardized role info from a classified helmet color."""
    key = str(color_name).upper().strip()
    return HELMET_ROLES.get(key, HELMET_ROLES["UNKNOWN"])


# ==============================================================================
# 2. CARRIED TOOLS & EQUIPMENT TAXONOMY
# ==============================================================================

CARRIED_TOOLS_TAXONOMY = {
    "insulated_toolkit": {
        "name": "Insulated Electrical Tool Kit (1000V rated)",
        "compatible_zones": ["ZONE_SUBSTATION", "ZONE_SUPERVISED", "ZONE_GENERAL"],
        "hazardous_if_unauthorized": False,
        "is_protective_gear": True,
    },
    "gas_cylinder": {
        "name": "Pressurized Flammable Gas Cylinder",
        "compatible_zones": ["ZONE_WELDING_BAY"],
        "hazardous_if_unauthorized": True,
        "hazard_risk_penalty": 25,
    },
    "welding_torch": {
        "name": "Welding Torch / Hot Work Equipment",
        "compatible_zones": ["ZONE_WELDING_BAY"],
        "hazardous_if_unauthorized": True,
        "hazard_risk_penalty": 20,
    },
    "tablet_clipboard": {
        "name": "Inspection Tablet / Digital Clipboard",
        "compatible_zones": ["ZONE_SUPERVISED", "ZONE_CHEMICAL", "ZONE_SUBSTATION", "ZONE_GENERAL"],
        "hazardous_if_unauthorized": False,
    },
    "general_toolbox": {
        "name": "Mechanical Toolbox",
        "compatible_zones": ["ZONE_GENERAL", "ZONE_SUPERVISED", "ZONE_CHEMICAL"],
        "hazardous_if_unauthorized": False,
    },
    "ladder": {
        "name": "Mobile Step Ladder",
        "compatible_zones": ["ZONE_GENERAL", "ZONE_SUPERVISED"],
        "hazardous_if_unauthorized": False,
        "requires_ppe": ["Safety Harness"],
    },
}


# ==============================================================================
# 3. ZONE ACCESS & RESTRICTION MATRIX (RBAC POLICIES)
# ==============================================================================

ZONE_ACCESS_MATRIX = {
    "ZONE_NO_GO_CRANE": {
        "zone_id": "ZONE_NO_GO_CRANE",
        "name_en": "Crane Active Lifting & Load Drop Zone",
        "name_ar": "منطقة الرفع النشط ومسار الرافعة (محظورة كلياً)",
        "zone_type": "NO_GO",
        "base_risk": 100,
        "allowed_roles": [],  # Forbidden for EVERYONE!
        "forbidden_roles": ["ALL"],
        "required_ppe": [],
        "siren_trigger": True,
        "description": "Zero tolerance overhead suspension hazard. No personnel permitted under suspended load.",
    },
    "ZONE_SUBSTATION": {
        "zone_id": "ZONE_SUBSTATION",
        "name_en": "High Voltage Substation & Switchgear Room (13.8kV)",
        "name_ar": "غرفة محولات الضغط العالي وقواطع الكهرباء",
        "zone_type": "RESTRICTED_QUALIFIED",
        "base_risk": 45,
        "allowed_roles": ["technician_electrician", "engineer_supervisor", "safety_fire_officer"],
        "forbidden_roles": ["general_laborer", "safety_inspector_trainee", "unidentified_visitor"],
        "required_ppe": ["Insulated Gloves", "Hard Hat", "Safety Boots", "Safety Glasses"],
        "required_tools": ["insulated_toolkit"],
        "siren_trigger": False,
        "description": "High voltage arc flash risk. Certified electricians and authorized supervisors only.",
    },
    "ZONE_CHEMICAL": {
        "zone_id": "ZONE_CHEMICAL",
        "name_en": "Hazardous Chemical Reaction Unit (U-200)",
        "name_ar": "وحدة التفاعلات والمذيبات الكيميائية الخطرة",
        "zone_type": "RESTRICTED_QUALIFIED",
        "base_risk": 40,
        "allowed_roles": ["technician_electrician", "engineer_supervisor", "safety_fire_officer"],
        "forbidden_roles": ["general_laborer", "unidentified_visitor"],
        "required_ppe": ["Face Shield", "Chemical Gloves", "Hard Hat", "Coverall"],
        "siren_trigger": False,
        "description": "Toxic gas / corrosive chemical splash risk. Requires full chemical PPE.",
    },
    "ZONE_WELDING_BAY": {
        "zone_id": "ZONE_WELDING_BAY",
        "name_en": "Heavy Fabrication & Welding Bay",
        "name_ar": "منطقة اللحام والأعمال الساخنة",
        "zone_type": "RESTRICTED_QUALIFIED",
        "base_risk": 35,
        "allowed_roles": ["general_laborer", "technician_electrician", "engineer_supervisor", "safety_fire_officer"],
        "forbidden_roles": ["unidentified_visitor"],
        "required_ppe": ["Welding Helmet", "Leather Gloves", "Safety Boots"],
        "siren_trigger": False,
        "description": "UV arc radiation and molten spatter. Welding protection required.",
    },
    "ZONE_SUPERVISED": {
        "zone_id": "ZONE_SUPERVISED",
        "name_en": "Scaffolding Erection & Working-at-Height Zone",
        "name_ar": "منطقة أعمال السقالات والعمل على ارتفاعات",
        "zone_type": "SUPERVISED",
        "base_risk": 25,
        "allowed_roles": ["general_laborer", "technician_electrician", "engineer_supervisor", "safety_fire_officer", "safety_inspector_trainee"],
        "forbidden_roles": ["unidentified_visitor"],
        "required_ppe": ["Safety Harness", "Hard Hat", "Safety Boots"],
        "siren_trigger": False,
        "description": "Elevated fall hazard zone. Mandatory 100% tie-off safety harness.",
    },
    "ZONE_GENERAL": {
        "zone_id": "ZONE_GENERAL",
        "name_en": "General Construction & Staging Area",
        "name_ar": "الساحة العامة ومنطقة التحضير والتخزين",
        "zone_type": "GENERAL",
        "base_risk": 10,
        "allowed_roles": ["ALL"],
        "forbidden_roles": [],
        "required_ppe": ["Hard Hat", "Safety Vest", "Safety Boots"],
        "siren_trigger": False,
        "description": "Standard industrial staging area. Basic PPE required.",
    },
}


# ==============================================================================
# 4. DYNAMIC RISK SCORING ENGINE
# ==============================================================================

class ZoneAccessEngine:
    """
    Evaluates worker authorization, role clearance, carried tools, and PPE
    against physical geofenced zones and calculates dynamic risk (0-100%).
    """

    def __init__(self, matrix: Optional[Dict] = None):
        self.matrix = matrix or ZONE_ACCESS_MATRIX

    def normalize_role_id(self, role_input: str) -> str:
        """Normalizes any role string, title, or helmet color to standard role_id."""
        val = str(role_input).strip().lower()

        # Check direct helmet color names
        if val.upper() in HELMET_ROLES:
            return HELMET_ROLES[val.upper()]["role_id"]

        # Check role_id or titles
        for col, info in HELMET_ROLES.items():
            if val == info["role_id"] or val in info["title_en"].lower() or val in info["title_ar"]:
                return info["role_id"]

        # Keyword matching
        if any(k in val for k in ["eng", "superv", "مدير", "مهندس", "مشرف"]):
            return "engineer_supervisor"
        if any(k in val for k in ["tech", "electr", "فني", "كهرب"]):
            return "technician_electrician"
        if any(k in val for k in ["labor", "work", "operat", "عامل", "مشغل"]):
            return "general_laborer"
        if any(k in val for k in ["safe", "hse", "fire", "سلامة", "اطفاء", "إطفاء"]):
            return "safety_fire_officer"
        if any(k in val for k in ["inspect", "train", "مفتش", "متدرب"]):
            return "safety_inspector_trainee"

        return "unidentified_visitor"

    def evaluate_access(
        self,
        worker_role: str,
        zone_id: str,
        carried_tools: Optional[List[str]] = None,
        ppe_worn: Optional[List[str]] = None,
        worker_id: Optional[Union[str, int]] = None,
    ) -> Dict:
        """
        Computes dynamic risk score and access decision.

        Args:
            worker_role: Role name, title, or helmet color (e.g. 'Blue', 'electrician', 'engineer').
            zone_id: Target zone ID (e.g. 'ZONE_SUBSTATION', 'ZONE_NO_GO_CRANE').
            carried_tools: Optional list of tools carried (e.g. ['insulated_toolkit', 'gas_cylinder']).
            ppe_worn: List of PPE currently detected on the worker.
            worker_id: Optional worker identifier.

        Returns:
            Dict containing risk_score (0-100), severity, access_granted, missing_ppe,
            unauthorized_tools, and alert message.
        """
        target_zone_id = zone_id.strip().upper()
        zone = self.matrix.get(target_zone_id)

        # Fallback if zone ID not found
        if not zone:
            # Try fuzzy match
            for zid, zinfo in self.matrix.items():
                if zid in target_zone_id or target_zone_id in zid:
                    zone = zinfo
                    target_zone_id = zid
                    break

        if not zone:
            return {
                "error": f"Zone '{zone_id}' not found in Access Matrix.",
                "available_zones": list(self.matrix.keys()),
            }

        norm_role = self.normalize_role_id(worker_role)
        role_meta = next((v for v in HELMET_ROLES.values() if v["role_id"] == norm_role), HELMET_ROLES["UNKNOWN"])
        tools = carried_tools or []
        ppe = [p.strip().lower() for p in (ppe_worn or [])]

        # -------------------------------------------------------------
        # CASE 1: NO-GO / RED ZONE (Strict Zero-Tolerance)
        # -------------------------------------------------------------
        if zone.get("zone_type") == "NO_GO":
            return {
                "worker_id": worker_id or "W-UNKNOWN",
                "role_id": norm_role,
                "role_title_en": role_meta["title_en"],
                "role_title_ar": role_meta["title_ar"],
                "zone_id": target_zone_id,
                "zone_name_en": zone["name_en"],
                "zone_name_ar": zone["name_ar"],
                "zone_type": "NO_GO",
                "access_granted": False,
                "risk_score": 100.0,
                "severity": "CRITICAL",
                "action_required": "SIREN_IMMEDIATE_EVACUATION",
                "alert_message_en": (
                    f"CRITICAL RED ZONE BREACH: Worker {worker_id or ''} ({role_meta['title_en']}) entered "
                    f"strictly prohibited zone [{zone['name_en']}]. Evacuate immediately!"
                ),
                "alert_message_ar": (
                    f"خطر داهم: دخول منطقة محظورة كلياً [{zone['name_ar']}] بواسطة ({role_meta['title_ar']}). "
                    f"إخلاء فوري وتشغيل صافرة الإنذار!"
                ),
            }

        # -------------------------------------------------------------
        # CASE 2: CALCULATE DYNAMIC RISK SCORE
        # -------------------------------------------------------------
        risk_score = float(zone.get("base_risk", 20))
        reasons = []
        is_role_authorized = True

        # 1. Role Authorization Check
        allowed_roles = zone.get("allowed_roles", [])
        forbidden_roles = zone.get("forbidden_roles", [])

        if "ALL" in allowed_roles:
            is_role_authorized = True
        elif norm_role in forbidden_roles or (allowed_roles and norm_role not in allowed_roles):
            is_role_authorized = False
            penalty = 40.0
            risk_score += penalty
            reasons.append(f"Role unauthorized (+{int(penalty)}%): {role_meta['title_en']} not cleared for {zone['name_en']}")

        # 2. PPE Verification Check
        missing_ppe = []
        for req in zone.get("required_ppe", []):
            if not any(req.lower() in p or p in req.lower() for p in ppe):
                missing_ppe.append(req)

        if missing_ppe:
            ppe_penalty = min(30.0, len(missing_ppe) * 12.0)
            risk_score += ppe_penalty
            reasons.append(f"Missing mandatory PPE (+{int(ppe_penalty)}%): {', '.join(missing_ppe)}")

        # 3. Carried Tools & Hazardous Equipment Check
        unauthorized_tools = []
        for tool in tools:
            tool_key = tool.lower().replace(" ", "_")
            tool_meta = CARRIED_TOOLS_TAXONOMY.get(tool_key)
            if tool_meta:
                if target_zone_id not in tool_meta.get("compatible_zones", []):
                    if tool_meta.get("hazardous_if_unauthorized"):
                        pen = tool_meta.get("hazard_risk_penalty", 20)
                        risk_score += pen
                        unauthorized_tools.append(tool_meta["name"])
                        reasons.append(f"Hazardous tool mismatch (+{pen}%): {tool_meta['name']}")

        # 4. Check Mandatory Tools Required by Zone (e.g. Insulated kit for Substation)
        missing_mandatory_tools = []
        for req_t in zone.get("required_tools", []):
            if not any(req_t in t.lower().replace(" ", "_") for t in tools):
                missing_mandatory_tools.append(req_t)
                risk_score += 15.0
                reasons.append(f"Missing safety-rated tool (+15%): {req_t}")

        # Clamp risk score to [0, 100]
        risk_score = round(max(0.0, min(100.0, risk_score)), 1)

        # Determine severity & action
        if risk_score >= 75.0 or not is_role_authorized:
            severity = "CRITICAL"
            access_granted = False
            action = "DENY_ACCESS_DISPATCH_ALERT"
        elif risk_score >= 45.0 or missing_ppe:
            severity = "WARNING"
            access_granted = False if not is_role_authorized else True
            action = "WARN_REQUIRE_PPE"
        elif risk_score >= 25.0:
            severity = "LOW"
            access_granted = True
            action = "PERMIT_WITH_ADVISORY"
        else:
            severity = "SAFE"
            access_granted = True
            action = "ACCESS_GRANTED"

        # Generate messages
        if access_granted and not missing_ppe:
            msg_en = f"Access Granted: {role_meta['title_en']} cleared for {zone['name_en']} (Risk: {risk_score}%)."
            msg_ar = f"تصريح دخول معتمد: ({role_meta['title_ar']}) مصرح له بالتواجد في [{zone['name_ar']}] (مستوى الخطر: {risk_score}%)."
        elif access_granted and missing_ppe:
            msg_en = f"Conditional Access: {role_meta['title_en']} authorized, but missing PPE: {', '.join(missing_ppe)} (Risk: {risk_score}%)."
            msg_ar = f"دخول مشروط: ({role_meta['title_ar']}) مصرح له لكن تنقصه معدات وقاية: {', '.join(missing_ppe)} (مستوى الخطر: {risk_score}%)."
        else:
            msg_en = f"SECURITY BREACH: {role_meta['title_en']} unauthorized for {zone['name_en']}! {'; '.join(reasons)} (Risk: {risk_score}%)."
            msg_ar = f"مخالفة أمن وسلامة: ({role_meta['title_ar']}) غير مصرح له بدخول [{zone['name_ar']}]! {'; '.join(reasons)} (مستوى الخطر: {risk_score}%)."

        return {
            "worker_id": worker_id or "W-UNKNOWN",
            "role_id": norm_role,
            "role_title_en": role_meta["title_en"],
            "role_title_ar": role_meta["title_ar"],
            "zone_id": target_zone_id,
            "zone_name_en": zone["name_en"],
            "zone_name_ar": zone["name_ar"],
            "zone_type": zone.get("zone_type", "RESTRICTED"),
            "access_granted": access_granted,
            "risk_score": risk_score,
            "severity": severity,
            "action_required": action,
            "is_role_authorized": is_role_authorized,
            "missing_ppe": missing_ppe,
            "unauthorized_tools": unauthorized_tools,
            "missing_mandatory_tools": missing_mandatory_tools,
            "risk_reasons": reasons,
            "alert_message_en": msg_en,
            "alert_message_ar": msg_ar,
        }

    def get_matrix_summary(self) -> Dict:
        """Returns clean overview of all physical zones and role permissions."""
        return {
            "total_zones": len(self.matrix),
            "zones": [
                {
                    "zone_id": z["zone_id"],
                    "name_en": z["name_en"],
                    "name_ar": z["name_ar"],
                    "zone_type": z["zone_type"],
                    "base_risk": z["base_risk"],
                    "allowed_roles": z["allowed_roles"],
                    "forbidden_roles": z["forbidden_roles"],
                    "required_ppe": z["required_ppe"],
                    "required_tools": z.get("required_tools", []),
                    "description": z["description"],
                }
                for z in self.matrix.values()
            ],
            "standard_helmet_roles": {
                color: {
                    "role_id": info["role_id"],
                    "title_en": info["title_en"],
                    "title_ar": info["title_ar"],
                    "clearance_level": info["clearance_level"],
                }
                for color, info in HELMET_ROLES.items()
            },
        }
