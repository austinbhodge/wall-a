#!/usr/bin/env bash
# Build and upload Arduino firmware via PlatformIO.
# Usage: ./scripts/flash-arduino.sh [port]

set -euo pipefail

PORT="${1:-/dev/ttyACM0}"

echo "Building and uploading firmware..."
cd firmware/arduino

PIO="${PIO:-pio}"
# Use venv pio if available
if [ -x "$(dirname "$0")/../.venv/bin/pio" ]; then
    PIO="$(dirname "$0")/../.venv/bin/pio"
fi

$PIO run --target upload --upload-port "$PORT"

echo ""
echo "Upload complete! To monitor serial output:"
echo "  $PIO device monitor --port $PORT --baud 115200"
