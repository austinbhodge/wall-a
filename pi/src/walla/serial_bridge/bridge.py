"""Serial bridge to Arduino — JSON messages over USB."""

import json
import logging

import serial

log = logging.getLogger(__name__)

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD = 115200


class SerialBridge:
    def __init__(self, port: str = DEFAULT_PORT, baud: int = DEFAULT_BAUD):
        self.port = port
        self.baud = baud
        self._ser: serial.Serial | None = None

    def connect(self):
        log.info("Connecting to Arduino on %s @ %d baud", self.port, self.baud)
        self._ser = serial.Serial(self.port, self.baud, timeout=1)
        self._ser.reset_input_buffer()

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()

    def read_sensors(self) -> dict | None:
        """Read one JSON line from Arduino."""
        if not self._ser:
            return None
        line = self._ser.readline().decode("utf-8", errors="replace").strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            log.warning("Bad JSON from Arduino: %s", line)
            return None

    def send_command(self, command: dict):
        """Send a JSON command to Arduino."""
        if not self._ser:
            return
        msg = json.dumps(command) + "\n"
        self._ser.write(msg.encode("utf-8"))

    def set_motors(self, left: int, right: int):
        """Convenience: send motor command."""
        self.send_command({"type": "motor", "left": left, "right": right})
