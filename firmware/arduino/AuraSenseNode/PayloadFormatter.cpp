#include "PayloadFormatter.h"
#include <stdio.h>

String PayloadFormatter::formatEnv(
    const char *nodeId, 
    uint32_t ts, 
    float tempC, 
    float humidityPct, 
    float pressureHpa, 
    float vocIaq
) {
    char buffer[256];
    snprintf(buffer, sizeof(buffer),
        "{\"node_id\":\"%s\",\"ts\":%lu,\"type\":\"env\","
        "\"features\":{\"temp_c\":%.2f,\"humidity_pct\":%.2f,\"pressure_hpa\":%.2f,\"voc_iaq\":%.2f}}",
        nodeId, (unsigned long)ts, tempC, humidityPct, pressureHpa, vocIaq
    );
    return String(buffer);
}

String PayloadFormatter::formatMotion(
    const char *nodeId,
    uint32_t ts,
    bool presence,
    float breathingRate,
    bool fallDetected,
    bool rapidMovementDetected,
    float stationaryReflectionRatio
) {
    char buffer[320];
    snprintf(buffer, sizeof(buffer),
        "{\"node_id\":\"%s\",\"ts\":%lu,\"type\":\"motion\","
        "\"features\":{\"presence\":%s,\"breathing_rate\":%.1f,\"fall_detected\":%s,"
        "\"stationary_reflection_ratio\":%.2f,\"rapid_movement_detected\":%s,\"point_cloud_summary\":[]}}",
        nodeId, (unsigned long)ts,
        presence ? "true" : "false",
        breathingRate,
        fallDetected ? "true" : "false",
        stationaryReflectionRatio,
        rapidMovementDetected ? "true" : "false"
    );
    return String(buffer);
}

String PayloadFormatter::formatPulseMeter(
    const char *nodeId,
    uint32_t ts,
    uint32_t pulseCount,
    uint32_t impPerKwh,
    float activePowerW
) {
    char buffer[256];
    snprintf(buffer, sizeof(buffer),
        "{\"node_id\":\"%s\",\"ts\":%lu,\"type\":\"pulse_meter\","
        "\"features\":{\"pulse_count\":%lu,\"imp_per_kwh\":%lu,\"active_power_w\":%.2f}}",
        nodeId, (unsigned long)ts,
        (unsigned long)pulseCount,
        (unsigned long)impPerKwh,
        activePowerW
    );
    return String(buffer);
}

String PayloadFormatter::formatAudio(
    const char *nodeId,
    uint32_t ts,
    const char *label,
    float confidence
) {
    char buffer[256];
    snprintf(buffer, sizeof(buffer),
        "{\"node_id\":\"%s\",\"ts\":%lu,\"type\":\"audio\","
        "\"features\":{\"label\":\"%s\",\"confidence\":%.2f}}",
        nodeId, (unsigned long)ts,
        label, confidence
    );
    return String(buffer);
}
