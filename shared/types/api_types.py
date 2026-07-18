from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal

class NodeStatus(BaseModel):
    node_id: str
    type: Literal["power", "audio", "motion", "env"]
    last_seen: int
    firmware_version: str
    status: Literal["ONLINE", "STALE", "OFFLINE"]

class EventPayload(BaseModel):
    event_id: str
    ts: int
    type: str  # e.g., "power_anomaly", "glass_break", "fall", etc.
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    node_id: str
    payload: Dict[str, Any]
    acknowledged: bool = False

class AnomalyScorePayload(BaseModel):
    ts: int
    model: str
    score: float
    context: Dict[str, Any]

class LLMQueryRequest(BaseModel):
    prompt: str = Field(..., description="Natural language prompt for the on-device assistant")

class LLMQueryResponse(BaseModel):
    response: str = Field(..., description="Generated natural language response")
    context_used: List[Dict[str, Any]] = Field(default_factory=list, description="Sensor readings and events referenced in the response generation")

class GenericResponseEnvelope(BaseModel):
    data: Any
    meta: Dict[str, Any] = Field(default_factory=dict)

class APIErrorDetail(BaseModel):
    code: str
    message: str
    detail: Optional[Dict[str, Any]] = None

class APIErrorResponse(BaseModel):
    error: APIErrorDetail
