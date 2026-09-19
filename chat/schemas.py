"""Pydantic schemas for the Safety Chat Assistant."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str
    tools_used: List[str] = []
    sources: List[str] = []


class ToolCall(BaseModel):
    name: str
    args: dict


class RequiredPPEResponse(BaseModel):
    task: str
    critical_ppe: List[str]
    recommended_ppe: List[str]
    source: str
    confidence: float
    citation: Optional[str] = None
