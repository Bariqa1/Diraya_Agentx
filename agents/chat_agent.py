"""Safety Chat Assistant Agent - uses OpenAI tool calling."""
import json
import logging
import os
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI

from tools.chat_tools import CHAT_TOOL_REGISTRY

load_dotenv()
LOG = logging.getLogger(__name__)


# ===========================================================
# Tool Definitions (OpenAI format)
# ===========================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_required_ppe",
            "description": (
                "Get the required PPE for a specific industrial task from the "
                "safety manual. Use when the user asks about PPE requirements "
                "for a task (e.g., welding, grinding, working at height)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": (
                            "Task name in English. Examples: 'welding', "
                            "'grinding', 'working_at_height'."
                        ),
                    }
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_incident_stats",
            "description": (
                "Get statistics about safety incidents. Use when the user asks "
                "how many violations occurred, counts by severity, zone, or falls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["CRITICAL", "WARNING", "SAFE"],
                        "description": "Optional filter by severity.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_incidents",
            "description": (
                "Get the most recent safety incidents. Use when the user asks "
                "to see recent violations or 'show me the last N incidents'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of incidents to return (1-50).",
                        "default": 5,
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["CRITICAL", "WARNING", "SAFE"],
                        "description": "Optional severity filter.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rule_metadata",
            "description": (
                "Get approval metadata for a rule (who approved it, when, "
                "from which source). Use when the user asks who approved a "
                "rule or when."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task name (e.g., 'welding').",
                    }
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_violation",
            "description": (
                "Explain why a specific incident is a violation by combining "
                "incident data with the applicable safety rule. "
                "Use when the user asks 'why is X a violation?' or "
                "'explain incident Y'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": (
                            "Incident ID (e.g., 'ALT-0001', 'INC-001')."
                        ),
                    }
                },
                "required": ["incident_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_environment_assessment",
            "description": (
                "Get real-time weather and heat stress (WBGT) assessment for the industrial facility. "
                "Calculates temperature, humidity, wind, Wet Bulb Globe Temperature (WBGT), "
                "heat exposure risk (LOW, MODERATE, HIGH, VERY_HIGH), hydration & work/rest cycles, "
                "and verifies compliance with the Saudi Midday Outdoor Sun Work Ban (MHRSD decision). "
                "Use when the user asks about weather, heat, temperature, outdoor working conditions, "
                "hydration, heat stress, or whether it is safe to work under the sun."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "workload": {
                        "type": "string",
                        "enum": ["light", "moderate", "heavy", "very_heavy"],
                        "description": "Physical workload level of workers (default: 'moderate').",
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Optional GPS latitude (defaults to Jubail Industrial City).",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Optional GPS longitude (defaults to Jubail Industrial City).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sign_hazard_zones",
            "description": (
                "Get dynamically calculated safety hazard zones and buffer perimeters extracted "
                "from on-site safety signboards (e.g. 'DANGER: HIGH VOLTAGE - KEEP 5M CLEAR', "
                "'FLAMMABLE CHEMICALS - 4M BUFFER'). "
                "Reads sign text, required buffer distance in meters, required PPE, and calculated ground perimeters. "
                "Use when the user asks about safety signs, signboards, required clearance distance around hazardous equipment, "
                "or sign-based restricted zones."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sign_id": {
                        "type": "string",
                        "description": "Optional sign ID (e.g. 'SIGN-01', 'SIGN-02').",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_zone_access",
            "description": (
                "Evaluate worker physical authorization and clearance into a hazardous facility zone. "
                "Calculates dynamic risk score (0-100%), severity (SAFE, LOW, MEDIUM, CRITICAL), "
                "access authorization verdict, missing PPE, and action required. "
                "Use when the user asks 'Can a laborer enter the substation?', 'Is a welder allowed in Zone X?', "
                "or asks to calculate the risk score for a worker entering a specific area."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "worker_role": {
                        "type": "string",
                        "description": "Worker role, title, or helmet color (e.g. 'White', 'Blue', 'electrician', 'engineer', 'laborer').",
                    },
                    "zone_id": {
                        "type": "string",
                        "description": "Target zone ID (e.g. 'ZONE_SUBSTATION', 'ZONE_NO_GO_CRANE', 'ZONE_CHEMICAL', 'ZONE_WELDING_BAY').",
                    },
                    "carried_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tools carried (e.g. ['insulated_toolkit', 'gas_cylinder']).",
                    },
                    "ppe_worn": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of PPE currently worn (e.g. ['Hard Hat', 'Insulated Gloves']).",
                    },
                },
                "required": ["worker_role", "zone_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_zone_access_matrix",
            "description": (
                "Get the physical RBAC clearance rules and safety criteria for facility zones. "
                "Shows authorized roles, forbidden roles, required PPE, and base hazard risk. "
                "Use when the user asks 'Who is allowed in the High Voltage room?', 'What are the rules for the Crane zone?', "
                "or asks to view the facility zone permissions matrix."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_id": {
                        "type": "string",
                        "description": "Optional zone ID (e.g. 'ZONE_SUBSTATION', 'ZONE_NO_GO_CRANE') to inspect a specific zone.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_heat_stress_guidelines",
            "description": (
                "Get official occupational safety guidelines and procedures for heat stress prevention, "
                "hydration protocols, work/rest cycles, heat illness symptoms, first aid, "
                "and compliance with the Saudi MHRSD Midday Sun Work Ban. "
                "Use when the user asks about heat stress prevention, procedures for working in high temperatures, "
                "how to prevent heat exhaustion/stroke, hydration schedules, or outdoor heat safety regulations. "
                "Example queries: 'ما إجراءات الوقاية من الإجهاد الحراري؟', 'كيف نحمي العمال من ضربات الشمس؟', 'ما هو بروتوكول شرب الماء في الحر؟'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional topic filter: 'prevention', 'hydration', 'symptoms_and_first_aid', 'saudi_regulations', or 'all'.",
                    }
                },
                "required": [],
            },
        },
    },
]


