#ifndef AURASENSE_SENSOR_OPTICAL_PULSE_H
#define AURASENSE_SENSOR_OPTICAL_PULSE_H

#include <Arduino.h>

struct PulseMeterReading {
    uint32_t totalPulses;
    uint32_t impPerKwh;
    float activePowerW;
};

class SensorOpticalPulse {
public:
    SensorOpticalPulse();
    bool begin(uint8_t pin, uint32_t impPerKwh);
    PulseMeterReading getStatus();
    
    // Static ISR handler
    static void IRAM_ATTR onPulseInterrupt();

private:
    static volatile uint32_t s_pulseCount;
    static volatile uint64_t s_lastPulseMicros;
    static volatile float s_activePowerW;
    static uint32_t s_impPerKwh;
    static uint8_t s_pin;
};

#endif // AURASENSE_SENSOR_OPTICAL_PULSE_H
