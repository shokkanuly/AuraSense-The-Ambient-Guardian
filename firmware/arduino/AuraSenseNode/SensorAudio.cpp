#include "SensorAudio.h"

SensorAudio::SensorAudio()
    : _simulatedLabel("none"),
      _simulatedConfidence(0.1f),
      _hasPendingSimulatedEvent(false) {}

bool SensorAudio::begin() {
    Serial.println("[SensorAudio] Initialized acoustic classification module.");
    return true;
}

AudioReading SensorAudio::update() {
    AudioReading reading;

    if (_hasPendingSimulatedEvent) {
        reading.label = _simulatedLabel;
        reading.confidence = _simulatedConfidence;
        _hasPendingSimulatedEvent = false;
        Serial.printf("[SensorAudio] Emitting acoustic classification: %s (conf: %.2f)\n", reading.label, reading.confidence);
    } else {
        reading.label = "none";
        reading.confidence = 0.05f;
    }

    return reading;
}

void SensorAudio::triggerSimulatedEvent(const char *label, float confidence) {
    _simulatedLabel = label;
    _simulatedConfidence = confidence;
    _hasPendingSimulatedEvent = true;
}
