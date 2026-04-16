# CLAUDE.md — Wall-A Robot Project

## Project Overview

Wall-A is a companion robot inspired by Wall-E, built on a 3D-printed tank chassis with the north-star goal of becoming an autonomous trash-collecting machine. The project encompasses the robot's operating system, computer vision pipeline, and AI personality layer.

This is a monorepo containing firmware, application code, vision processing, and hardware documentation for the entire Wall-A system.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  GPU Server (Desktop — NVIDIA GTX 3060 12GB)            │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │ YOLOv8   │ │ Whisper  │ │ LLM (Ollama│ │ TTS      │ │
│  │ Object   │ │ STT      │ │ Llama 3.1) │ │ (Piper)  │ │
│  │ Detection│ │          │ │            │ │          │ │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘ └────┬─────┘ │
│       └─────────────┴─────────────┴─────────────┘       │
│                         ▲  │                             │
│                    WiFi │  │ commands / audio             │
└─────────────────────────┼──┼────────────────────────────┘
                          │  ▼
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi 5 (hostname: pi5, user: austin)           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Camera   │ │ Audio    │ │ Sensor   │ │ Serial    │  │
│  │ Capture  │ │ I/O      │ │ Fusion   │ │ Bridge    │  │
│  │ & Stream │ │ (mic +   │ │          │ │ (to       │  │
│  │          │ │ speaker) │ │          │ │ Arduino)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └─────┬─────┘  │
│                                                │        │
│  SSH: ssh austin@pi5.local                     │ USB    │
│  Remote: Raspberry Pi Connect                  │ Serial │
└────────────────────────────────────────────────┼────────┘
                                                 ▼
┌─────────────────────────────────────────────────────────┐
│  Arduino Uno + Motor Shield                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐    │
│  │ Motor    │ │ Sensor   │ │ Future: servo for     │    │
│  │ Control  │ │ Reads    │ │ tail / arm / etc.     │    │
│  │ (PWM)    │ │ (IMU,    │ │                       │    │
│  │          │ │  bump,   │ │                       │    │
│  │          │ │  etc.)   │ │                       │    │
│  └────┬─────┘ └──────────┘ └───────────────────────┘    │
│       │                                                  │
└───────┼──────────────────────────────────────────────────┘
        ▼
┌─────────────────────────────────────────────────────────┐
│  Chassis: 3D Printed Tank (Thingiverse thing:2753227)   │
│  Drive: Tamiya 70097 Twin-Motor Gearbox (203:1 ratio)   │
│  Steering: Differential drive (tank-style)              │
└─────────────────────────────────────────────────────────┘
```

## Data Flow — Context Pipeline

All sensor and perception data flows upward through the stack, enriching the context passed to Claude / the LLM for decision-making:

```
Arduino (raw sensor data: motor encoder ticks, IMU, bump sensors)
  │
  ├─► Serial JSON to Pi ──► Robot State object
  │     {
  │       "motors": { "left_speed": 120, "right_speed": 115 },
  │       "imu": { "roll": 2.1, "pitch": -0.5, "yaw": 178.3 },
  │       "battery_voltage": 7.2,
  │       "bump_sensors": { "front_left": false, "front_right": false }
  │     }
  │
  ├─► Pi enriches with position estimate (odometry / SLAM)
  │     {
  │       "position": { "x": 1.3, "y": 0.7, "theta": 178.3 },
  │       "map_confidence": 0.85,
  │       "nearby_obstacles": [...]
  │     }
  │
  └─► GPU server receives full context for LLM / vision
        {
          "robot_state": { ... },          // from Arduino via Pi
          "position": { ... },              // from Pi (SLAM/odometry)
          "vision": {                       // from YOLO on GPU
            "objects": [
              { "label": "trash", "confidence": 0.92, "bbox": [...] },
              { "label": "cat", "confidence": 0.98, "bbox": [...] }
            ]
          },
          "audio": {                        // from Whisper on GPU
            "transcript": "Hey Wall-A!",
            "ambient_db": 45,
            "cat_vocalization_detected": true
          }
        }
