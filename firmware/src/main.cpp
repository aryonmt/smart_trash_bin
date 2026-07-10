// firmware/src/main.cpp
// -------------------------------------------------------------------------
// Secure, Non-Blocking Smart Waste Bin Firmware with TLS Verification
// -------------------------------------------------------------------------

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include "config.h"

constexpr int TOTAL_SAMPLE_BURST = 11;

WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);
unsigned long lastMeasureTime = 0;

char telemetryTopic[128];
char statusTopic[128];
char cmdTopic[128];

void setupWiFi();
void syncTime();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
float readUltrasonicOnceCm();
float getFilteredDistance();

void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.println("\n==================================================");
    Serial.println("[System] Booting secure waste bin node...");
    Serial.println("==================================================");

    pinMode(TRIGGER_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);

    snprintf(telemetryTopic, sizeof(telemetryTopic), "wastebin/%s/%s/telemetry", ZONE_ID, DEVICE_ID);
    snprintf(statusTopic, sizeof(statusTopic), "wastebin/%s/%s/status", ZONE_ID, DEVICE_ID);
    snprintf(cmdTopic, sizeof(cmdTopic), "wastebin/%s/%s/cmd", ZONE_ID, DEVICE_ID);

    setupWiFi();
    syncTime(); // Sync time to allow SSL/TLS expiration checks

    // Configure Secure Client
    if (MQTT_PORT == 8883) {
        espClient.setCACert(MQTT_CA_CERT); // Enforce server identity verification via CA Cert
        Serial.println("[System] Secure TLS client initialized with custom Root CA.");
    } else {
        Serial.println("[System] Warning: Running over unencrypted insecure channel.");
    }

    espClient.setBufferSizes(2048, 1024); // Optimize SSL buffers for ESP32 RAM stability
    espClient.setTimeout(3);

    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastWiFiRetry = 0;
        if (millis() - lastWiFiRetry > 15000) {
            lastWiFiRetry = millis();
            Serial.println("[WiFi Debug] Re-initiating connection...");
            setupWiFi();
        }
    } else {
        if (!mqttClient.connected()) {
            connectMQTT();
        } else {
            mqttClient.loop();
        }
    }

    unsigned long currentMillis = millis();
    if (currentMillis - lastMeasureTime >= MEASURE_INTERVAL_MS) {
        lastMeasureTime = currentMillis;

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
}

void setupWiFi() {
    Serial.printf("[WiFi Debug] Connecting to SSID: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

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

void syncTime() {
    if (WiFi.status() != WL_CONNECTED) {
        return;
    }
    Serial.println("[Time Debug] Syncing time via NTP...");
    // Configure standard global NTP servers (GMT+3.5 for Tehran)
    configTime(3.5 * 3600, 0, "pool.ntp.org", "time.nist.gov");

    int attempts = 0;
    while (time(nullptr) < 1000000000 && attempts < 15) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (time(nullptr) >= 1000000000) {
        time_t now = time(nullptr);
        Serial.printf("\n[Time Debug] Clock synchronized! UTC: %s", ctime(&now));
    } else {
        Serial.println("\n[Time Debug] NTP sync failed. Certificate expiration validation will be bypassed.");
    }
}

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
        } else {
            Serial.printf("[MQTT Debug] Connection failed, rc=%d\n", mqttClient.state());
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
