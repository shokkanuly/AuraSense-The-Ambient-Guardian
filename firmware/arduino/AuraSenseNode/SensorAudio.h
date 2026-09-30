#ifndef AURASENSE_SENSOR_AUDIO_H
#define AURASENSE_SENSOR_AUDIO_H

#include <Arduino.h>

struct AudioReading {
    const char *label;
    float confidence;
};

class SensorAudio {
public:
    SensorAudio();
    bool begin();
    AudioReading update();
    void triggerSimulatedEvent(const char *label, float confidence);

private:
    const char *_simulatedLabel;
    float _simulatedConfidence;
    bool _hasPendingSimulatedEvent;
};

#endif // AURASENSE_SENSOR_AUDIO_H
