from dataclasses import dataclass
from typing import Dict, List

@dataclass
class NILMInput:
    # A sliding window of power readings (current, voltage, power, thd)
    # Expected shape: (sequence_length, 4)
    power_sequence: List[List[float]] 

@dataclass
class NILMOutput:
    # Key: appliance name (e.g., "refrigerator", "microwave"), Value: active power consumption in Watts
    appliance_power: Dict[str, float]

@dataclass
class AcousticModelInput:
    # Log-mel spectrogram representation of audio
    # Expected shape: (num_frames, num_bands) e.g., (96, 64)
    spectrogram: List[List[float]]

@dataclass
class AcousticModelOutput:
    label: str
    confidence: float

@dataclass
class BehavioralAnomalyInput:
    # History of activities / events over the past N hours
    # List of activity representations e.g., active time, active zones
    activity_vector: List[float]

@dataclass
class BehavioralAnomalyOutput:
    anomaly_score: float
    is_anomaly: bool
    contributing_factors: List[str]

@dataclass
class FallDetectionInput:
    # Time series of radar point clouds / summaries
    # Shape: (sequence_length, features)
    point_cloud_sequence: List[List[float]]

@dataclass
class FallDetectionOutput:
    fall_probability: float
    is_fall: bool
