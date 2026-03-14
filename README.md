# Wall-A

A companion robot inspired by Wall-E, built on a 3D-printed tank chassis. The north-star goal: an autonomous trash-collecting machine with personality.

## Architecture

Three compute layers working together:

| Layer | Hardware | Role |
|-------|----------|------|
| **Firmware** | Arduino Uno + Motor Shield | Motor control, sensor reads, serial JSON |
| **Pi App** | Raspberry Pi 5 | Camera, audio, serial bridge, odometry |
| **GPU Server** | Desktop (GTX 3060) | YOLO vision, Whisper STT, Ollama LLM, Piper TTS |

See [CLAUDE.md](CLAUDE.md) for full architecture, data flow, hardware BOM, and roadmap.

## Project Structure

```
firmware/arduino/   — PlatformIO C++ (Arduino Uno)
pi/                 — Python package (Raspberry Pi 5)
server/             — Python package (GPU desktop)
shared/schemas/     — Protocol definitions (serial, WebSocket)
hardware/           — STLs, CAD, print guides, BOM
scripts/            — Deploy and flash helpers
```

## Quick Start

```bash
# Flash Arduino firmware
./scripts/flash-arduino.sh

# Deploy to Pi
./scripts/deploy-pi.sh

# Run GPU server locally
cd server && pip install -e . && walla-server
```
