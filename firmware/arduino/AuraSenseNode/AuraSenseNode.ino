/**
 * AuraSense — Arduino Node Foundation
 * 
 * Hardware Foundation Sketch for AuraSense ambient guardian network.
 * Compatible with ESP32 / ESP32-S3 boards using the standard Arduino IDE
 * or PlatformIO.
 * 
 * Emits compact JSON feature vectors conforming to shared/types/sensor_payload.py
 * over MQTT (QoS 1) with UTC timestamps synchronized via SNTP.
 */

#include "config.h"
#include "NetworkManager.h"
#include "PayloadFormatter.h"
#include "SensorEnv.h"
#include "SensorMotion.h"
#include "SensorOpticalPulse.h"
#include "SensorAudio.h"

// Subsystem instances
NetworkManager networkManager;
SensorEnv sensorEnv;
SensorMotion sensorMotion;
SensorOpticalPulse sensorPulse;
SensorAudio sensorAudio;

// Timing counters (non-blocking)
unsigned long lastEnvPublish = 0;
unsigned long lastMotionPublish = 0;
unsigned long lastPulsePublish = 0;
unsigned long lastAudioPublish = 0;

// Handle incoming commands from AuraSense Hub (e.g. OTA, diagnostic pings)
void onCommandReceived(const char *topic, const uint8_t *payload, unsigned int length) {
    String msg = "";
    for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    Serial.printf("[CMD RX] Topic: %s | Message: %s\n", topic, msg.c_str());

    // Check if OTA command
    if (strstr(topic, "/ota/cmd") != nullptr) {
        Serial.println("[OTA] Hub requested OTA update sequence. Initiating verification...");
        // In full production, trigger ESP32 httpUpdate via URL in payload
    } 
    // Check if diagnostic test trigger
    else if (msg.indexOf("simulate_fall") >= 0) {
        sensorMotion.triggerSimulatedFall();
    } else if (msg.indexOf("simulate_glass_break") >= 0) {
        sensorAudio.triggerSimulatedEvent("glass_break", 0.92f);
    }
}

// Process serial console inputs for fast workbench testing
void checkSerialCommands() {
    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'f' || c == 'F') {
            Serial.println("\n>>> Bench Command: Simulating Fall Event <<<");
            sensorMotion.triggerSimulatedFall();
        } else if (c == 'g' || c == 'G') {
            Serial.println("\n>>> Bench Command: Simulating Glass Break Event <<<");
            sensorAudio.triggerSimulatedEvent("glass_break", 0.94f);
        } else if (c == 'v' || c == 'V') {
            Serial.println("\n>>> Bench Command: Simulating VOC Gas Spike <<<");
            // Will produce VOC IAQ > 250 to test Consensus Matrix Rule 2
        } else if (c == 's' || c == 'S') {
            Serial.println("\n--- AuraSense Node Status ---");
            Serial.printf("Node ID: %s | Firmware: %s\n", NODE_ID, FIRMWARE_VERSION);
            Serial.printf("Network: %s | UTC Epoch: %lu\n", 
                          networkManager.isConnected() ? "Connected" : "Disconnected", 
                          (unsigned long)networkManager.getEpochSeconds());
            Serial.println("-----------------------------");
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n==============================================");
    Serial.println("       AuraSense Node Firmware starting       ");
    Serial.printf("       Node ID: %s\n", NODE_ID);
    Serial.printf("       Firmware: %s\n", FIRMWARE_VERSION);
    Serial.println("==============================================");

    // 1. Initialize Sensors
    #if ENABLE_ENV_SENSOR
    sensorEnv.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    #endif

    #if ENABLE_MOTION_SENSOR
    sensorMotion.begin(PIN_RADAR_PRESENCE, PIN_RADAR_FALL_OR_RAPID);
    #endif

    #if ENABLE_OPTICAL_PULSE_SENSOR
    sensorPulse.begin(PIN_OPTICAL_PULSE, OPTICAL_METER_IMP_PER_KWH);
    #endif

    #if ENABLE_AUDIO_FEATURES
    sensorAudio.begin();
    #endif

    // 2. Initialize Network & MQTT Lifecycle
    networkManager.begin(onCommandReceived);

    Serial.println("[Ready] Node setup complete. Type 'f' for fall, 'g' for glass break, 's' for status.");
}

void loop() {
    // Keep WiFi, NTP, and MQTT active
    networkManager.update();
    checkSerialCommands();

    unsigned long currentMillis = millis();
    uint32_t currentTs = networkManager.getEpochSeconds();

    // --------------------------------------------------------------------------
    // 1. Environmental Sensor Publishing
    // --------------------------------------------------------------------------
    #if ENABLE_ENV_SENSOR
    if (currentMillis - lastEnvPublish >= INTERVAL_ENV_MS) {
        lastEnvPublish = currentMillis;
        EnvReading env = sensorEnv.read();
        if (env.isValid) {
            String payload = PayloadFormatter::formatEnv(
                NODE_ID, currentTs, env.tempC, env.humidityPct, env.pressureHpa, env.vocIaq
            );
            networkManager.publishReading("env", payload);
        }
    }
    #endif

    // --------------------------------------------------------------------------
    // 2. Motion / mmWave Radar Publishing
    // --------------------------------------------------------------------------
    #if ENABLE_MOTION_SENSOR
    if (currentMillis - lastMotionPublish >= INTERVAL_MOTION_MS) {
        lastMotionPublish = currentMillis;
        MotionReading motion = sensorMotion.update();
        
        // Always publish if presence detected or fall detected, or periodic heartbeat
        String payload = PayloadFormatter::formatMotion(
            NODE_ID, currentTs, motion.presence, motion.breathingRate, 
            motion.fallDetected, motion.rapidMovementDetected, 
            motion.stationaryReflectionRatio
        );
        networkManager.publishReading("motion", payload);
    }
    #endif

    // --------------------------------------------------------------------------
    // 3. Optical Pulse Utility Power Publishing
    // --------------------------------------------------------------------------
    #if ENABLE_OPTICAL_PULSE_SENSOR
    if (currentMillis - lastPulsePublish >= INTERVAL_PULSE_REPORT_MS) {
        lastPulsePublish = currentMillis;
        PulseMeterReading pulse = sensorPulse.getStatus();
        String payload = PayloadFormatter::formatPulseMeter(
            NODE_ID, currentTs, pulse.totalPulses, pulse.impPerKwh, pulse.activePowerW
        );
        networkManager.publishReading("pulse_meter", payload);
    }
    #endif

    // --------------------------------------------------------------------------
    // 4. Acoustic Event Publishing
    // --------------------------------------------------------------------------
    #if ENABLE_AUDIO_FEATURES
    if (currentMillis - lastAudioPublish >= INTERVAL_AUDIO_MS) {
        lastAudioPublish = currentMillis;
        AudioReading audio = sensorAudio.update();
        
        // Publish when confidence > 0.4 or periodic normal heartbeat
        if (audio.confidence > 0.4f || (currentMillis % 30000 < INTERVAL_AUDIO_MS)) {
            String payload = PayloadFormatter::formatAudio(
                NODE_ID, currentTs, audio.label, audio.confidence
            );
            networkManager.publishReading("audio", payload);
        }
    }
    #endif

    delay(20); // Yield to FreeRTOS watchdog & background network tasks
}
