// firmware/src/main.cpp
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include "config.h"

// --- Hardware Pins for Trigger/Echo (Mode 1) ---
constexpr int TRIGGER_PIN = 12;
constexpr int ECHO_PIN = 13;
constexpr int TOTAL_SAMPLE_BURST = 11;

WiFiClient espClient;
PubSubClient mqttClient(espClient);
unsigned long lastMeasureTime = 0;

// Dynamic topic buffers
char telemetryTopic[128];
char statusTopic[128];
char cmdTopic[128];

void setupWiFi();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
float readUltrasonicOnceCm();
float getFilteredDistance();

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n--- Smart Waste Bin Initializing ---");

    pinMode(TRIGGER_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);

    // Formulate dynamic MQTT topics based on provisioning details
    snprintf(telemetryTopic, sizeof(telemetryTopic), "wastebin/%s/%s/telemetry", ZONE_ID, DEVICE_ID);
    snprintf(statusTopic, sizeof(statusTopic), "wastebin/%s/%s/status", ZONE_ID, DEVICE_ID);
    snprintf(cmdTopic, sizeof(cmdTopic), "wastebin/%s/%s/cmd", ZONE_ID, DEVICE_ID);

    setupWiFi();
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        setupWiFi();
    }
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop();

    unsigned long currentMillis = millis();
    if (currentMillis - lastMeasureTime >= MEASURE_INTERVAL_MS) {
        lastMeasureTime = currentMillis;

        float distance = getFilteredDistance();

        if (distance > 0) {
            JsonDocument doc;
            doc["device_id"] = DEVICE_ID;
            doc["zone_id"] = ZONE_ID;
            doc["distance_cm"] = round(distance * 100.0) / 100.0;
            doc["sample_count"] = TOTAL_SAMPLE_BURST;
            doc["uptime_s"] = millis() / 1000;

            char payloadBuffer[256];
            serializeJson(doc, payloadBuffer);

            if (mqttClient.publish(telemetryTopic, payloadBuffer)) {
                Serial.printf("[MQTT] Telemetry published to %s\n", telemetryTopic);
            } else {
                Serial.println("[MQTT] Telemetry publish failed.");
            }
        } else {
            Serial.println("[Sensor] Sensor read fault or bin fully obstructed.");
        }
    }
}

void setupWiFi() {
    delay(10);
    Serial.printf("[WiFi] Connecting to SSID: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[WiFi] Connected! IP Address: %s\n", WiFi.localIP().toString().c_str());
}

void connectMQTT() {
    while (!mqttClient.connected()) {
        Serial.println("[MQTT] Attempting connection...");
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
            Serial.println("[MQTT] Connected to broker.");
            mqttClient.publish(statusTopic, "online", true);
            mqttClient.subscribe(cmdTopic);
        } else {
            Serial.printf("[MQTT] Connection failed, rc=%d. Retrying in 5 seconds...\n", mqttClient.state());
            delay(5000);
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.printf("[MQTT] Command received on topic: %s\n", topic);
}

float readUltrasonicOnceCm() {
    digitalWrite(TRIGGER_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    if (duration == 0) {
        return -1.0f;
    }
    return (duration * 0.0343f) / 2.0f;
}

float getFilteredDistance() {
    std::vector<float> samples;
    for (int i = 0; i < TOTAL_SAMPLE_BURST; i++) {
        float raw = readUltrasonicOnceCm();
        if (raw >= SENSOR_BLIND_ZONE_CM && raw <= (BIN_DEPTH_CM + 10.0f)) {
            samples.push_back(raw);
        }
        delay(50);
    }

    if (samples.size() < (TOTAL_SAMPLE_BURST / 2)) {
        return -1.0f;
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
