#include "NetworkManager.h"
#include <time.h>

NetworkManager::NetworkManager() 
    : _mqttClient(_wifiClient), 
      _cmdCallback(nullptr), 
      _lastMqttReconnectAttempt(0), 
      _lastWifiReconnectAttempt(0),
      _ntpSynced(false) {}

void NetworkManager::begin(CommandHandlerCallback cmdCallback) {
    _cmdCallback = cmdCallback;
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    _mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
    _mqttClient.setBufferSize(768); // Ensure adequate buffer for JSON payloads

    if (_cmdCallback) {
        _mqttClient.setCallback(_cmdCallback);
    }

    connectWiFi();
}

void NetworkManager::connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.print("[WiFi] Connecting to SSID: ");
    Serial.println(WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startMs = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - startMs < 10000)) {
        delay(250);
        Serial.print(".");
        digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
        digitalWrite(PIN_STATUS_LED, HIGH);
        syncNTP();
    } else {
        Serial.println("\n[WiFi] Connection timeout. Will retry in background.");
        digitalWrite(PIN_STATUS_LED, LOW);
    }
}

void NetworkManager::syncNTP() {
    Serial.println("[NTP] Synchronizing UTC time...");
    configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER_1, NTP_SERVER_2);

    time_t now = 0;
    int retry = 0;
    while (now < 100000 && retry < 10) { // wait until epoch > Jan 1 1970
        delay(500);
        time(&now);
        retry++;
    }

    if (now > 100000) {
        _ntpSynced = true;
        Serial.printf("[NTP] Time synchronized! Current UTC Epoch: %lu\n", (unsigned long)now);
    } else {
        Serial.println("[NTP] Warning: Time synchronization pending.");
    }
}

bool NetworkManager::connectMQTT() {
    if (_mqttClient.connected()) return true;
    if (WiFi.status() != WL_CONNECTED) return false;

    Serial.printf("[MQTT] Attempting connection to %s:%d...\n", MQTT_BROKER_HOST, MQTT_BROKER_PORT);

    // Will topic & payload for automatic STALE node marking if abruptly disconnected
    char willTopic[64];
    snprintf(willTopic, sizeof(willTopic), "aurasense/nodes/%s/status", NODE_ID);
    const char *willPayload = "{\"status\":\"OFFLINE\"}";

    if (_mqttClient.connect(MQTT_CLIENT_ID, willTopic, 1, true, willPayload)) {
        Serial.println("[MQTT] Connected successfully!");

        // Subscribe to node commands and OTA triggers
        char subCmdTopic[64];
        char subOtaTopic[64];
        snprintf(subCmdTopic, sizeof(subCmdTopic), "aurasense/nodes/%s/cmd", NODE_ID);
        snprintf(subOtaTopic, sizeof(subOtaTopic), "aurasense/nodes/%s/ota/cmd", NODE_ID);

        _mqttClient.subscribe(subCmdTopic, 1);
        _mqttClient.subscribe(subOtaTopic, 1);
        Serial.printf("[MQTT] Subscribed to %s and %s\n", subCmdTopic, subOtaTopic);

        // Publish ONLINE status
        _mqttClient.publish(willTopic, "{\"status\":\"ONLINE\",\"version\":\"" FIRMWARE_VERSION "\"}", true);
        return true;
    } else {
        Serial.printf("[MQTT] Failed, rc=%d. Will retry.\n", _mqttClient.state());
        return false;
    }
}

void NetworkManager::update() {
    // Check WiFi
    if (WiFi.status() != WL_CONNECTED) {
        if (millis() - _lastWifiReconnectAttempt > 10000) {
            _lastWifiReconnectAttempt = millis();
            connectWiFi();
        }
        return;
    }

    // Check MQTT
    if (!_mqttClient.connected()) {
        if (millis() - _lastMqttReconnectAttempt > 5000) {
            _lastMqttReconnectAttempt = millis();
            connectMQTT();
        }
    } else {
        _mqttClient.loop();
    }
}

bool NetworkManager::isConnected() {
    return WiFi.status() == WL_CONNECTED && _mqttClient.connected();
}

bool NetworkManager::publishReading(const char *sensorType, const String &payloadJson) {
    if (!_mqttClient.connected()) {
        return false;
    }

    char topic[96];
    snprintf(topic, sizeof(topic), "aurasense/nodes/%s/%s", NODE_ID, sensorType);

    bool success = _mqttClient.publish(topic, payloadJson.c_str());
    if (success) {
        Serial.printf("[MQTT TX] %s -> %s\n", topic, payloadJson.c_str());
    } else {
        Serial.printf("[MQTT ERR] Failed to publish to %s\n", topic);
    }
    return success;
}

uint32_t NetworkManager::getEpochSeconds() {
    time_t now;
    time(&now);
    if (now < 100000) {
        // Fallback: approximate using millis if NTP not yet locked
        return 1720000000 + (millis() / 1000);
    }
    return (uint32_t)now;
}
