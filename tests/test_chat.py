"""Test the Safety Chat Assistant with the 5 example questions."""
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from agents import SafetyChatAgent
from tools.chat_tools import CHAT_TOOL_REGISTRY

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")


TEST_QUESTIONS = [
    "What PPE is required for welding?",
    "How many violations today?",
    "Show me the last 5 CRITICAL violations",
    "Who approved the welding rule?",
    "Explain why ALT-0001 is a violation",
]


def test_tools_offline():
    """Verify all 5 tools read live data files correctly without API calls."""
    print("\n" + "=" * 70)
    print("   OFFLINE DATA INTEGRATION TEST (ALL 5 TOOLS)")
    print("=" * 70)

    tests = [
        ("get_required_ppe", {"task": "welding"}),
        ("get_incident_stats", {"severity": "CRITICAL"}),
        ("get_recent_incidents", {"n": 3, "severity": "CRITICAL"}),
        ("get_rule_metadata", {"task": "welding"}),
        ("explain_violation", {"incident_id": "ALT-0001"}),
        ("get_environment_assessment", {"workload": "heavy"}),
    ]

    for name, args in tests:
        func = CHAT_TOOL_REGISTRY[name]
        res = func(**args)
        status = "OK" if "error" not in res else "ERROR"
        preview = res[:120] + "..." if len(res) > 120 else res
        print(f"[{status}] {name}({args})")
        print(f"      -> {preview}")

    print("=" * 70)


def main():
    agent = SafetyChatAgent()

    # Always test that the underlying tools and files work 100%
    test_tools_offline()

    if not agent.client:
        print("\n[NOTE] Neither OPENAI_API_KEY nor GEMINI_API_KEY is set in .env yet.")
        print("To run the full LLM agent test:")
        print("1. Add OPENAI_API_KEY or GEMINI_API_KEY in your .env file.")
        print("2. Re-run: .venv/bin/python test_chat.py\n")
        return

    print("\n" + "=" * 70)
    print(f"   SAFETY CHAT ASSISTANT - AGENT TEST SUITE (Provider: {agent.provider.upper()}, Model: {agent.model})")
    print("=" * 70)

    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}] Question: {q}")
        print("-" * 70)

        result = agent.ask(q)

        print(f"Answer:\n{result['answer']}\n")
        print(f"Tools used: {result['tools_used']}")

        for trace in result["tool_traces"]:
            preview = trace["result"][:200]
            print(f"   |-- {trace['tool']}({trace['args']})")
            print(f"   |   -> {preview}...")

    print("\n" + "=" * 70)
    print("   TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
