import unittest
from agents.compliance_agent import ComplianceAgent
from tools.manual_rules import ManualRules


class TestComplianceAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = ManualRules()
        cls.agent = ComplianceAgent(rules=cls.rules)

    def test_full_compliance_safe(self):
        obs = {
            "context": {"task": "walking_in_yard", "confidence": 0.9, "source": "gemini"},
            "zone": {"violation": False},
            "ppe": {"detections": [{"class": "Helmet", "confidence": 0.85}]},
        }
        res = self.agent.evaluate(obs)
        self.assertFalse(res["alert"])
        self.assertEqual(res["severity"], "SAFE")
        self.assertEqual(res["escalation"], "none")
        self.assertEqual(res["missing_critical_ppe"], [])

    def test_missing_critical_ppe_critical(self):
        obs = {
            "context": {"task": "welding", "confidence": 0.9, "source": "gemini"},
            "zone": {"violation": False},
            "ppe": {
                "detections": [
                    {"class": "Helmet", "confidence": 0.9},
                    {"class": "No Face Shield", "confidence": 0.85},
                    {"class": "Gloves", "confidence": 0.9},
                    {"class": "Coverall", "confidence": 0.9},
                ]
            },
        }
        res = self.agent.evaluate(obs)
        self.assertTrue(res["alert"])
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertIn("Face Shield", res["missing_critical_ppe"])
        self.assertEqual(res["escalation"], "safety_officer")

    def test_missing_recommended_ppe_warning(self):
        obs = {
            "context": {"task": "welding", "confidence": 0.9, "source": "gemini"},
            "zone": {"violation": False},
            "ppe": {
                "detections": [
                    {"class": "Face Shield", "confidence": 0.9},
                    {"class": "Gloves", "confidence": 0.9},
                    {"class": "Coverall", "confidence": 0.9},
                    {"class": "No Ear Protectors", "confidence": 0.8},  # Recommended
                ]
            },
        }
        res = self.agent.evaluate(obs)
        self.assertTrue(res["alert"])
        self.assertEqual(res["severity"], "WARNING")
        self.assertIn("Ear Protectors", res["missing_recommended_ppe"])
        self.assertEqual(res["escalation"], "supervisor")

    def test_zone_violation_emergency(self):
        obs = {
            "context": {"task": "walking_in_yard", "confidence": 0.9, "source": "gemini"},
            "zone": {"violation": True},
            "ppe": {"detections": [{"class": "Helmet", "confidence": 0.9}]},
        }
        res = self.agent.evaluate(obs)
        self.assertTrue(res["alert"])
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertTrue(res["zone_violation"])
        self.assertEqual(res["escalation"], "emergency")

    def test_fall_detection_is_critical_emergency(self):
        obs = {
            "context": {"task": "walking_in_yard", "confidence": 0.9, "source": "gemini"},
            "zone": {"violation": False},
            "fall": {"detected": True, "confidence": 0.92},
            "ppe": {"detections": [{"class": "Helmet", "confidence": 0.9}]},
        }
        res = self.agent.evaluate(obs)
        self.assertTrue(res["alert"])
        self.assertTrue(res["fall_detected"])
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertEqual(res["escalation"], "emergency")
        self.assertIn("fall_detected", [reason["code"] for reason in res["reasons"]])

    def test_unknown_task_escalation(self):
        obs = {
            "context": {"task": "unknown_chore", "confidence": 0.9, "source": "gemini"},
            "zone": {"violation": False},
            "ppe": {"detections": []},
        }
        res = self.agent.evaluate(obs)
        self.assertTrue(res["unknown_task"])
        self.assertTrue(res["alert"])
        self.assertIn(res["severity"], ("WARNING", "CRITICAL"))

    def test_low_confidence_escalation(self):
        obs = {
            "context": {"task": "walking_in_yard", "confidence": 0.2, "source": "gemini"},
            "zone": {"violation": False},
            "ppe": {"detections": [{"class": "Helmet", "confidence": 0.9}]},
        }
        res = self.agent.evaluate(obs)
        self.assertTrue(res["low_confidence"])
        self.assertEqual(res["severity"], "WARNING")

    def test_explain_without_llm_client_does_not_mutate(self):
        agent_no_llm = ComplianceAgent(rules=self.rules, llm_client=None)
        obs = {
            "context": {"task": "welding", "confidence": 0.9},
            "zone": {"violation": False},
            "ppe": {"detections": [{"class": "No Face Shield", "confidence": 0.9}]},
        }
        dec = agent_no_llm.evaluate(obs)
        explained = agent_no_llm.explain(dec)
        self.assertEqual(explained["severity"], dec["severity"])
        self.assertEqual(explained["alert"], dec["alert"])
        self.assertEqual(explained["escalation"], dec["escalation"])
        self.assertIsNone(explained["explanation"])


if __name__ == "__main__":
    unittest.main()
