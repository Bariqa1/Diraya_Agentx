"""Unit tests for Sign Hazard Monitor, Dynamic Geofencing, and Chat Tool."""
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient

from tools.sign_hazard_monitor import (
    SignHazardMonitor,
    compute_sign_hazard_polygon,
    STANDARD_SIGN_HEIGHT_METERS,
)
from tools.chat_tools import get_sign_hazard_zones
from api_chat import app


class TestComputeSignHazardPolygon:
    def test_polygon_generation_shape(self):
        sign_bbox = [100, 100, 150, 150]
        safety_m = 5.0
        poly = compute_sign_hazard_polygon(sign_bbox, safety_m, num_vertices=16)

        assert isinstance(poly, np.ndarray)
        assert poly.shape == (16, 2)
        assert poly.dtype == np.int32

    def test_perspective_ground_anchor(self):
        sign_bbox = [200, 100, 300, 200]  # center_x = 250, bottom_y = 200, h = 100
        safety_m = 4.0
        poly = compute_sign_hazard_polygon(sign_bbox, safety_m)

        # Polygon centroid Y should be below the bottom edge of the sign
        mean_y = np.mean(poly[:, 1])
        assert mean_y > 200

    def test_depth_scaling(self):
        # Far sign (small height: 20px) vs Close sign (large height: 100px)
        far_poly = compute_sign_hazard_polygon([50, 50, 70, 70], 5.0)      # h = 20
        close_poly = compute_sign_hazard_polygon([200, 200, 300, 300], 5.0) # h = 100

        far_span_x = np.max(far_poly[:, 0]) - np.min(far_poly[:, 0])
        close_span_x = np.max(close_poly[:, 0]) - np.min(close_poly[:, 0])

        assert close_span_x > far_span_x


class TestSignHazardMonitor:
    def test_cache_initialization(self, tmp_path):
        cache_file = tmp_path / "test_signs.json"
        monitor = SignHazardMonitor(cache_path=cache_file)

        assert len(monitor.signs) >= 3
        assert cache_file.exists()

        # Reload from cache
        monitor2 = SignHazardMonitor(cache_path=cache_file)
        assert len(monitor2.signs) == len(monitor.signs)
        assert monitor2.signs[0]["sign_id"] == monitor.signs[0]["sign_id"]

    def test_evaluate_persons_breach_detection(self, tmp_path):
        cache_file = tmp_path / "signs.json"
        monitor = SignHazardMonitor(cache_path=cache_file)

        # First sign is SIGN-01 [180, 130, 245, 185] with 5m buffer
        sign0 = monitor.signs[0]
        poly = sign0["hazard_polygon"]
        centroid_x = int(np.mean(poly[:, 0]))
        centroid_y = int(np.mean(poly[:, 1]))

        # Person inside the danger zone
        inside_person = {
            "track_id": 101,
            "bbox": [centroid_x - 15, centroid_y - 80, centroid_x + 15, centroid_y],
        }

        # Person far away (safe)
        outside_person = {
            "track_id": 102,
            "bbox": [1500, 1500, 1530, 1600],
        }

        violations = monitor.evaluate_persons([inside_person, outside_person])
        assert len(violations) >= 1
        v = violations[0]
        assert v["person_id"] == 101
        assert v["sign_id"] == sign0["sign_id"]
        assert "CRITICAL" in v["severity"] or "WARNING" in v["severity"]
        assert "breached" in v["alert_message"].lower()

    def test_annotate_rendering(self, tmp_path):
        cache_file = tmp_path / "signs.json"
        monitor = SignHazardMonitor(cache_path=cache_file)
        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        annotated = monitor.annotate(dummy_frame)
        assert annotated.shape == (720, 1280, 3)

        # With breach alert
        violations = [{
            "sign_id": "SIGN-01",
            "safety_distance_meters": 5.0,
        }]
        annotated_breach = monitor.annotate(dummy_frame, violations=violations)
        assert annotated_breach.shape == (720, 1280, 3)

    def test_zero_token_scan_frame(self, tmp_path):
        cache_file = tmp_path / "signs.json"
        monitor = SignHazardMonitor(cache_path=cache_file)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Should return cached signs immediately without calling external API
        signs = monitor.scan_frame_with_vlm(dummy_frame, force_rescan=False)
        assert len(signs) == len(monitor.signs)


class TestChatToolIntegration:
    def test_get_sign_hazard_zones_all(self):
        raw = get_sign_hazard_zones()
        data = json.loads(raw)

        assert "total_signs" in data
        assert data["total_signs"] >= 3
        assert "caching_strategy" in data

    def test_get_sign_hazard_zones_specific(self):
        raw = get_sign_hazard_zones(sign_id="SIGN-01")
        data = json.loads(raw)

        assert "sign" in data
        assert data["sign"]["sign_id"] == "SIGN-01"
        assert data["sign"]["safety_distance_meters"] > 0
        assert "hazard_type" in data["sign"]

    def test_get_sign_hazard_zones_not_found(self):
        raw = get_sign_hazard_zones(sign_id="NON_EXISTENT_999")
        data = json.loads(raw)

        assert "error" in data
        assert "available_signs" in data


class TestApiChatSignEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_signs_hazards(self, client):
        response = client.get("/signs/hazards")
        assert response.status_code == 200
        data = response.json()
        assert "total_signs" in data
        assert data["total_signs"] >= 3

    def test_get_sign_by_id(self, client):
        response = client.get("/signs/hazards?sign_id=SIGN-01")
        assert response.status_code == 200
        data = response.json()
        assert data["sign_id"] == "SIGN-01"

    def test_get_sign_not_found(self, client):
        response = client.get("/signs/hazards?sign_id=UNKNOWN_SIGN")
        assert response.status_code == 404

    def test_post_signs_evaluate(self, client):
        # Safe person far outside
        payload_safe = {
            "persons": [{"track_id": 99, "bbox": [1800, 1800, 1850, 1950]}]
        }
        res_safe = client.post("/signs/evaluate", json=payload_safe)
        assert res_safe.status_code == 200
        assert res_safe.json()["has_breach"] is False
        assert res_safe.json()["total_violations"] == 0

        # Person inside SIGN-01 zone (anchor is around x=212, y=210)
        payload_breach = {
            "persons": [{"track_id": 1, "bbox": [200, 130, 225, 210]}]
        }
        res_breach = client.post("/signs/evaluate", json=payload_breach)
        assert res_breach.status_code == 200
        assert res_breach.json()["has_breach"] is True
        assert res_breach.json()["total_violations"] >= 1
