// firmware/src/main.cpp
// -------------------------------------------------------------------------
// Smart Waste Bin IoT Firmware - Constant Power Version (No Deep Sleep)
// -------------------------------------------------------------------------

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

// --- Global Objects ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);
unsigned long lastMeasureTime = 0;

// --- Function Declarations ---
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

    setupWiFi();
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void loop() {
    // Keep WiFi and MQTT connections alive
    if (WiFi.status() != WL_CONNECTED) {
        setupWiFi();
    }
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop();

    // Trigger measurement periodically based on configuration
    unsigned long currentMillis = millis();
    if (currentMillis - lastMeasureTime >= MEASURE_INTERVAL_MS) {
        lastMeasureTime = currentMillis;

        float distance = getFilteredDistance();

        // Only publish if a valid reading was obtained
        if (distance > 0) {
            JsonDocument doc;
            doc["device_id"] = "bin-0142"; // Unique device ID for testing
            doc["distance_cm"] = round(distance * 100.0) / 100.0;
            doc["uptime_s"] = millis() / 1000;

            char payloadBuffer[256];
            serializeJson(doc, payloadBuffer);

            // Publish to the telemetry topic
            if (mqttClient.publish("wastebin/district-7/bin-0142/telemetry", payloadBuffer)) {
                Serial.printf("[MQTT] Published telemetry: %s\n", payloadBuffer);
            } else {
                Serial.println("[MQTT] Failed to publish telemetry.");
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
        // Using a unique client ID and Last Will testament
        String clientId = "BinClient-" + String(random(0xffff), HEX);

        bool connected = mqttClient.connect(
            clientId.c_str(),
            MQTT_USER,
            MQTT_PASSWORD,
            "wastebin/district-7/bin-0142/status", // LWT topic
            1,                                    // QoS
            true,                                 // Retained
            "offline"                             // LWT message
        );

        if (connected) {
            Serial.println("[MQTT] Connected to broker.");
            // Publish status as online
            mqttClient.publish("wastebin/district-7/bin-0142/status", "online", true);

            // Subscribe to commands
            mqttClient.subscribe("wastebin/district-7/bin-0142/cmd");
        } else {
            Serial.printf("[MQTT] Connection failed, rc=%d. Retrying in 5 seconds...\n", mqttClient.state());
            delay(5000);
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.printf("[MQTT] Message arrived on topic: %s\n", topic);
    // Command handling logic will be expanded here
}

/**
 * @brief Measures raw distance once using physical Trigger and Echo pulses.
 * @return Raw distance in cm, or -1.0 if timeout occurred.
 */
float readUltrasonicOnceCm() {
    digitalWrite(TRIGGER_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER_PIN, LOW);

    // Timeout in 30ms (corresponds to ~5 meters max distance)
    long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    if (duration == 0) {
        return -1.0f;
    }
    return (duration * 0.0343f) / 2.0f;
}

/**
 * @brief Takes a burst of 11 samples, filters outliers, and returns the mean of valid samples.
 *        This implements Stage-1 filtering on the Edge.
 */
float getFilteredDistance() {
    std::vector<float> samples;
    const int totalSamples = 11;

    for (int i = 0; i < totalSamples; i++) {
        float raw = readUltrasonicOnceCm();
        // Check if the reading is within physically plausible bounds
        if (raw >= SENSOR_BLIND_ZONE_CM && raw <= (BIN_DEPTH_CM + 10.0f)) {
            samples.push_back(raw);
        }
        delay(50); // Small delay to avoid interference between sequential pulses
    }

    if (samples.size() < (totalSamples / 2)) {
        // Not enough valid readings; suspect sensor failure or total obstruction
        return -1.0f;
    }

    // Sort to compute the median
    std::sort(samples.begin(), samples.end());
    float median = samples[samples.size() / 2];

    // Filter out values far from the median (simple outlier rejection)
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
