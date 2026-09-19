"""Unit tests for Role-Based Zone Access Control & Dynamic Risk Scoring."""
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient

from tools.zone_access_matrix import (
    classify_helmet_color,
    get_role_from_helmet_color,
    ZoneAccessEngine,
    ZONE_ACCESS_MATRIX,
    HELMET_ROLES,
)
from tools.chat_tools import evaluate_zone_access, get_zone_access_matrix
from api_chat import app


class TestHelmetColorClassification:
    def test_white_helmet_bgr(self):
        # BGR (245, 245, 245)
        color = classify_helmet_color((245, 245, 245))
        assert color == "WHITE"
        role = get_role_from_helmet_color(color)
        assert role["role_id"] == "engineer_supervisor"
        assert role["clearance_level"] >= 4

    def test_blue_helmet_bgr(self):
        # BGR (220, 130, 20)
        color = classify_helmet_color((220, 130, 20))
        assert color == "BLUE"
        role = get_role_from_helmet_color(color)
        assert role["role_id"] == "technician_electrician"

    def test_yellow_helmet_bgr(self):
        # BGR (30, 210, 255)
        color = classify_helmet_color((30, 210, 255))
        assert color == "YELLOW"
        role = get_role_from_helmet_color(color)
        assert role["role_id"] == "general_laborer"

    def test_red_helmet_bgr(self):
        # BGR (20, 20, 220)
        color = classify_helmet_color((20, 20, 220))
        assert color == "RED"
        role = get_role_from_helmet_color(color)
        assert role["role_id"] == "safety_fire_officer"

    def test_green_helmet_bgr(self):
        # BGR (50, 220, 50)
        color = classify_helmet_color((50, 220, 50))
        assert color == "GREEN"
        role = get_role_from_helmet_color(color)
        assert role["role_id"] == "safety_inspector_trainee"

    def test_crop_numpy_array(self):
        # 20x20 yellow crop in BGR
        crop = np.full((20, 20, 3), (30, 210, 255), dtype=np.uint8)
        assert classify_helmet_color(crop) == "YELLOW"


class TestZoneAccessEngine:
    @pytest.fixture
    def engine(self):
        return ZoneAccessEngine()

    def test_no_go_zone_forbidden_for_everyone(self, engine):
        # Even a senior engineer is forbidden under the crane load
        res = engine.evaluate_access(
            worker_role="WHITE",
            zone_id="ZONE_NO_GO_CRANE",
            worker_id="ENG-101",
        )
        assert res["access_granted"] is False
        assert res["risk_score"] == 100.0
        assert res["severity"] == "CRITICAL"
        assert res["action_required"] == "SIREN_IMMEDIATE_EVACUATION"
        assert "RED ZONE" in res["alert_message_en"]

    def test_restricted_zone_authorized_technician(self, engine):
        # Qualified electrical technician entering Substation with full PPE and insulated kit
        res = engine.evaluate_access(
            worker_role="BLUE",
            zone_id="ZONE_SUBSTATION",
            carried_tools=["insulated_toolkit"],
            ppe_worn=["Insulated Gloves", "Hard Hat", "Safety Boots", "Safety Glasses"],
            worker_id="TECH-42",
        )
        assert res["access_granted"] is True
        assert res["is_role_authorized"] is True
        assert res["missing_ppe"] == []
        assert res["risk_score"] <= 50.0

    def test_restricted_zone_unauthorized_laborer_breach(self, engine):
        # General laborer attempting entry into high voltage substation
        res = engine.evaluate_access(
            worker_role="YELLOW",
            zone_id="ZONE_SUBSTATION",
            worker_id="LABOR-07",
        )
        assert res["access_granted"] is False
        assert res["is_role_authorized"] is False
        assert res["risk_score"] >= 80.0
        assert res["severity"] == "CRITICAL"
        assert "DENY_ACCESS" in res["action_required"]

    def test_missing_ppe_penalty(self, engine):
        # Technician authorized, but forgot insulated gloves
        res = engine.evaluate_access(
            worker_role="technician_electrician",
            zone_id="ZONE_SUBSTATION",
            carried_tools=["insulated_toolkit"],
            ppe_worn=["Hard Hat", "Safety Boots"],
        )
        assert "Insulated Gloves" in res["missing_ppe"]
        assert res["risk_score"] > 45.0  # Base 45 + penalty
        assert res["severity"] == "WARNING"

    def test_hazardous_tool_mismatch(self, engine):
        # Worker carrying flammable gas cylinder into electrical substation
        res = engine.evaluate_access(
            worker_role="technician_electrician",
            zone_id="ZONE_SUBSTATION",
            carried_tools=["gas_cylinder"],
        )
        assert len(res["unauthorized_tools"]) > 0
        assert any("flammable gas" in t.lower() for t in res["unauthorized_tools"])


class TestChatToolsZoneAccess:
    def test_evaluate_zone_access_tool(self):
        raw = evaluate_zone_access(worker_role="Blue", zone_id="ZONE_SUBSTATION")
        data = json.loads(raw)
        assert "risk_score" in data
        assert "access_granted" in data

    def test_get_zone_access_matrix_all(self):
        raw = get_zone_access_matrix()
        data = json.loads(raw)
        assert "total_zones" in data
        assert data["total_zones"] >= 5
        assert "standard_helmet_roles" in data

    def test_get_zone_access_matrix_specific(self):
        raw = get_zone_access_matrix(zone_id="ZONE_SUBSTATION")
        data = json.loads(raw)
        assert data["zone_id"] == "ZONE_SUBSTATION"
        assert "technician_electrician" in data["allowed_roles"]


class TestApiChatZoneEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_matrix(self, client):
        res = client.get("/zones/access-matrix")
        assert res.status_code == 200
        assert res.json()["total_zones"] >= 5

    def test_get_matrix_specific_zone(self, client):
        res = client.get("/zones/access-matrix?zone_id=ZONE_NO_GO_CRANE")
        assert res.status_code == 200
        assert res.json()["zone_type"] == "NO_GO"

    def test_post_evaluate_access_authorized(self, client):
        payload = {
            "worker_role": "electrician",
            "zone_id": "ZONE_SUBSTATION",
            "carried_tools": ["insulated_toolkit"],
            "ppe_worn": ["Insulated Gloves", "Hard Hat", "Safety Boots", "Safety Glasses"],
        }
        res = client.post("/zones/evaluate-access", json=payload)
        assert res.status_code == 200
        assert res.json()["access_granted"] is True

    def test_post_evaluate_access_unauthorized(self, client):
        payload = {
            "worker_role": "laborer",
            "zone_id": "ZONE_SUBSTATION",
        }
        res = client.post("/zones/evaluate-access", json=payload)
        assert res.status_code == 200
        assert res.json()["access_granted"] is False
        assert res.json()["risk_score"] >= 80.0
