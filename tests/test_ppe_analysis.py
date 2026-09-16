import unittest
from tools.ppe_analysis import analyze_ppe, KNOWN_PPE


class TestPPEAnalysis(unittest.TestCase):
    def test_positive_detections(self):
        obs = {
            "detections": [
                {"class": "Helmet", "confidence": 0.85},
                {"class": "Safety Vest", "confidence": 0.90},
            ]
        }
        res = analyze_ppe(obs, conf_threshold=0.25)
        self.assertIn("Helmet", res["detected"])
        self.assertIn("Safety Vest", res["detected"])
        self.assertNotIn("Helmet", res["missing"])
        self.assertNotIn("Helmet", res["uncertain"])

    def test_negative_detections(self):
        obs = {
            "detections": [
                {"class": "No Helmet", "confidence": 0.80},
                {"class": "No Gloves", "confidence": 0.70},
            ]
        }
        res = analyze_ppe(obs, conf_threshold=0.25)
        self.assertIn("Helmet", res["missing"])
        self.assertIn("Gloves", res["missing"])
        self.assertNotIn("Helmet", res["detected"])

    def test_conflict_resolution_by_confidence(self):
        # Case A: Positive has higher confidence
        obs_a = {
            "detections": [
                {"class": "Helmet", "confidence": 0.88},
                {"class": "No Helmet", "confidence": 0.40},
            ]
        }
        res_a = analyze_ppe(obs_a, conf_threshold=0.25)
        self.assertIn("Helmet", res_a["detected"])
        self.assertNotIn("Helmet", res_a["missing"])

        # Case B: Negative has higher confidence
        obs_b = {
            "detections": [
                {"class": "Helmet", "confidence": 0.35},
                {"class": "No Helmet", "confidence": 0.82},
            ]
        }
        res_b = analyze_ppe(obs_b, conf_threshold=0.25)
        self.assertIn("Helmet", res_b["missing"])
        self.assertNotIn("Helmet", res_b["detected"])

    def test_low_confidence_to_uncertain(self):
        obs = {
            "detections": [
                {"class": "Helmet", "confidence": 0.15},  # Below 0.25
            ]
        }
        res = analyze_ppe(obs, conf_threshold=0.25)
        self.assertNotIn("Helmet", res["detected"])
        self.assertNotIn("Helmet", res["missing"])
        self.assertIn("Helmet", res["uncertain"])

    def test_unobserved_items_are_uncertain(self):
        obs = {"detections": [{"class": "Helmet", "confidence": 0.9}]}
        res = analyze_ppe(obs, conf_threshold=0.25)
        # Standard items like Face Shield and Gloves were not observed
        self.assertIn("Face Shield", res["uncertain"])
        self.assertIn("Gloves", res["uncertain"])

    def test_empty_or_malformed_input(self):
        self.assertEqual(len(analyze_ppe({})["detected"]), 0)
        self.assertEqual(len(analyze_ppe(None)["detected"]), 0)
        self.assertEqual(len(analyze_ppe({"detections": None})["detected"]), 0)


if __name__ == "__main__":
    unittest.main()
