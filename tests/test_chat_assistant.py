"""Unit tests for the Safety Chat Assistant tools and schemas."""
import json
import unittest

from chat.schemas import ChatRequest, ChatResponse, RequiredPPEResponse
from chat.tools import (
    explain_violation,
    get_incident_stats,
    get_recent_incidents,
    get_required_ppe,
    get_rule_metadata,
)


class TestChatTools(unittest.TestCase):
    def test_schemas(self):
        req = ChatRequest(question="What PPE for welding?")
        self.assertEqual(req.question, "What PPE for welding?")

        resp = ChatResponse(answer="Face shield required", tools_used=["get_required_ppe"])
        self.assertEqual(resp.tools_used, ["get_required_ppe"])

    def test_get_required_ppe(self):
        res = json.loads(get_required_ppe("welding"))
        self.assertEqual(res["task"], "welding")
        self.assertIn("Face Shield", res["critical_ppe"])
        self.assertIn("Gloves", res["critical_ppe"])

    def test_get_incident_stats(self):
        res = json.loads(get_incident_stats())
        self.assertGreater(res["total"], 0)
        self.assertIn("CRITICAL", res["by_severity"])

    def test_get_recent_incidents(self):
        res = json.loads(get_recent_incidents(n=3))
        self.assertLessEqual(res["count"], 3)
        self.assertIsInstance(res["incidents"], list)

    def test_get_rule_metadata(self):
        res = json.loads(get_rule_metadata("welding"))
        self.assertEqual(res["task"], "welding")
        self.assertIn("approved_by", res)

    def test_explain_violation(self):
        res = json.loads(explain_violation("ALT-0001"))
        self.assertIn("incident", res)
        self.assertIn("applicable_rule", res)
        self.assertIn("reasoning", res)
