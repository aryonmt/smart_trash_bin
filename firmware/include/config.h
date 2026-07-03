// firmware/include/config.h
#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// --- Wi-Fi Configuration ---
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// --- MQTT Configuration ---
extern const char* MQTT_SERVER;
extern const int MQTT_PORT;
extern const char* MQTT_USER;
extern const char* MQTT_PASSWORD;

// --- Hardware Pins (ESP32 DevKit V1) ---
// Using Hardware Serial 2 (UART2) for AJ-SR04M in Mode 3 (TTL)
#define SENSOR_RX_PIN 16
#define SENSOR_TX_PIN 17

// --- Physical Bin Constants ---
// Constant vertical distance (cm) from sensor to the bottom of the bin
constexpr float BIN_DEPTH_CM = 150.0f;

// Sensor minimum measuring distance (blind zone)
constexpr float SENSOR_BLIND_ZONE_CM = 20.0f;

// Interval between measurement cycles in milliseconds (e.g., 60 seconds)
constexpr unsigned long MEASURE_INTERVAL_MS = 60000;

#endif // CONFIG_H
