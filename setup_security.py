# setup_security.py
# -------------------------------------------------------------------------
# Automates local TLS self-signed certs and Mosquitto password file creation
# -------------------------------------------------------------------------

import os
import shutil
import subprocess


def run_command(command: list) -> None:
    """Executes a system shell command safely, validating return codes.

    Args:
        command: List of command arguments to pass to the subprocess.
    """
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[Error] Command execution failed: {e}")
        exit(1)


def load_env() -> dict:
    """Loads and parses the environmental secrets from the root .env file.

    Returns:
        dict: Parsed key-value pairs of environment credentials.
    """
    env_vars = {}
    if not os.path.exists(".env"):
        print("[Error] No .env file found in root folder! Creating template first.")
        shutil.copy(".env.example", ".env")
        print(
            "[System] Template .env file generated. Please inspect and update configuration."
        )

    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                env_vars[key.strip()] = val.strip()
    return env_vars


def main() -> None:
    """Orchestrates directory creations, SSL keys generation and MQTT password database."""
    print("=== Commencing Smart Waste Bin Security Provisioning ===")

    # 1. Load variables from environment
    env = load_env()
    bin_pass = env.get("MQTT_BIN_PASSWORD", "secure_bin_pass_2026")
    ingest_pass = env.get("MQTT_INGESTION_PASSWORD", "secure_ingestion_pass_2026")

    # 2. Re-create directories
    os.makedirs("mosquitto/certs", exist_ok=True)
    os.makedirs("mosquitto/config", exist_ok=True)

    print(
        "\n[Step 1] Generating TLS/SSL self-signed certificates via Docker container..."
    )
    pwd_env = os.getcwd()

    cert_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{pwd_env}/mosquitto:/workspace",
        "-w",
        "/workspace",
        "alpine",
        "sh",
        "-c",
        "apk add --no-cache openssl && "
        "openssl req -new -x509 -days 3650 -extensions v3_ca -keyout certs/ca.key -out certs/ca.crt -subj '/CN=MyLocalCA' -nodes && "
        "openssl req -newkey rsa:2048 -nodes -keyout certs/server.key -out certs/server.csr -subj '/CN=localhost' && "
        "openssl x509 -req -days 365 -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial -out certs/server.crt",
    ]
    run_command(cert_command)
    print(
        "[Success] Certificates generated successfully under 'mosquitto/certs/' folder."
    )

    print(
        "\n[Step 2] Provisioning secure password database 'passwd' for MQTT Broker..."
    )
    passwd_cmd_1 = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{pwd_env}/mosquitto:/workspace",
        "-w",
        "/workspace",
        "eclipse-mosquitto:2.0.18",
        "mosquitto_passwd",
        "-b",
        "-c",
        "config/passwd",
        "bin_device",
        bin_pass,
    ]
    passwd_cmd_2 = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{pwd_env}/mosquitto:/workspace",
        "-w",
        "/workspace",
        "eclipse-mosquitto:2.0.18",
        "mosquitto_passwd",
        "-b",
        "config/passwd",
        "ingestion_service",
        ingest_pass,
    ]
    run_command(passwd_cmd_1)
    run_command(passwd_cmd_2)
    print(
        "[Success] Password database successfully provisioned with hashed credentials."
    )
    print("\n=== Hardening Provisioning Finished. System is ready to boot securely ===")


if __name__ == "__main__":
    main()
