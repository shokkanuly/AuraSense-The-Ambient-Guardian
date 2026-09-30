#include "SensorOpticalPulse.h"

volatile uint32_t SensorOpticalPulse::s_pulseCount = 0;
volatile uint64_t SensorOpticalPulse::s_lastPulseMicros = 0;
volatile float SensorOpticalPulse::s_activePowerW = 0.0f;
uint32_t SensorOpticalPulse::s_impPerKwh = 1000;
uint8_t SensorOpticalPulse::s_pin = 4;

void IRAM_ATTR SensorOpticalPulse::onPulseInterrupt() {
    uint64_t nowUs = esp_timer_get_time();
    uint64_t diffUs = nowUs - s_lastPulseMicros;

    // Debounce noise pulses < 10ms
    if (diffUs > 10000) {
        s_pulseCount++;
        if (s_lastPulseMicros > 0 && diffUs > 0) {
            // Power (W) = (3,600,000,000 / (imp_per_kwh * dt_in_us))
            s_activePowerW = (3600000000.0f / (float)(s_impPerKwh * diffUs));
        }
        s_lastPulseMicros = nowUs;
    }
}

SensorOpticalPulse::SensorOpticalPulse() {}

bool SensorOpticalPulse::begin(uint8_t pin, uint32_t impPerKwh) {
    s_pin = pin;
    s_impPerKwh = impPerKwh;

    pinMode(s_pin, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(s_pin), onPulseInterrupt, FALLING);

    Serial.printf("[SensorOpticalPulse] Initialized on GPIO %d (%lu imp/kWh)\n", s_pin, (unsigned long)s_impPerKwh);
    return true;
}

PulseMeterReading SensorOpticalPulse::getStatus() {
    PulseMeterReading reading;
    noInterrupts();
    reading.totalPulses = s_pulseCount;
    reading.impPerKwh = s_impPerKwh;
    
    // Decay active power to 0 if no pulses received for > 30 seconds
    uint64_t nowUs = esp_timer_get_time();
    if (s_lastPulseMicros > 0 && (nowUs - s_lastPulseMicros) > 30000000ULL) {
        s_activePowerW = 0.0f;
    }
    reading.activePowerW = s_activePowerW;
    interrupts();

    return reading;
}
