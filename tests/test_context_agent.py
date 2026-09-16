import unittest
import numpy as np
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
        self.mock_zone.detect.return_value = {"persons": [], "violation": False}

        self.agent = ContextAgent(
            ppe_detector=self.mock_ppe,
            context_tool=self.mock_context_tool,
            zone_monitor=self.mock_zone,
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
        self.mock_context_tool.analyze.assert_called_once()

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
