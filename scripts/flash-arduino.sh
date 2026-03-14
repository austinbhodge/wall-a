#!/usr/bin/env bash
# Build and upload Arduino firmware via PlatformIO.
# Usage: ./scripts/flash-arduino.sh [port]

set -euo pipefail

PORT="${1:-/dev/ttyACM0}"

echo "Building and uploading firmware..."
cd firmware/arduino

pio run --target upload --upload-port "$PORT"

echo "Opening serial monitor..."
pio device monitor --port "$PORT" --baud 115200
