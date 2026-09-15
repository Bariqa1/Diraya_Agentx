# Derayah Context Agent

A hackathon MVP: custom PPE YOLO + Gemini visual context + a
separate person YOLO and polygon membership check, orchestrated by LangGraph.
No compliance, policy retrieval, risk scoring, or alerts are implemented yet.

## Project files

```text
Diraya/
config.py                     # Environment parsing and validation
main.py                       # Video pipeline and overlays
agents/
    __init__.py                # Exports ContextAgent
    context_agent.py           # State, graph, cache, fusion
tools/
    __init__.py
    ppe_detector.py            # PPE inference and annotation
    gemini_context.py          # Prompt, parser, retries
    zone_monitor.py            # Person inference and polygon checks
├── .env.example                  # Copy to .env and configure
├── .gitignore
├── requirements.txt
├── README.md
├── PPE_model.pt                  # Existing local checkpoint

User-supplied / generated:
├── .env
├── models/best.pt                # Or point to existing PPE_model.pt
├── video_test2.mp4
└── outputs/
    ├── context_agent_output.mp4
    └── context_agent_output.jsonl
```

The package initializers identify Python packages. Use `python main.py` to run the pipeline.

## Setup and run (PowerShell)

Use Python 3.11 or newer. Run these commands from the repository root:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

1. Put your trusted PPE checkpoint at `models/best.pt`, or set
   `PPE_MODEL_PATH=PPE_model.pt` to use the checkpoint already in this repository.
   The loader checks the exact 20 label names and uses checkpoint class IDs.
2. Put `video_test2.mp4` in the repository root, or change `INPUT_VIDEO`.
3. Set `GEMINI_API_KEY` to your Gemini API key. `.env` is ignored by Git.
4. Set `GEMINI_MODEL` to a vision model available to your Gemini API project
   that supports JSON structured output. There is deliberately no guessed model ID.
5. Set `RESTRICTED_ZONE` to a simple polygon in original video pixel coordinates.
   The sample polygon is a placeholder, not a calibrated factory zone.

```powershell
python main.py
```

`PERSON_MODEL=yolo11n.pt` is a separate pretrained COCO model. Ultralytics may
download these weights on first use; for offline use, set a local checkpoint path.
Relative configuration paths resolve from the repository root. Existing shell
environment variables take precedence over `.env`. Each run replaces the configured
output MP4 and JSONL. Input and output video paths must differ.

## Graph and public API

```text
START -> Check Cache
           |-- valid / failure cooldown -> Use Cache --|
           |-- missing / expired -------> Gemini -----|
                                                      v
                        PPE Detection -> Zone Monitoring -> Observation Fusion -> END
```

```python
from agents import ContextAgent

# Construct the three tools with your configuration (see main.py).
agent = ContextAgent(ppe_detector, context_tool, zone_monitor, cache_ttl=30)
observation = agent.process_frame(frame, timestamp=frame_index / fps)
```

Use one agent instance per sequential stream. The graph carries context and
cache timestamps; the wrapper retains only cache fields between invocations,
not raw frames. `agent.reset_cache()` supports future explicit scene/task
invalidation. A timestamp moving backward resets the cache automatically.

PPE and zone inference run on every processed frame. Gemini runs on the first
frame and at cache expiry (default 30 video seconds). This simple synchronous
pipeline pauses for Gemini on refresh frames; it does not promise uninterrupted
real-time throughput. Saved-video cache age uses `frame_index / fps`, independent
of inference speed. For a future live caller, supply elapsed `time.monotonic()`
seconds consistently instead; live capture is not part of this demo.

Gemini gets a JPEG of the current frame, a constrained observation prompt, and
a JSON schema. Local parsing also rejects malformed JSON, duplicate/extra fields,
incorrect types, non-finite confidence, and confidence outside [0,1].
Retries default to two additional attempts, with 1s then 2s backoff; each API
attempt has a 30s timeout. Non-transient HTTP errors are not retried within a call.

After an exhausted call, old context retains its original timestamp and uses
`cache_after_vlm_failure`; without old context, the result is `unknown`, empty
lists, confidence 0, and source `unavailable`. A configurable 5-video-second
failure cooldown prevents retrying on every frame. Cooldown observations retain
the failure source and degraded status. A failed response never refreshes the
successful cache timestamp.

## Observations and output

The output MP4 retains the input FPS, dimensions, and all decoded frames, with
PPE/person boxes, person bottom-center points, the zone polygon, and a top overlay
showing only task and zone violation. OpenCV output has no audio.
This MVP requires even video dimensions for MP4 encoding.

`outputs/context_agent_output.jsonl` contains one unified JSON object per frame:
`timestamp`, `ppe`, `context`, `zone`, `confidence`, `status`, `errors`,
`gemini_called`, and `context_timestamp`. The raw frame is never serialized.

- Individual detection confidence is preserved. PPE summary confidence is the
  mean of detected boxes, or `null` if none were detected.
- Zone confidence and overall confidence remain `null`.
- `zone.violation` is the requested compatibility field for **observed polygon
  occupancy**, not a determination of authorization or company policy compliance.
  A person's bottom-center on the polygon boundary counts as inside.
- Failed zone inference returns `violation: null`, not a false clear result.
  Detector failures and Gemini failures appear in `errors` with degraded status.
- No PPE detection does not imply missing PPE. Explicit `No ...` model classes
  remain observations. PPE is scene-level, with no per-worker association/tracking.
- Gemini confidence is model-reported, not calibrated. TTL caching can retain
  stale activity until refresh; no scene-change detection is implemented.

Terminal logs are throttled to once per video second for routine observations,
with full JSON every 10 video seconds, plus Gemini refresh/failure messages:

```text
Video: 30.00 FPS, 1280x720
[00:00] No VLM cache -> calling Gemini
[00:00] Gemini context: Grinding a metal workpiece
[00:00] PPE detection complete; context=gemini; zone=False; status=ok
[00:01] PPE detection complete; context=cache; zone=False; status=ok
[00:30] VLM cache expired -> calling Gemini
Saved ... frames to ...mp4 and ...jsonl
```

Task names and detection results above are illustrative. Runtime logs use video
timestamps, not time spent waiting for API responses.

Implementation references: [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api),
[Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output),
and [Ultralytics prediction results](https://docs.ultralytics.com/modes/predict).
