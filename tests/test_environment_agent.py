"""Unit tests for the DIRAYA Environment Agent & Heat Stress Assessment."""
import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from agents.environment_agent import EnvironmentAgent
from tools.chat_tools import get_environment_assessment


class TestEnvironmentAgent(unittest.TestCase):
    def setUp(self):
        self.agent = EnvironmentAgent()

    def test_stull_wet_bulb_estimation(self):
        """Verify Stull equation produces physically sound wet-bulb values."""
        # Standard test: 30°C and 50% RH -> Twb should be around 22°C (approx 21-23°C)
        tw = self.agent.estimate_wet_bulb(temperature_c=30.0, humidity=50.0)
        self.assertTrue(21.0 <= tw <= 23.5, f"Expected Tw ~ 22°C, got {tw}")

        # High heat and high humidity: 40°C and 80% RH
        tw_high = self.agent.estimate_wet_bulb(temperature_c=40.0, humidity=80.0)
        self.assertTrue(35.0 <= tw_high <= 38.0, f"Expected high Tw, got {tw_high}")

    def test_wbgt_calculation(self):
        """Verify WBGT formulas for outdoor direct sun vs shaded."""
        res_sun = self.agent.calculate_estimated_wbgt(
            temperature_c=38.0,
            humidity=50.0,
            outdoor=True,
            direct_sun=True,
        )
        self.assertIn("estimated_wbgt_c", res_sun)
        self.assertIn("wet_bulb_c", res_sun)
        self.assertIn("globe_temperature_c", res_sun)
        # In direct sun, globe temp is +10°C higher
        self.assertEqual(res_sun["globe_temperature_c"], 48.0)

        res_shade = self.agent.calculate_estimated_wbgt(
            temperature_c=38.0,
            humidity=50.0,
            outdoor=True,
            direct_sun=False,
        )
        self.assertLess(res_shade["estimated_wbgt_c"], res_sun["estimated_wbgt_c"])

    def test_workload_thresholds_and_exposure(self):
        """Verify ACGIH / ISO 7243 workload threshold lookups and risk exposure."""
        heavy_acclimatized = self.agent.get_workload_threshold("heavy", acclimatized=True)
        self.assertEqual(heavy_acclimatized, 26.0)

        heavy_unacclimatized = self.agent.get_workload_threshold("heavy", acclimatized=False)
        self.assertEqual(heavy_unacclimatized, 23.0)

        # WBGT = 32°C with threshold 26°C -> delta = +6°C -> VERY_HIGH
        exp = self.agent.assess_heat_exposure(wbgt=32.0, workload="heavy", acclimatized=True)
        self.assertEqual(exp["heat_exposure"], "VERY_HIGH")

        # WBGT = 21°C with threshold 26°C -> delta = -5°C -> LOW
        exp_low = self.agent.assess_heat_exposure(wbgt=21.0, workload="heavy", acclimatized=True)
        self.assertEqual(exp_low["heat_exposure"], "LOW")

    def test_saudi_midday_sun_ban_active_violation(self):
        """Verify Saudi Ministerial Decision No. 3337 triggers on July 20 at 13:30 under direct sun."""
        eval_time = datetime(2026, 7, 20, 13, 30, tzinfo=ZoneInfo("Asia/Riyadh"))
        ban_eval = self.agent.check_saudi_midday_ban(
            current_dt=eval_time,
            outdoor=True,
            direct_sun=True,
        )
        self.assertTrue(ban_eval["saudi_midday_ban_active"])
        self.assertTrue(ban_eval["is_statutory_violation"])
        self.assertIn("MHRSD", ban_eval["legal_basis"])
        self.assertIn("إيقاف العمل", ban_eval["mandatory_action"])

    def test_saudi_midday_sun_ban_inactive_winter(self):
        """Verify Saudi ban is inactive in winter months (e.g. December)."""
        winter_time = datetime(2026, 12, 10, 13, 30, tzinfo=ZoneInfo("Asia/Riyadh"))
        ban_eval = self.agent.check_saudi_midday_ban(
            current_dt=winter_time,
            outdoor=True,
            direct_sun=True,
        )
        self.assertFalse(ban_eval["saudi_midday_ban_active"])
        self.assertFalse(ban_eval["is_statutory_violation"])

    def test_saudi_midday_sun_ban_inactive_morning(self):
        """Verify Saudi ban is inactive outside prohibited hours (e.g. 9:00 AM)."""
        morning_time = datetime(2026, 7, 20, 9, 0, tzinfo=ZoneInfo("Asia/Riyadh"))
        ban_eval = self.agent.check_saudi_midday_ban(
            current_dt=morning_time,
            outdoor=True,
            direct_sun=True,
        )
        self.assertFalse(ban_eval["saudi_midday_ban_active"])
        self.assertFalse(ban_eval["is_statutory_violation"])

    def test_full_environment_assessment(self):
        """Verify full assess_environment payload structure."""
        res = self.agent.assess_environment(
            temperature_c=42.0,
            humidity=60.0,
            wind_speed=1.5,
            outdoor=True,
            direct_sun=True,
            workload="heavy",
            acclimatized=True,
        )
        self.assertEqual(res["heat_exposure"], "VERY_HIGH")
        self.assertIn("environmental_warnings", res)
        self.assertGreater(len(res["environmental_warnings"]), 0)
        self.assertIn("recommendation", res)
        self.assertIn("work_rest_cycle", res)

    def test_chat_tool_integration(self):
        """Verify get_environment_assessment chat tool returns valid JSON."""
        tool_res = get_environment_assessment(workload="heavy")
        data = json.loads(tool_res)
        self.assertIn("location", data)
        self.assertIn("weather", data)
        self.assertIn("assessment", data)
        self.assertIn("estimated_wbgt_c", data["assessment"])
        self.assertIn("heat_exposure", data["assessment"])


    def test_api_analyze_endpoint(self):
        """Verify FastAPI /analyze endpoint returns the unified frontend format."""
        from starlette.testclient import TestClient
        from api_chat import app

        client = TestClient(app)
        response = client.post("/analyze", json={"latitude": 24.7136, "longitude": 46.6753})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("location", data)
        self.assertIn("weather", data)
        self.assertIn("environment_assessment", data)
        self.assertIn("assessment", data)
        self.assertIn("temperature_c", data["weather"])
        self.assertIn("estimated_wbgt_c", data["environment_assessment"])


if __name__ == "__main__":
    unittest.main()