# ===========================================================
# System Prompt
# ===========================================================

SYSTEM_PROMPT = """You are the Safety Chat Assistant for the Diraya Industrial Safety Monitoring System.

Your job: answer the user's questions by calling the available tools.

=============================================================
STRICT RULES:
1. Use tools to fetch real data. Do NOT guess.
2. Do NOT invent numbers or information that is not in tool results.
3. Always cite the source of each fact (from result.source or result.source_file).
4. Answer concisely, clearly, and accurately in the user's language (Arabic by default).
5. For heat stress prevention, environmental safety, or high temperature procedures, ALWAYS call get_heat_stress_guidelines() or get_environment_assessment() to provide complete, actionable safety procedures.
6. If data is genuinely not available for an unsupported topic, respond: "I don't have that information right now."
7. If the question is ambiguous, ask for clarification.
8. Use real numbers from tools only.

Tool usage examples:
- "What PPE is required for welding?" -> get_required_ppe(task="welding")
- "ما إجراءات الوقاية من الإجهاد الحراري؟" -> get_heat_stress_guidelines(topic="prevention")
- "كيف نحمي العمال من الإجهاد الحراري وضربات الشمس؟" -> get_heat_stress_guidelines(topic="all")
- "How many violations today?" -> get_incident_stats()
- "Show me the last 5 CRITICAL violations" -> get_recent_incidents(n=5, severity="CRITICAL")
- "Who approved the welding rule?" -> get_rule_metadata(task="welding")
- "Why is ALT-0001 a violation?" -> explain_violation(incident_id="ALT-0001")
- "Is it safe to work outside in Jubail now?" -> get_environment_assessment(workload="moderate")
- "What are the restricted hazard zones around the high voltage sign?" -> get_sign_hazard_zones(sign_id="SIGN-01")
- "Can a laborer enter the high voltage substation?" -> evaluate_zone_access(worker_role="laborer", zone_id="ZONE_SUBSTATION")
- "Who is allowed in the crane lifting area?" -> get_zone_access_matrix(zone_id="ZONE_NO_GO_CRANE")
=============================================================
"""




