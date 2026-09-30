#ifndef AURASENSE_CONFIG_H
#define AURASENSE_CONFIG_H

#include <Arduino.h>

// ==============================================================================
// AuraSense Node Hardware & Network Configuration
// ==============================================================================

// --- Node Identity ---
#define NODE_ID              "node_living_room"
#define FIRMWARE_VERSION     "1.1.0-arduino"

// --- Wi-Fi Credentials ---
#define WIFI_SSID            "YOUR_WIFI_SSID"
#define WIFI_PASSWORD        "YOUR_WIFI_PASSWORD"

// --- MQTT Hub Broker Configuration ---
// Point to the Raspberry Pi / Hub machine running Mosquitto (port 1883)
#define MQTT_BROKER_HOST     "192.168.1.100"
#define MQTT_BROKER_PORT     1883
#define MQTT_CLIENT_ID       "AuraSense_" NODE_ID
#define MQTT_QOS             1

// --- NTP Time Server (Required for valid UTC timestamps in TimescaleDB) ---
#define NTP_SERVER_1         "pool.ntp.org"
#define NTP_SERVER_2         "time.nist.gov"
#define GMT_OFFSET_SEC       0     // TimescaleDB expects UTC (0 offset)
#define DAYLIGHT_OFFSET_SEC  0

// ==============================================================================
// Sensor Selection & Sampling Rates
// Enable the sensors connected to this specific physical board
// ==============================================================================
#define ENABLE_ENV_SENSOR            true   // BME680 / BME280 (I2C)
#define ENABLE_MOTION_SENSOR         true   // mmWave Radar LD2410 / PIR (GPIO/UART)
#define ENABLE_OPTICAL_PULSE_SENSOR  false  // Electric Meter Phototransistor (GPIO Interrupt)
#define ENABLE_AUDIO_FEATURES        false  // MEMS Microphone feature extractor (I2S/Analog)

// --- Reporting Intervals (milliseconds) ---
#define INTERVAL_ENV_MS              10000  // Publish environmental metrics every 10s
#define INTERVAL_MOTION_MS           2000   // Motion/Presence evaluation every 2s
#define INTERVAL_PULSE_REPORT_MS     5000   // Utility power meter publish every 5s
#define INTERVAL_AUDIO_MS            3000   // Audio classification heartbeat every 3s
#define INTERVAL_HEARTBEAT_MS        30000  // Node keep-alive heartbeat

// ==============================================================================
// Pin Allocations (ESP32 / ESP32-S3 defaults - adapt to your board)
// ==============================================================================
// I2C for BME680 / BME280 / SHT31
#define PIN_I2C_SDA                  21
#define PIN_I2C_SCL                  22

// Motion / mmWave Radar Pin (Digital In from radar OUT pin, e.g. LD2410)
#define PIN_RADAR_PRESENCE           19
#define PIN_RADAR_FALL_OR_RAPID      18

// Optical Pulse Meter Reader (Interrupt Pin, Active LOW on pulse LED)
#define PIN_OPTICAL_PULSE            4
#define OPTICAL_METER_IMP_PER_KWH    1000  // e.g., 1000 or 1600 imp/kWh printed on utility meter

// Status Indicator LED
#define PIN_STATUS_LED               2     // Built-in LED on most ESP32 dev boards

#endif // AURASENSE_CONFIG_H
