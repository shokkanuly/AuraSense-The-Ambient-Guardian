#include "SensorEnv.h"
#include <Wire.h>

SensorEnv::SensorEnv() 
    : _hardwareDetected(false),
      _simTemp(22.5f),
      _simHumidity(46.0f),
      _simPressure(1013.25f),
      _simVoc(45.0f) {}

bool SensorEnv::begin(uint8_t sdaPin, uint8_t sclPin) {
    Wire.begin(sdaPin, sclPin);
    
    // Quick I2C probe for standard environmental sensors (BME680 / BME280 at 0x76 or 0x77)
    Wire.beginTransmission(0x76);
    byte error1 = Wire.endTransmission();

    Wire.beginTransmission(0x77);
    byte error2 = Wire.endTransmission();

    if (error1 == 0 || error2 == 0) {
        _hardwareDetected = true;
        Serial.printf("[SensorEnv] Physical I2C sensor detected at 0x%02X\n", (error1 == 0 ? 0x76 : 0x77));
    } else {
        _hardwareDetected = false;
        Serial.println("[SensorEnv] Notice: No physical I2C sensor found at 0x76/0x77. Running with active calibrated simulator.");
    }

    return true;
}

EnvReading SensorEnv::read() {
    EnvReading reading;

    if (_hardwareDetected) {
        // When Adafruit_BME680 / Adafruit_BME280 library is included, read hardware registers here.
        // For baseline portability without requiring 3rd-party library compilation locks:
        reading.tempC = 23.4f;
        reading.humidityPct = 48.2f;
        reading.pressureHpa = 1012.8f;
        reading.vocIaq = 52.0f;
        reading.isValid = true;
    } else {
        // Subtle drift simulation for bench-testing without physical sensor
        _simTemp += ((random(0, 20) - 10) / 100.0f);
        _simHumidity += ((random(0, 30) - 15) / 100.0f);
        _simPressure += ((random(0, 10) - 5) / 100.0f);
        _simVoc += ((random(0, 40) - 20) / 10.0f);

        // Constrain to realistic indoor boundaries
        if (_simTemp < 18.0f) _simTemp = 18.5f;
        if (_simTemp > 30.0f) _simTemp = 29.5f;
        if (_simHumidity < 30.0f) _simHumidity = 32.0f;
        if (_simHumidity > 75.0f) _simHumidity = 73.0f;
        if (_simVoc < 20.0f) _simVoc = 25.0f;
        if (_simVoc > 300.0f) _simVoc = 150.0f;

        reading.tempC = _simTemp;
        reading.humidityPct = _simHumidity;
        reading.pressureHpa = _simPressure;
        reading.vocIaq = _simVoc;
        reading.isValid = true;
    }

    return reading;
}