# ===========================================================
# Agent
# ===========================================================

class SafetyChatAgent:
    """Chat assistant with tool calling for the safety system."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 5,
    ):
        self.openai_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

        self.max_iterations = max_iterations

        if self.openai_key:
            self.provider = "openai"
            self.api_key = self.openai_key
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
            self.client = OpenAI(api_key=self.api_key)
            LOG.info("SafetyChatAgent initialized with OpenAI (model: %s)", self.model)
        elif self.gemini_key:
            self.provider = "gemini"
            self.api_key = self.gemini_key
            self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            LOG.info("SafetyChatAgent initialized with Gemini fallback (model: %s)", self.model)
        else:
            self.provider = None
            self.api_key = None
            self.model = None
            self.client = None
            LOG.warning("Neither OPENAI_API_KEY nor GEMINI_API_KEY is configured in .env.")

    def _fallback_to_gemini(self) -> bool:
        """Switch provider to Gemini if OpenAI credits are exhausted or unavailable."""
        if not self.gemini_key or self.provider == "gemini":
            return False
        LOG.warning("OpenAI credits exhausted or unavailable. Automatically falling back to Gemini!")
        self.provider = "gemini"
        self.api_key = self.gemini_key
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return True

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool by name and return its JSON string result."""
        func = CHAT_TOOL_REGISTRY.get(name)
        if func is None:
            return json.dumps(
                {"error": f"Unknown tool: {name}"},
                ensure_ascii=False,
            )

        try:
            return func(**args)
        except Exception as exc:
            LOG.error("Tool '%s' failed: %s", name, exc)
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def ask(self, question: str) -> Dict:
        """
        Answer a user question using tool calling.

        Returns:
            {
                "answer": str,
                "tools_used": List[str],
                "tool_traces": List[Dict],
            }
        """
        if not self.client:
            return {
                "answer": (
                    "Neither OPENAI_API_KEY nor GEMINI_API_KEY is configured in .env. "
                    "Please set one of them to start using the assistant."
                ),
                "tools_used": [],
                "tool_traces": [],
            }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        tools_used: List[str] = []
        tool_traces: List[Dict] = []

        for iteration in range(self.max_iterations):
            response = None
            for attempt in range(3):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        temperature=0,
                    )
                    break
                except Exception as exc:
                    err_str = str(exc).lower()
                    if "insufficient_quota" in err_str or "credit_balance_exhausted" in err_str:
                        if self._fallback_to_gemini():
                            # Retrying immediately with Gemini
                            continue
                    if "429" in err_str or "rate" in err_str or "quota" in err_str:
                        sleep_s = 2.0 * (attempt + 1)
                        LOG.warning("Rate limit encountered (%s), retrying in %.1fs...", exc, sleep_s)
                        time.sleep(sleep_s)
                        if attempt == 2:
                            LOG.error("%s API call failed after retries: %s", self.provider or "LLM", exc)
                            return {
                                "answer": "The AI model is currently busy. Please try asking again in a few seconds.",
                                "tools_used": tools_used,
                                "tool_traces": tool_traces,
                            }
                    else:
                        LOG.error("%s API call failed: %s", self.provider or "LLM", exc)
                        return {
                            "answer": f"Error contacting model: {exc}",
                            "tools_used": tools_used,
                            "tool_traces": tool_traces,
                        }

            if not response:
                break

            msg = response.choices[0].message

            # No tool calls -> final answer
            if not msg.tool_calls:
                return {
                    "answer": msg.content or "I could not produce an answer.",
                    "tools_used": tools_used,
                    "tool_traces": tool_traces,
                }

            # Add assistant message with tool calls (appending msg preserves thought_signature for Gemini)
            messages.append(msg)

            # Execute each tool call
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                result = self._execute_tool(name, args)
                tools_used.append(name)
                tool_traces.append({
                    "tool": name,
                    "args": args,
                    "result": result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return {
            "answer": "I could not reach an answer within the allowed steps.",
            "tools_used": tools_used,
            "tool_traces": tool_traces,
        }
