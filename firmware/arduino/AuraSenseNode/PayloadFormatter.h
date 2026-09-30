#ifndef AURASENSE_PAYLOAD_FORMATTER_H
#define AURASENSE_PAYLOAD_FORMATTER_H

#include <Arduino.h>

/**
 * PayloadFormatter ensures all serialized JSON strictly conforms
 * to AuraSense shared types defined in shared/types/sensor_payload.py
 * and consumed by hub/services/ingestion.py.
 */
class PayloadFormatter {
public:
    // Format Environmental Payload (BME680 / BME280)
    static String formatEnv(
        const char *nodeId, 
        uint32_t ts, 
        float tempC, 
        float humidityPct, 
        float pressureHpa, 
        float vocIaq
    );

    // Format Motion / mmWave Radar Payload
    static String formatMotion(
        const char *nodeId,
        uint32_t ts,
        bool presence,
        float breathingRate,
        bool fallDetected,
        bool rapidMovementDetected,
        float stationaryReflectionRatio
    );

    // Format Optical Pulse Meter Payload
    static String formatPulseMeter(
        const char *nodeId,
        uint32_t ts,
        uint32_t pulseCount,
        uint32_t impPerKwh,
        float activePowerW
    );

    // Format Acoustic Event Payload
    static String formatAudio(
        const char *nodeId,
        uint32_t ts,
        const char *label,
        float confidence
    );
};

#endif // AURASENSE_PAYLOAD_FORMATTER_H
