"""Alert handlers: console, beep, file, webhook."""
import json
from pathlib import Path


def console_handler(event):
    """Print alert to console with formatting."""
    icon = {"CRITICAL": "🔴", "WARNING": "🟡"}.get(event.severity, "⚪")
    print(f"\n{icon} ALERT [{event.incident_id}] — {event.severity}")
    print(f"   Task: {event.task}")
    print(f"   Missing PPE: {', '.join(event.missing_ppe) or 'none'}")
    print(f"   Zone violation: {event.zone_violation}")
    print(f"   Fall detected: {event.fall_detected}")
    print(f"   Escalation: {event.escalation}")
    if event.explanation:
        print(f"   Reason: {event.explanation}")
    print()


def beep_handler(event):
    """Beep on CRITICAL only."""
    if event.severity == "CRITICAL":
        import os
        # macOS/Linux
        os.system("printf '\\a'")
        # Windows: import winsound; winsound.Beep(1000, 500)


def file_handler_factory(path: Path):
    """Return a handler that appends events to a file."""
    def handler(event):
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")
    return handler


def webhook_handler_factory(url: str):
    """Return a handler that POSTs to a webhook (Slack/Discord/Teams)."""
    def handler(event):
        import requests
        payload = {
            "text": (
                f"*{event.severity}* — {event.task}\n"
                f"Missing PPE: {', '.join(event.missing_ppe) or 'none'}\n"
                f"Fall detected: {event.fall_detected}\n"
                f"Escalation: {event.escalation}\n"
                f"{event.explanation or ''}"
            )
        }
        requests.post(url, json=payload, timeout=5)
    return handler
