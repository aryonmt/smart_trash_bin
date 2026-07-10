// firmware/src/main.cpp
// -------------------------------------------------------------------------
// Hardened, Non-Blocking Smart Waste Bin Firmware with Deep Diagnostic Logs
// -------------------------------------------------------------------------

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include "config.h"

// --- Hardware Pins for Trigger/Echo (Mode 1) ---
// constexpr int TRIGGER_PIN = 12;
// constexpr int ECHO_PIN = 13;
constexpr int TOTAL_SAMPLE_BURST = 11;

WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);
unsigned long lastMeasureTime = 0;

// Dynamic MQTT topics
char telemetryTopic[128];
char statusTopic[128];
char cmdTopic[128];

// Function Declarations
void setupWiFi();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
float readUltrasonicOnceCm();
float getFilteredDistance();

void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n==================================================");
    Serial.println("[System] Smart Waste Bin Booting up...");
    Serial.println("==================================================");

    pinMode(TRIGGER_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);

    // Formulate MQTT topics
    snprintf(telemetryTopic, sizeof(telemetryTopic), "wastebin/%s/%s/telemetry", ZONE_ID, DEVICE_ID);
    snprintf(statusTopic, sizeof(statusTopic), "wastebin/%s/%s/status", ZONE_ID, DEVICE_ID);
    snprintf(cmdTopic, sizeof(cmdTopic), "wastebin/%s/%s/cmd", ZONE_ID, DEVICE_ID);

    // Secure TLS: Tell ESP32 to encrypt but bypass certificate verification for local development
    espClient.setInsecure();
    espClient.setTimeout(3);

    setupWiFi();
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void loop() {
    // 1. Manage WiFi connection (Non-blocking reconnect attempts)
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastWiFiRetry = 0;
        if (millis() - lastWiFiRetry > 15000) { // Try to reconnect WiFi every 15 seconds
            lastWiFiRetry = millis();
            Serial.println("[WiFi Debug] Wi-Fi connection lost. Attempting to reconnect...");
            setupWiFi();
        }
    } else {
        // 2. Manage MQTT connection (Non-blocking reconnect attempts)
        if (!mqttClient.connected()) {
            connectMQTT();
        } else {
            mqttClient.loop();
        }
    }

    // 3. Perform sensory reading strictly on time interval (completely decoupled from network blocking)
    unsigned long currentMillis = millis();
    if (currentMillis - lastMeasureTime >= MEASURE_INTERVAL_MS) {
        lastMeasureTime = currentMillis;

        float distance = getFilteredDistance();

        if (distance > 0) {
            JsonDocument doc;
            doc["device_id"] = DEVICE_ID;
            doc["zone_id"] = ZONE_ID;
            doc["distance_cm"] = round(distance * 100.0) / 100.0;
            doc["bin_depth_cm"] = BIN_DEPTH_CM;  // Added dynamically from config.h!
            doc["sample_count"] = TOTAL_SAMPLE_BURST;
            doc["uptime_s"] = millis() / 1000;

            char payloadBuffer[256];
            serializeJson(doc, payloadBuffer);

            if (mqttClient.publish(telemetryTopic, payloadBuffer)) {
                Serial.printf("[MQTT Debug] Telemetry published: %s\n", payloadBuffer);
            } else {
                Serial.println("[MQTT Debug] Telemetry publish failed.");
            }
        } else {
            Serial.println("[Sensor Debug] Sensor read fault.");
        }
    }
}

void setupWiFi() {
    Serial.printf("[WiFi Debug] Initiating connection to SSID: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    // Limit blocking connection attempt to maximum 10 seconds during startup
    int timeoutAttempts = 0;
    while (WiFi.status() != WL_CONNECTED && timeoutAttempts < 20) {
        delay(500);
        Serial.print(".");
        timeoutAttempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[WiFi Debug] Connected! Local IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[WiFi Debug] Connection attempt timed out. Will retry in background...");
    }
}

void connectMQTT() {
    static unsigned long lastMqttRetry = 0;
    unsigned long currentMillis = millis();

    // Limit reconnection attempts to once every 10 seconds to keep loop non-blocking
    if (currentMillis - lastMqttRetry > 10000) {
        lastMqttRetry = currentMillis;

        if (WiFi.status() != WL_CONNECTED) {
            return; // Cannot connect MQTT without WiFi
        }

        Serial.printf("[MQTT Debug] Attempting secure MQTTS connection to %s:%d...\n", MQTT_SERVER, MQTT_PORT);
        String clientId = "BinClient-" + String(DEVICE_ID) + "-" + String(random(0xffff), HEX);

        bool connected = mqttClient.connect(
            clientId.c_str(),
            MQTT_USER,
            MQTT_PASSWORD,
            statusTopic,
            1,            // QoS
            true,         // Retained
            "offline"     // LWT message
        );

        if (connected) {
            Serial.println("[MQTT Debug] Connection established successfully!");
            mqttClient.publish(statusTopic, "online", true);
            mqttClient.subscribe(cmdTopic);
        } else {
            Serial.printf("[MQTT Debug] Connection failed, rc=%d. Will retry in 10 seconds in background...\n", mqttClient.state());
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.printf("[MQTT Callback] Message arrived on topic: %s\n", topic);
}

float readUltrasonicOnceCm() {
    digitalWrite(TRIGGER_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER_PIN, LOW);

    // Pulse timeout capped at 30ms (~5 meters)
    long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    if (duration == 0) {
        return -1.0f;
    }
    return (duration * 0.0343f) / 2.0f;
}

float getFilteredDistance() {
    std::vector<float> samples;
    int successReads = 0;

    for (int i = 0; i < TOTAL_SAMPLE_BURST; i++) {
        float raw = readUltrasonicOnceCm();

        // Print raw diagnostics to track physical state of sensor
        Serial.printf("  [Raw Diagnostic] Pulse %d/%d: %.2f cm\n", i + 1, TOTAL_SAMPLE_BURST, raw);

        if (raw >= SENSOR_BLIND_ZONE_CM && raw <= (BIN_DEPTH_CM + 10.0f)) {
            samples.push_back(raw);
            successReads++;
        }
        delay(50);
    }

    Serial.printf("[Sensor Debug] Total valid pulses in burst: %d/%d\n", successReads, TOTAL_SAMPLE_BURST);

    if (samples.size() < (TOTAL_SAMPLE_BURST / 2)) {
        return -1.0f; // Return error if more than half of pulses failed
    }

    std::sort(samples.begin(), samples.end());
    float median = samples[samples.size() / 2];

    float sum = 0;
    int count = 0;
    constexpr float toleranceCm = 15.0f;

    for (float val : samples) {
        if (std::abs(val - median) <= toleranceCm) {
            sum += val;
            count++;
        }
    }

    return (count > 0) ? (sum / count) : median;
}