```

## Hardware Bill of Materials

### Chassis — 3D Printed Tank (Thingiverse thing:2753227)

A small tracked robot designed for prototyping, using 22mm skateboard bearings for improved ground clearance and track flexibility. Printable on beds >= 120mm.

| Part | Quantity | Notes |
|------|----------|-------|
| M3 Screws (10mm) | 24 | |
| M3 Nuts | 28 | |
| M3 Standoffs (30mm) | 8 | |
| 22mm Skateboard Bearings (8mm bore, 7mm thick) | 8 | |
| Tamiya 70097 Twin-Motor Gearbox Kit | 1 | **Set to 203:1 gear ratio** |

### Electronics

| Component | Details |
|-----------|---------|
| Raspberry Pi 5 | Main compute on robot. Headless Ubuntu 24.04 Server |
| Arduino Uno | Low-level motor/sensor control |
| Motor Shield (on Arduino) | Drives the Tamiya twin motors |
| Raspberry Pi Camera Module 3 | imx708 sensor, 4608×2592, CSI ribbon to CAM/DISP 0 — mounted on chassis |
| USB Microphone | For speech input, audio level monitoring |
| Small Speaker | For TTS output (Piper TTS on Pi or streamed from GPU) |
| USB Power Bank | Powers the Pi 5 via USB-C |
| Motor Battery Pack | Separate power for motors via motor shield |

### GPU Server (Desktop)

| Component | Details |
|-----------|---------|
| NVIDIA GTX 3060 (12GB VRAM) | Runs inference: YOLO, Whisper, LLM, TTS |
| Ollama | Local LLM hosting (Llama 3.1 8B or similar) |

## Connectivity

- **Pi ↔ Arduino**: USB Serial (common ground shared between power systems)
- **Pi ↔ Desktop GPU**: WiFi — video via MJPEG/GStreamer H.264, commands via WebSocket/MQTT
- **Pi SSH**: `ssh austin@pi5.local` (ed25519 key auth configured)
- **Pi Remote**: Raspberry Pi Connect (browser-based, works from anywhere)

## Software Stack

### Arduino Firmware (`/firmware/arduino/`)
- Motor control (differential drive via PWM)
- Sensor polling (IMU, bump sensors, battery voltage)
- Serial protocol: JSON messages over USB at 115200 baud
- Future: servo control for dynamic tail, arm mechanisms

### Pi Application (`/pi/`)
- Camera capture and streaming to GPU server
- Audio capture (mic) and playback (speaker)
- Serial bridge to Arduino (read sensors, send motor commands)
- Odometry / position estimation
- Future: ROS 2 nodes (Jazzy on Ubuntu 24.04)

### GPU Server (`/server/`)
- Computer vision pipeline (YOLOv8 object detection)
- Speech-to-text (Whisper)
- LLM personality engine (Ollama)
- Text-to-speech (Piper TTS)
- Context assembly: merges vision + audio + robot state for LLM
- Command generation: translates LLM decisions into motor commands

### Shared (`/shared/`)
- Protocol definitions (serial message format, WebSocket schemas)
- Robot state types/models
- Configuration files

## Wall-A's Personality

Wall-A is a determined little trash collector inspired by Wall-E. Personality traits to encode in the LLM system prompt:

- Curious about objects, excited when finding new things
- Determined and task-focused — always looking for trash to collect
- A little nervous about stairs and drop-offs
- Reacts to the cat with a mix of wariness and affection
- Speaks in short, expressive sentences
- Gets genuinely happy when the environment is cleaner

### Cat Noise Detection (Special Feature)
Wall-A monitors ambient audio levels. When cat vocalizations exceed a threshold, Wall-A navigates toward the cat and intervenes in-character (e.g., "Hey, keep it down in here."). This combines:
- Audio level monitoring from the USB mic
- Cat vocalization classification (Whisper + custom audio classifier)
- YOLO cat detection for localization
- Navigation toward the cat
- In-character TTS response

## 3D Printed Parts

### Philosophy on Source Control for Physical Parts

STL files **should** live in the repo. GitHub renders STL files inline, making it easy to preview parts without downloading. The recommended approach:

```
/hardware/
  /chassis/                    # Tank chassis parts (Thingiverse thing:2753227)
    README.md                  # Print settings, assembly notes, attribution
    /stl/                      # Print-ready STL files
      chassis_left.stl
      chassis_right.stl
      track_link.stl
      sprocket.stl
      ...
    /source/                   # Editable CAD files (if you have them)
      ...                      # Onshape links, .f3d, .step, etc.
  /custom/                     # Your own designed parts
    /camera_mount/
      camera_mount.stl
      camera_mount.step        # Keep editable source alongside STL
    /tail/                     # Dynamic tail assembly
      ...
    /mounts/                   # Arduino mount, Pi mount, speaker bracket, etc.
      ...
  BOM.md                       # Full bill of materials with sourcing links
  PRINT_GUIDE.md               # Print settings per part (layer height, infill, supports)
