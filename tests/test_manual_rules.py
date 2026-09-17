import unittest
from unittest.mock import patch
from tools.manual_rules import ManualRules, BASE_MINIMUM_CRITICAL


class TestManualRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = ManualRules()

    def test_loaded_tasks_count(self):
        self.assertGreaterEqual(len(self.rules.rules), 10)

    def test_welding_rules(self):
        rule = self.rules.get_required_ppe("welding")
        self.assertEqual(rule["source"], "structured_parser")
        self.assertIn("Face Shield", rule["critical_ppe"])
        self.assertIn("Gloves", rule["critical_ppe"])
        self.assertIn("Coverall", rule["critical_ppe"])
        self.assertIn("Safety Shoes", rule["recommended_ppe"])

    def test_working_at_height_rules(self):
        rule = self.rules.get_required_ppe("working_at_height")
        self.assertIn("Safety Harness", rule["critical_ppe"])
        self.assertIn("Helmet", rule["critical_ppe"])

    def test_case_and_whitespace_insensitivity(self):
        rule_1 = self.rules.get_required_ppe("  WELDING  ")
        rule_2 = self.rules.get_required_ppe("welding")
        self.assertEqual(rule_1["critical_ppe"], rule_2["critical_ppe"])

    def test_unknown_task_conservative_default(self):
        rule = self.rules.get_required_ppe("quantum_teleportation")
        self.assertEqual(rule["source"], "conservative_default")
        self.assertTrue(rule["requires_manual_review"])
        for base_item in BASE_MINIMUM_CRITICAL:
            self.assertIn(base_item, rule["critical_ppe"])

    def test_explicit_unknown_skips_resolution_log(self):
        with patch("tools.manual_rules.LOG.info") as log_info:
            rule = self.rules.get_required_ppe("unknown")
        self.assertEqual(rule["source"], "conservative_default")
        log_info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
