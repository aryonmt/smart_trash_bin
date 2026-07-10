# backend/test_pipeline.py
# -------------------------------------------------------------------------
# End-to-End Pipeline Verification and Deception Scenario Simulation Script
# -------------------------------------------------------------------------

import json
import time

import paho.mqtt.publish as publish

# Broker Connection Configurations
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TELEMETRY_TOPIC = "wastebin/district-7/bin-0142/telemetry"

# Hardened Authentication Credentials (Must match Mosquitto's passwd database)
MQTT_USER = "bin_device"
MQTT_PASSWORD = "secure_bin_pass_2026"


def send_reading(distance_cm: float, uptime: int) -> None:
    """Publishes a schema-validated telemetry payload representing one reading cycle.

    Args:
        distance_cm: Raw simulated ultrasonic distance in centimeters.
        uptime: Mocked continuous uptime of the device in seconds.
    """
    payload = {
        "device_id": "bin-0142",
        "zone_id": "district-7",
        "distance_cm": distance_cm,
        "bin_depth_cm": 150.0,
        "sample_count": 11,
        "uptime_s": uptime,
    }

    # Configure authentication dictionary for secure broker handshake
    auth_config = {"username": MQTT_USER, "password": MQTT_PASSWORD}

    publish.single(
        TELEMETRY_TOPIC,
        payload=json.dumps(payload),
        hostname=MQTT_BROKER,
        port=MQTT_PORT,
        auth=auth_config,
    )
    print(f"[Simulated Client] Sent reading: {distance_cm} cm (Uptime: {uptime}s)")


def run_test() -> None:
    """Orchestrates five distinct physical waste bin testing scenarios.

    Simulated Scenarios:
        1. Empty Bin State (baseline).
        2. Spurious Transient Obstruction (outlier rejection).
        3. Genuine Constant Filling Up (streak confirmation).
        4. Object Shifting/apparent emptying (monotonic ratchet guard).
        5. Genuine Physical Emptying/municipal pickup (empty event).
    """
    print("=== Starting Hardened End-to-End Pipeline Simulation ===")
    uptime = 10

    # Scenario 1: Bin is completely empty (sensor distance = 150 cm)
    print("\n--- Scenario 1: Bin is empty ---")
    send_reading(150.0, uptime)
    time.sleep(2)

    # Scenario 2: Transient noise (e.g., a plastic bag flies close to the sensor)
    # The sensor reads 25 cm for only 1 cycle. The pipeline must reject this.
    print("\n--- Scenario 2: Transient Noise (Flying plastic bag) ---")
    uptime += 60
    send_reading(25.0, uptime)
    time.sleep(2)

    # Scenario 3: Bin starts filling up genuinely.
    # The sensor reads 90 cm consistently for 3 cycles (confirm_cycles = 3).
    # The pipeline must confirm this new fill level after the 3rd cycle.
    print("\n--- Scenario 3: Genuine Fill Up ---")
    for i in range(3):
        uptime += 60
        print(f"  Cycle {i + 1}/3:")
        send_reading(90.0, uptime)
        time.sleep(2)

    # Scenario 4: Object shifting.
    # An object inside the bin shifts, making the sensor temporarily read 120 cm (apparently emptier).
    # Since trash doesn't remove itself, the Ratchet Guard must keep the confirmed level at 90 cm.
    print("\n--- Scenario 4: Object shifts (apparent emptier reading) ---")
    uptime += 60
    send_reading(120.0, uptime)
    time.sleep(2)

    # Scenario 5: Real Empty Event (Municipal pickup)
    # The garbage truck empties the bin. The sensor consistently reads ~148 cm for 2 cycles.
    # The pipeline must register a real Empty Event and reset the state.
    print("\n--- Scenario 5: Genuine Empty Event ---")
    for i in range(2):
        uptime += 60
        print(f"  Cycle {i + 1}/2:")
        send_reading(148.0, uptime)
        time.sleep(2)

    print("\n=== Hardened Simulation Complete ===")


if __name__ == "__main__":
    run_test()
