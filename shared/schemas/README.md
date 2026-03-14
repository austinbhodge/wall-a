# Shared Schemas

Protocol definitions and message schemas shared between Wall-A's components.

## Serial Protocol (`serial_protocol.json`)

JSON messages sent between the Raspberry Pi and Arduino over USB serial at 115200 baud. Each message is a single JSON object terminated by a newline.

**Direction: Pi → Arduino**
- `motor` — Set left/right motor speeds (-255 to 255)

**Direction: Arduino → Pi**
- `sensors` — Periodic sensor readings (motors, battery, bump sensors)
- `status` — Status/lifecycle messages
