import unittest
from tools.alert_dispatcher import AlertDispatcher


class TestAlertDispatcher(unittest.TestCase):
    def test_debounces_continuous_alerts(self):
        dispatcher = AlertDispatcher(debounce_seconds=1.0)

        # 10 consecutive frames with missing helmet
        for t in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
            dispatcher.process(
                {
                    "alert": True,
                    "severity": "CRITICAL",
                    "missing_ppe": ["Helmet"],
                    "escalation": "safety_officer",
                    "task": "welding",
                },
                timestamp=t,
            )

        # Should only be 1 aggregated incident, not 6
        self.assertEqual(len(dispatcher.incidents), 1)
        inc = dispatcher.incidents[0]
        self.assertEqual(inc.incident_type, "Missing PPE (Helmet)")
        self.assertEqual(inc.start_time, 0.0)
        self.assertEqual(inc.end_time, 0.5)
        self.assertEqual(inc.peak_severity, "CRITICAL")

    def test_close_all_calculates_duration(self):
        dispatcher = AlertDispatcher(debounce_seconds=1.0)
        dispatcher.process(
            {
                "alert": True,
                "severity": "CRITICAL",
                "zone_violation": True,
                "escalation": "emergency",
                "task": "walking_in_yard",
            },
            timestamp=2.0,
        )
        dispatcher.close_all(final_timestamp=7.0)
        summary = dispatcher.get_summary()
        self.assertEqual(summary["total_incidents"], 1)
        self.assertEqual(summary["critical_incidents"], 1)
        self.assertEqual(summary["incidents"][0]["duration_s"], 5.0)


if __name__ == "__main__":
    unittest.main()
