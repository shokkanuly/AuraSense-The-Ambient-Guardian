#ifndef AURASENSE_NETWORK_MANAGER_H
#define AURASENSE_NETWORK_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"

typedef void (*CommandHandlerCallback)(const char *topic, const uint8_t *payload, unsigned int length);

class NetworkManager {
public:
    NetworkManager();
    void begin(CommandHandlerCallback cmdCallback = nullptr);
    void update();
    bool isConnected();
    
    // Publish a sensor reading payload to "aurasense/nodes/<node_id>/<sensor_type>"
    bool publishReading(const char *sensorType, const String &payloadJson);
    
    // Returns current UTC epoch seconds (synced via NTP)
    uint32_t getEpochSeconds();

private:
    WiFiClient _wifiClient;
    PubSubClient _mqttClient;
    CommandHandlerCallback _cmdCallback;
    unsigned long _lastMqttReconnectAttempt;
    unsigned long _lastWifiReconnectAttempt;
    bool _ntpSynced;

    void connectWiFi();
    bool connectMQTT();
    void syncNTP();
};

#endif // AURASENSE_NETWORK_MANAGER_H
