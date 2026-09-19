"""Safety Chat Assistant package (Forwarder).

Implementation lives in:
  - agents/chat_agent.py (SafetyChatAgent)
  - tools/chat_tools.py (CHAT_TOOL_REGISTRY & tools)
"""
from agents.chat_agent import SafetyChatAgent, TOOLS, SYSTEM_PROMPT

__all__ = ["SafetyChatAgent", "TOOLS", "SYSTEM_PROMPT"]
