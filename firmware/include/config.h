// firmware/include/config.h
#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// --- Device Provisioning Information ---
extern const char* DEVICE_ID;
extern const char* ZONE_ID;

// --- Wi-Fi Configuration ---
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// --- MQTT Configuration ---
extern const char* MQTT_SERVER;
extern const int MQTT_PORT;
extern const char* MQTT_USER;
extern const char* MQTT_PASSWORD;

// --- Hardware Pins (ESP32 DevKit V1) ---
#define TRIGGER_PIN 12             // Hardware Trigger Pin
#define ECHO_PIN 13                // Hardware Echo Pin

// --- Physical Bin Constants ---
constexpr float BIN_DEPTH_CM = 150.0f;
constexpr float SENSOR_BLIND_ZONE_CM = 20.0f;
constexpr float FULL_LINE_CM = BIN_DEPTH_CM - SENSOR_BLIND_ZONE_CM;

// Interval between measurement cycles (e.g., 5 seconds for testing)
constexpr unsigned long MEASURE_INTERVAL_MS = 5000;

#endif // CONFIG_H
