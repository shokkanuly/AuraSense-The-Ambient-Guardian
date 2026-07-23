from pydantic import BaseModel, Field
from typing import List, Literal

class BaseSensorPayload(BaseModel):
    node_id: str = Field(..., description="Unique identifier for the sensor node")
    ts: int = Field(..., description="UTC Unix timestamp of the reading in seconds")
    type: Literal["power", "audio", "motion", "env"] = Field(..., description="Type of sensor data")

class PowerFeatures(BaseModel):
    rms_current: float = Field(..., description="Root Mean Square Current in Amperes")
    rms_voltage: float = Field(..., description="Root Mean Square Voltage in Volts")
    apparent_power: float = Field(..., description="Apparent Power in VA")
    thd: float = Field(..., description="Total Harmonic Distortion")

class PowerPayload(BaseSensorPayload):
    type: Literal["power"] = "power"
    features: PowerFeatures

class AudioFeatures(BaseModel):
    label: Literal["glass_break", "smoke_alarm", "running_water", "none"] = Field(..., description="Detected acoustic event classification")
    confidence: float = Field(..., description="Classification confidence score between 0.0 and 1.0")

class AudioPayload(BaseSensorPayload):
    type: Literal["audio"] = "audio"
    features: AudioFeatures

class MotionFeatures(BaseModel):
    presence: bool = Field(..., description="True if presence is detected via mmWave radar")
    breathing_rate: float = Field(..., description="Detected breathing rate in breaths per minute")
    fall_detected: bool = Field(..., description="True if a fall event is detected")
    point_cloud_summary: List[float] = Field(default_factory=list, description="Aggregated radar point cloud characteristics")

class MotionPayload(BaseSensorPayload):
    type: Literal["motion"] = "motion"
    features: MotionFeatures

class EnvFeatures(BaseModel):
    temp_c: float = Field(..., description="Temperature in degrees Celsius")
    humidity_pct: float = Field(..., description="Relative humidity percentage")
    pressure_hpa: float = Field(..., description="Atmospheric pressure in hPa")
    voc_iaq: float = Field(..., description="Volatile Organic Compounds Index for Air Quality")

class EnvPayload(BaseSensorPayload):
    type: Literal["env"] = "env"
    features: EnvFeatures


# Single source of truth mapping a sensor `type` (as it appears in the MQTT
# topic) to its payload model. Shared by the ingestion service and the
# device simulator / tests so the two never drift.
PAYLOAD_MODELS = {
    "power": PowerPayload,
    "audio": AudioPayload,
    "motion": MotionPayload,
    "env": EnvPayload,
}
