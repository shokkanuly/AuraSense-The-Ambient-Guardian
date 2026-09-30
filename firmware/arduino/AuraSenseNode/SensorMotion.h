#ifndef AURASENSE_SENSOR_MOTION_H
#define AURASENSE_SENSOR_MOTION_H

#include <Arduino.h>

struct MotionReading {
    bool presence;
    float breathingRate;
    bool fallDetected;
    bool rapidMovementDetected;
    float stationaryReflectionRatio;
};

class SensorMotion {
public:
    SensorMotion();
    bool begin(uint8_t presencePin, uint8_t alertPin);
    MotionReading update();
    void triggerSimulatedFall(); // Test method to trigger consensus fall event

private:
    uint8_t _presencePin;
    uint8_t _alertPin;
    bool _lastPresenceState;
    unsigned long _presenceStartTime;
    bool _manualFallTrigger;
};

#endif // AURASENSE_SENSOR_MOTION_H
