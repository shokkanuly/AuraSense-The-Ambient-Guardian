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

class PairRequest(BaseModel):
    pairing_code: str = Field(..., description="Out-of-band pairing code shown by the hub during setup")
    client_name: Optional[str] = Field(None, description="Human-friendly identifier for the pairing client")

class PairResponse(BaseModel):
    access_token: str = Field(..., description="Signed JWT to send as an Authorization: Bearer token")
    token_type: Literal["bearer"] = "bearer"
    expires_at: int = Field(..., description="Token expiry as a UTC Unix timestamp (seconds)")
    client_id: str = Field(..., description="Identifier embedded in the token's subject claim")

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
