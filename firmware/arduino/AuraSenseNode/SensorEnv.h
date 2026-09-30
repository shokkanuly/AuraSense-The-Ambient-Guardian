#ifndef AURASENSE_SENSOR_ENV_H
#define AURASENSE_SENSOR_ENV_H

#include <Arduino.h>

struct EnvReading {
    float tempC;
    float humidityPct;
    float pressureHpa;
    float vocIaq;
    bool isValid;
};

class SensorEnv {
public:
    SensorEnv();
    bool begin(uint8_t sdaPin, uint8_t sclPin);
    EnvReading read();

private:
    bool _hardwareDetected;
    float _simTemp;
    float _simHumidity;
    float _simPressure;
    float _simVoc;
};

#endif // AURASENSE_SENSOR_ENV_H
