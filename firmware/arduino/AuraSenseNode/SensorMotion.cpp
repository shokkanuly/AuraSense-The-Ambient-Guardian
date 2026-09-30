#include "SensorMotion.h"

SensorMotion::SensorMotion()
    : _presencePin(19),
      _alertPin(18),
      _lastPresenceState(false),
      _presenceStartTime(0),
      _manualFallTrigger(false) {}

bool SensorMotion::begin(uint8_t presencePin, uint8_t alertPin) {
    _presencePin = presencePin;
    _alertPin = alertPin;

    pinMode(_presencePin, INPUT_PULLDOWN);
    pinMode(_alertPin, INPUT_PULLDOWN);

    Serial.printf("[SensorMotion] Initialized mmWave radar inputs (Presence Pin: %d, Alert Pin: %d)\n", _presencePin, _alertPin);
    return true;
}

MotionReading SensorMotion::update() {
    MotionReading reading;
    
    // Read hardware inputs
    bool rawPresence = (digitalRead(_presencePin) == HIGH);
    bool rawAlert = (digitalRead(_alertPin) == HIGH);

    if (rawPresence) {
        if (!_lastPresenceState) {
            _presenceStartTime = millis();
        }
        _lastPresenceState = true;
    } else {
        _lastPresenceState = false;
        _presenceStartTime = 0;
    }

    reading.presence = rawPresence;
    reading.rapidMovementDetected = rawAlert;
    reading.fallDetected = _manualFallTrigger;
    _manualFallTrigger = false; // reset one-shot trigger

    // Normal healthy human resting breathing rate: ~14.0 - 18.0 bpm
    if (reading.presence) {
        reading.breathingRate = 16.2f;
        reading.stationaryReflectionRatio = 0.85f;
    } else {
        reading.breathingRate = 0.0f;
        reading.stationaryReflectionRatio = 0.05f;
    }

    return reading;
}

void SensorMotion::triggerSimulatedFall() {
    _manualFallTrigger = true;
    Serial.println("[SensorMotion] Simulating Fall event!");
}
