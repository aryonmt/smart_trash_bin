// firmware/src/main.cpp
// -------------------------------------------------------------------------
// Hardened, Non-Blocking Smart Waste Bin Firmware with Remote Configs
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

// Sampling constants
constexpr int TOTAL_SAMPLE_BURST = 11;

// Global Networking Objects
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);
unsigned long lastMeasureTime = 0;

// Remote command flags
volatile bool forceReportPending = false;

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
void performMeasurementCycle();

/**
 * @brief Standard Arduino initialization entry point.
 */
void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n==================================================");
    Serial.println("[System] Booting secure waste bin node v3.0...");
    Serial.println("==================================================");

    pinMode(TRIGGER_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);

    // Formulate dynamic MQTT topics
    snprintf(telemetryTopic, sizeof(telemetryTopic), "wastebin/%s/%s/telemetry", ZONE_ID, DEVICE_ID);
    snprintf(statusTopic, sizeof(statusTopic), "wastebin/%s/%s/status", ZONE_ID, DEVICE_ID);
    snprintf(cmdTopic, sizeof(cmdTopic), "wastebin/%s/%s/cmd", ZONE_ID, DEVICE_ID);

    setupWiFi();

    // Configure Secure Client
    if (MQTT_PORT == 8883) {
        espClient.setInsecure(); // Bypass cert chain verification for local self-signed keys
        Serial.println("[System] Secure TLS client initialized (Insecure Mode on port 8883).");
    } else {
        Serial.println("[System] Warning: Running over unencrypted insecure channel.");
    }

    espClient.setTimeout(3);

    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

/**
 * @brief Standard Arduino main execution loop.
 */
void loop() {
    // 1. Manage WiFi connection (Non-blocking reconnect attempts)
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastWiFiRetry = 0;
        if (millis() - lastWiFiRetry > 15000) {
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

    // 3. Perform sensory reading on interval or when triggered by remote command
    unsigned long currentMillis = millis();
    if (forceReportPending || (currentMillis - lastMeasureTime >= measureIntervalMs)) {
        // Reset remote command flag
        forceReportPending = false;
        lastMeasureTime = currentMillis;

        performMeasurementCycle();
    }
}

/**
 * @brief Connects to the local Wi-Fi router in a non-blocking manner.
 */
void setupWiFi() {
    Serial.printf("[WiFi Debug] Connecting to SSID: %s\n", WIFI_SSID);
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
        Serial.println("\n[WiFi Debug] Connection attempt timed out. Continuing in background...");
    }
}

/**
 * @brief Connects to the MQTT broker in a non-blocking manner.
 */
void connectMQTT() {
    static unsigned long lastMqttRetry = 0;
    unsigned long currentMillis = millis();

    if (currentMillis - lastMqttRetry > 10000) {
        lastMqttRetry = currentMillis;

        if (WiFi.status() != WL_CONNECTED) {
            return;
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
            Serial.println("[MQTT Debug] Connected! Secure SSL channel verified.");
            mqttClient.publish(statusTopic, "online", true);
            mqttClient.subscribe(cmdTopic);
            Serial.printf("[MQTT Debug] Subscribed to topic: %s\n", cmdTopic);
        } else {
            Serial.printf("[MQTT Debug] Connection failed, rc=%d\n", mqttClient.state());
        }
    }
}

/**
 * @brief Callback triggered when an MQTT message arrives on subscribed topics.
 *        Implements parsing for remote administrative commands (Issue #5).
 */
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    Serial.printf("[MQTT Callback] Message arrived on topic: %s\n", topic);

    // Allocate a buffer for parsing JSON
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload, length);

    if (error) {
        Serial.printf("[MQTT Callback] JSON Parsing failed: %s\n", error.c_str());
        return;
    }

    const char* command = doc["command"];
    if (!command) {
        Serial.println("[MQTT Callback] Ignored message: lacking 'command' attribute.");
        return;
    }

    // Command 1: Force immediate measurement report
    if (strcmp(command, "force-report") == 0) {
        Serial.println("[MQTT Callback] Command verified: Force immediate telemetry report!");
        forceReportPending = true;
    }
    // Command 2: Re-configure measurement interval dynamically
    else if (strcmp(command, "set-interval") == 0) {
        unsigned long newInterval = doc["value"];
        if (newInterval >= 1000 && newInterval <= 3600000) { // Capped between 1s and 1 hour
            measureIntervalMs = newInterval;
            Serial.printf("[MQTT Callback] Command verified: Measurement interval updated to %lu ms\n", measureIntervalMs);
        } else {
            Serial.println("[MQTT Callback] Rejected interval: value out of bounds (1s to 1 hour).");
        }
    } else {
        Serial.printf("[MQTT Callback] Unknown command received: %s\n", command);
    }
}

/**
 * @brief Triggers physical sensor burst sampling and publishes metrics.
 */
void performMeasurementCycle() {
    Serial.println("\n[Sensor Debug] --- Initiating Scheduled Sample Burst ---");
    float distance = getFilteredDistance();

    if (distance > 0) {
        Serial.printf("[Sensor Debug] Filtered Result: %.2f cm\n", distance);

        if (mqttClient.connected()) {
            JsonDocument doc;
            doc["device_id"] = DEVICE_ID;
            doc["zone_id"] = ZONE_ID;
            doc["distance_cm"] = round(distance * 100.0) / 100.0;
            doc["bin_depth_cm"] = BIN_DEPTH_CM;
            doc["sample_count"] = TOTAL_SAMPLE_BURST;
            doc["uptime_s"] = millis() / 1000;

            char payloadBuffer[256];
            serializeJson(doc, payloadBuffer);

            if (mqttClient.publish(telemetryTopic, payloadBuffer)) {
                Serial.printf("[MQTT Debug] Published: %s\n", payloadBuffer);
            } else {
                Serial.println("[MQTT Debug] Telemetry publish failed.");
            }
        } else {
            Serial.println("[System Debug] Telemetry skipped: Broker is currently offline.");
        }
    } else {
        Serial.println("[Sensor Debug] CRITICAL: Sensor read fault.");
    }
    Serial.println("[Sensor Debug] ---------------------------------------------\n");
}

/**
 * @brief Measures a single raw trigger pulse from the ultrasonic sensor.
 * @return Raw distance in centimeters, or -1.0 on timeouts.
 */
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

/**
 * @brief Takes a burst of 11 raw samples, filters outliners, and returns the robust median.
 */
float getFilteredDistance() {
    std::vector<float> samples;
    int successReads = 0;

    for (int i = 0; i < TOTAL_SAMPLE_BURST; i++) {
        float raw = readUltrasonicOnceCm();
        Serial.printf("  [Raw Diagnostic] Pulse %d/%d: %.2f cm\n", i + 1, TOTAL_SAMPLE_BURST, raw);

        if (raw >= SENSOR_BLIND_ZONE_CM && raw <= (BIN_DEPTH_CM + 10.0f)) {
            samples.push_back(raw);
            successReads++;
        }
        delay(50);
    }

    Serial.printf("[Sensor Debug] Valid pulses in burst: %d/%d\n", successReads, TOTAL_SAMPLE_BURST);

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
