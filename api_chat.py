"""FastAPI server for the Safety Chat Assistant."""
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents import SafetyChatAgent
from chat.schemas import ChatRequest, ChatResponse

load_dotenv()
logging.basicConfig(level=logging.INFO)

agent: SafetyChatAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = SafetyChatAgent()
    if agent.client:
        logging.info("Safety Chat Agent initialized (provider: %s, model: %s)", agent.provider, agent.model)
    else:
        logging.warning("Neither OPENAI_API_KEY nor GEMINI_API_KEY is configured in .env.")
    yield
    logging.info("Shutting down Safety Chat Agent...")


app = FastAPI(
    title="Safety Chat Assistant API",
    description="Interactive conversational safety assistant for Diraya Hackathon",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent_ready": agent is not None and bool(agent.client),
        "provider": getattr(agent, "provider", None),
        "model": getattr(agent, "model", None),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not agent.client:
        raise HTTPException(
            status_code=400,
            detail="Neither OPENAI_API_KEY nor GEMINI_API_KEY is configured on server. Please add one to .env",
        )

    try:
        result = agent.ask(request.question)
        return ChatResponse(
            answer=result["answer"],
            tools_used=result["tools_used"],
            sources=list({t["tool"] for t in result["tool_traces"]}),
        )
    except Exception as exc:
        logging.error("Chat failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/environment/assess")
@app.get("/analyze")
async def get_environment_assessment(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    workload: str = "moderate",
    outdoor: bool = True,
):
    """
    Get live environmental weather & WBGT heat stress assessment for a facility or worker location.
    Includes Saudi Ministry of Human Resources (MHRSD) Midday Work Ban verification.
    """
    try:
        from agents.environment_agent import EnvironmentAgent
        agent_env = EnvironmentAgent()
        raw = agent_env.assess_current_facility(
            latitude=lat,
            longitude=lon,
            workload=workload,
            outdoor=outdoor,
        )
        return {
            "location": raw["location"],
            "weather": raw["weather"],
            "environment_assessment": raw["assessment"],
            "assessment": raw["assessment"],
            "data": {
                "location": raw["location"],
                "weather": raw["weather"],
                "environment_assessment": raw["assessment"],
                "assessment": raw["assessment"],
            },
        }
    except Exception as exc:
        logging.error("Environment assessment failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze")
@app.post("/environment/analyze")
@app.post("/environment/assess")
async def post_environment_assessment(body: dict):
    """
    POST variant for GPS coordinates and workplace parameters.
    Compatible with frontend /analyze endpoint.
    Body keys: latitude, longitude, workload, outdoor, direct_sun
    """
    try:
        from agents.environment_agent import EnvironmentAgent
        agent_env = EnvironmentAgent()
        lat = body.get("latitude")
        lon = body.get("longitude")
        workload = body.get("workload", "moderate")
        outdoor = body.get("outdoor", True)

        raw = agent_env.assess_current_facility(
            latitude=lat,
            longitude=lon,
            workload=workload,
            outdoor=outdoor,
        )
        return {
            "location": raw["location"],
            "weather": raw["weather"],
            "environment_assessment": raw["assessment"],
            "assessment": raw["assessment"],
            "data": {
                "location": raw["location"],
                "weather": raw["weather"],
                "environment_assessment": raw["assessment"],
                "assessment": raw["assessment"],
            },
        }
    except Exception as exc:
        logging.error("Environment assessment failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/signs/hazards")
async def get_sign_hazards(sign_id: Optional[str] = None):
    """
    Get dynamic safety hazard perimeters defined by visual safety signboards.
    Uses one-shot VLM scan with persistent caching for 0-token recurring cost.
    """
    try:
        from tools.sign_hazard_monitor import SignHazardMonitor
        monitor = SignHazardMonitor()
        summary = monitor.get_summary()
        if sign_id:
            target = sign_id.strip().upper()
            for s in summary.get("signs", []):
                if s.get("sign_id", "").upper() == target:
                    return s
            raise HTTPException(status_code=404, detail=f"Sign '{sign_id}' not found")
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Sign hazard query failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/signs/evaluate")
async def evaluate_sign_breaches(body: dict):
    """
    Check if a list of tracked persons (with bounding boxes) breach any signboard hazard perimeter.
    Body: {"persons": [{"track_id": 1, "bbox": [180, 150, 240, 260]}]}
    """
    try:
        from tools.sign_hazard_monitor import SignHazardMonitor
        monitor = SignHazardMonitor()
        persons = body.get("persons", [])
        violations = monitor.evaluate_persons(persons)
        return {
            "total_violations": len(violations),
            "violations": violations,
            "has_breach": len(violations) > 0,
        }
    except Exception as exc:
        logging.error("Sign breach evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/zones/access-matrix")
async def get_zone_access_matrix(zone_id: Optional[str] = None):
    """
    Get physical RBAC rules for facility zones and standard helmet roles.
    """
    try:
        from tools.zone_access_matrix import ZoneAccessEngine
        engine = ZoneAccessEngine()
        summary = engine.get_matrix_summary()
        if zone_id:
            target = zone_id.strip().upper()
            for z in summary.get("zones", []):
                if z.get("zone_id", "").upper() == target:
                    return z
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Zone matrix query failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/zones/evaluate-access")
async def evaluate_worker_zone_access(body: dict):
    """
    Evaluate worker authorization and dynamic risk score (0-100%) for a target zone.
    Body keys:
      - worker_role: (e.g. 'Blue', 'electrician', 'engineer', 'laborer')
      - zone_id: (e.g. 'ZONE_SUBSTATION', 'ZONE_NO_GO_CRANE')
      - carried_tools: optional list (e.g. ['insulated_toolkit'])
      - ppe_worn: optional list (e.g. ['Hard Hat', 'Insulated Gloves'])
      - worker_id: optional str/int
    """
    try:
        from tools.zone_access_matrix import ZoneAccessEngine
        engine = ZoneAccessEngine()
        role = body.get("worker_role") or body.get("role") or body.get("helmet_color")
        zone_id = body.get("zone_id")
        if not role or not zone_id:
            raise HTTPException(status_code=400, detail="'worker_role' and 'zone_id' are required")

        carried_tools = body.get("carried_tools", [])
        ppe_worn = body.get("ppe_worn", [])
        worker_id = body.get("worker_id")

        return engine.evaluate_access(
            worker_role=role,
            zone_id=zone_id,
            carried_tools=carried_tools,
            ppe_worn=ppe_worn,
            worker_id=worker_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Zone access evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/alerts")
async def get_alerts(limit: int = 30):
    """
    Get live safety alerts detected by the computer vision and inference pipelines.
    Reads from outputs/alerts.jsonl.
    """
    alerts_file = os.path.join(os.path.dirname(__file__), "outputs", "alerts.jsonl")
    records = []
    if os.path.exists(alerts_file):
        try:
            with open(alerts_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
        except Exception as exc:
            logging.error("Failed to read alerts.jsonl: %s", exc)
    return {"total": len(records), "alerts": records}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("api_chat:app", host="0.0.0.0", port=port, reload=True)


