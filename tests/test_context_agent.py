import unittest
import numpy as np
import threading
from unittest.mock import MagicMock
from agents.context_agent import ContextAgent


class TestContextAgent(unittest.TestCase):
    def setUp(self):
        self.mock_ppe = MagicMock()
        self.mock_ppe.detect.return_value = {"detections": [{"class": "Helmet", "confidence": 0.9}], "confidence": 0.9}
        self.mock_context_tool = MagicMock()
        self.mock_context_tool.analyze.return_value = {
            "task": "welding",
            "tools": ["torch"],
            "equipment": ["welder"],
            "environment": "workshop",
            "confidence": 0.95,
        }
        self.mock_zone = MagicMock()
        self.mock_zone.detect_people.return_value = [
            {"bbox": [10, 10, 50, 90], "confidence": 0.9, "track_id": 1}
        ]
        self.mock_zone.evaluate_zone.return_value = {
            "persons": [{"bbox": [10, 10, 50, 90], "confidence": 0.9,
                         "track_id": 1, "inside_restricted_zone": False}],
            "violation": False,
        }
        self.mock_fall = MagicMock()
        self.mock_fall.detect.return_value = {"detected": False, "detections": [], "confidence": None}

        self.agent = ContextAgent(
            ppe_detector=self.mock_ppe,
            context_tool=self.mock_context_tool,
            zone_monitor=self.mock_zone,
            fall_detector=self.mock_fall,
            cache_ttl=10.0,
            failure_cooldown=5.0,
        )

        # Standard 3-channel dummy BGR frame
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)

    def test_first_frame_invokes_vlm(self):
        obs = self.agent.process_frame(self.frame, timestamp=0.0)
        self.assertEqual(obs["context"]["task"], "welding")
        self.assertEqual(obs["context"]["source"], "gemini")
        self.assertTrue(obs["gemini_called"])
        self.assertTrue(obs["person_detected"])
        self.assertEqual(obs["persons"][0]["track_id"], 1)
        self.mock_context_tool.analyze.assert_called_once()
        self.mock_fall.detect.assert_called_once()

    def test_no_person_skips_remaining_graph(self):
        self.mock_zone.detect_people.return_value = []
        obs = self.agent.process_frame(self.frame, timestamp=0.0)
        self.assertFalse(obs["person_detected"])
        self.assertEqual(obs["status"], "no_person")
        self.assertEqual(obs["context"]["source"], "skipped_no_person")
        self.mock_context_tool.analyze.assert_not_called()
        self.mock_ppe.detect.assert_not_called()
        self.mock_fall.detect.assert_not_called()
        self.mock_zone.evaluate_zone.assert_not_called()

    def test_compliance_agent_runs_after_fusion(self):
        compliance = MagicMock()
        compliance.evaluate.return_value = {"alert": False, "severity": "SAFE"}
        agent = ContextAgent(
            ppe_detector=self.mock_ppe, context_tool=self.mock_context_tool,
            zone_monitor=self.mock_zone, fall_detector=self.mock_fall,
            compliance_agent=compliance,
        )
        obs = agent.process_frame(self.frame, timestamp=0.0)
        compliance.evaluate.assert_called_once()
        self.assertEqual(obs["compliance"]["severity"], "SAFE")

    def test_context_and_detectors_run_in_parallel(self):
        barrier = threading.Barrier(4, timeout=2)

        context_result = self.mock_context_tool.analyze.return_value
        ppe_result = self.mock_ppe.detect.return_value
        fall_result = self.mock_fall.detect.return_value
        zone_result = self.mock_zone.evaluate_zone.return_value
        self.mock_context_tool.analyze.side_effect = lambda _frame: (barrier.wait(), context_result)[1]
        self.mock_ppe.detect.side_effect = lambda _frame: (barrier.wait(), ppe_result)[1]
        self.mock_fall.detect.side_effect = lambda _frame: (barrier.wait(), fall_result)[1]
        self.mock_zone.evaluate_zone.side_effect = lambda _persons: (barrier.wait(), zone_result)[1]

        obs = self.agent.process_frame(self.frame, timestamp=0.0)
        self.assertEqual(obs["status"], "ok")
        self.assertEqual(barrier.n_waiting, 0)

    def test_fall_detection_is_in_observation(self):
        self.mock_fall.detect.return_value = {
            "detected": True,
            "detections": [{"class": "Fall-Detected", "confidence": 0.92, "bbox": [1, 2, 3, 4]}],
            "confidence": 0.92,
        }
        obs = self.agent.process_frame(self.frame, timestamp=0.0)
        self.assertTrue(obs["fall"]["detected"])
        self.assertEqual(obs["confidence"]["fall"], 0.92)

    def test_cached_within_ttl(self):
        # Frame 1 at t=0s -> calls Gemini
        self.agent.process_frame(self.frame, timestamp=0.0)
        self.mock_context_tool.analyze.reset_mock()

        # Frame 2 at t=5s (< 10s TTL) -> uses cache
        obs2 = self.agent.process_frame(self.frame, timestamp=5.0)
        self.assertEqual(obs2["context"]["task"], "welding")
        self.assertEqual(obs2["context"]["source"], "cache")
        self.assertFalse(obs2["gemini_called"])
        self.mock_context_tool.analyze.assert_not_called()

    def test_cache_expires_after_ttl(self):
        # Frame 1 at t=0s
        self.agent.process_frame(self.frame, timestamp=0.0)
        self.mock_context_tool.analyze.reset_mock()

        # Frame 2 at t=15s (> 10s TTL) -> calls Gemini again
        obs2 = self.agent.process_frame(self.frame, timestamp=15.0)
        self.assertEqual(obs2["context"]["source"], "gemini")
        self.assertTrue(obs2["gemini_called"])
        self.mock_context_tool.analyze.assert_called_once()


if __name__ == "__main__":
    unittest.main()
