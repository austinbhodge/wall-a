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

    def connect(self) -> bool:
        log.info("Connecting to Arduino on %s @ %d baud", self.port, self.baud)
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=1)
            self._ser.reset_input_buffer()
            return True
        except (serial.SerialException, OSError) as e:
            log.warning("Arduino unavailable on %s: %s", self.port, e)
            self._ser = None
            return False

    @property
    def connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def try_reconnect(self) -> bool:
        """Attempt to (re)connect. Returns True only if newly connected."""
        if self.connected:
            return False
        return self.connect()

    def _drop(self):
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass
        self._ser = None

    def close(self):
        self._drop()

    def read_sensors(self) -> dict | None:
        """Read one JSON line from Arduino."""
        if not self._ser:
            return None
        try:
            line = self._ser.readline().decode("utf-8", errors="replace").strip()
        except (serial.SerialException, OSError) as e:
            log.warning("Arduino disconnected during read: %s", e)
            self._drop()
            return None
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
        try:
            self._ser.write(msg.encode("utf-8"))
        except (serial.SerialException, OSError) as e:
            log.warning("Arduino disconnected during write: %s", e)
            self._drop()

    def set_motors(self, left: int, right: int):
        """Convenience: send motor command."""
        self.send_command({"type": "motor", "left": left, "right": right})