```

**Best practices:**
- Use Git LFS for large STL/STEP files (`git lfs track "*.stl" "*.step" "*.3mf"`)
- Keep both STL (print-ready) and source CAD files (STEP, .f3d, Onshape links)
- The Thingiverse chassis STLs are third-party — include attribution and license info
- Your custom parts (camera mounts, Pi brackets, tail mechanism) absolutely belong in the repo with version history
- Include print settings in a README or PRINT_GUIDE.md (layer height, infill %, supports, material)
- Screenshots or renders of assembled parts help future-you and contributors

### Note on Third-Party STLs
The base chassis (Thingiverse thing:2753227) was designed by its creator for classroom prototyping. The creator has stated they cannot share source CAD files. Respect the license — include attribution and link back to the original Thingiverse listing. If you modify any of the STLs, note your changes clearly.

## Future Roadmap

### Phase 1 — Mobile Base (Current)
- [x] Chassis printed and assembled
- [x] Tamiya gearbox at 203:1
- [x] Arduino + motor shield wired
- [x] Pi 5 set up (SSH, Pi Connect)
- [ ] Serial communication Pi ↔ Arduino
- [ ] Basic motor control from Pi (forward, back, turn)
- [ ] Camera streaming Pi → GPU server

### Phase 2 — Perception
- [ ] YOLO object detection on GPU server
- [ ] Monocular depth estimation (Depth Anything v2)
- [ ] Basic obstacle avoidance
- [ ] Visual SLAM (ORB-SLAM3) for position tracking
- [ ] Cat detection and tracking

### Phase 3 — Personality & Voice
- [ ] Whisper STT pipeline (mic → Pi → GPU → transcription)
- [ ] Ollama LLM with Wall-A system prompt
- [ ] Piper TTS response pipeline (text → audio → Pi → speaker)
- [ ] Context injection: feed vision + sensor state into LLM
- [ ] Cat noise detection and intervention behavior

### Phase 4 — Trash Collection
- [ ] Train or fine-tune trash detection model
- [ ] Navigation toward detected trash
- [ ] Pickup mechanism (scoop, arm, or gripper — TBD)
- [ ] "Patrol and collect" behavior loop

### Phase 5 — Advanced
- [ ] ROS 2 Jazzy integration on Pi
- [ ] Dynamic tail with servo + water ballast for balance
- [ ] Extendable legs for height adjustment
- [ ] Expressive OLED "eyes" for personality
- [ ] Outdoor operation (weatherproofing, solar charging)

## Development Environment

- **Desktop OS**: Windows 11 with WSL2
- **IDE**: Cursor
- **Arduino IDE / PlatformIO**: For firmware
- **Python 3.11+**: Pi application and GPU server
- **3D Printer**: Bambu Lab A1 Mini
- **CAD**: Onshape (free) or FreeCAD
- **Source Control**: Git + Azure DevOps (or GitHub)
- **LLM**: Ollama locally on desktop

## Quick Start

```bash
# SSH into the robot
ssh austin@pi5.local

# Or use Raspberry Pi Connect at:
# https://connect.raspberrypi.com

# Clone the repo on the Pi
git clone <repo-url> ~/wall-a
cd ~/wall-a

# Arduino firmware — flash via Arduino IDE or PlatformIO
# Pi application — see /pi/README.md
# GPU server — see /server/README.md
```

## Attribution

- Tank chassis design: [Thingiverse thing:2753227](https://www.thingiverse.com/thing:2753227) — 3D printable tracked robot for prototyping
- Tamiya 70097 Twin-Motor Gearbox Kit
- Inspired by Wall-E (Pixar, 2008)