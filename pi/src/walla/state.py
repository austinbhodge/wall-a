"""Thread-safe shared robot state."""

import dataclasses
import threading
import time

import numpy as np

VALID_MODES = ("MANUAL", "AUTO", "WEB")


@dataclasses.dataclass
class RobotState:
    # Sensor data from Arduino
    battery_voltage: float = 0.0
    bump_front_left: bool = False
    bump_front_right: bool = False
    motor_left: int = 0
    motor_right: int = 0

    # Latest camera frame
    frame: np.ndarray | None = dataclasses.field(default=None, repr=False)

    # Control mode: MANUAL | AUTO | WEB
    mode: str = "MANUAL"

    # Connection status
    arduino_connected: bool = False
    camera_active: bool = False
    controller_connected: bool = False

    # Web-driven motor intent (watchdog in main loop zeroes motors if stale)
    web_drive_left: int = 0
    web_drive_right: int = 0
    web_drive_timestamp: float = 0.0

    _lock: threading.Lock = dataclasses.field(
        default_factory=threading.Lock, repr=False
    )

    def update_sensors(self, data: dict):
        with self._lock:
            self.arduino_connected = True
            self.battery_voltage = data.get("battery_voltage", self.battery_voltage)
            motors = data.get("motors", {})
            self.motor_left = motors.get("left_speed", self.motor_left)
            self.motor_right = motors.get("right_speed", self.motor_right)
            bumps = data.get("bump_sensors", {})
            self.bump_front_left = bumps.get("front_left", self.bump_front_left)
            self.bump_front_right = bumps.get("front_right", self.bump_front_right)

    def update_frame(self, frame: np.ndarray):
        with self._lock:
            self.frame = frame
            self.camera_active = True

    def toggle_mode(self):
        """Cycle MANUAL ↔ AUTO for gamepad toggle; WEB is set only via API."""
        with self._lock:
            self.mode = "AUTO" if self.mode == "MANUAL" else "MANUAL"
            return self.mode

    def set_mode(self, mode: str) -> str:
        if mode not in VALID_MODES:
            raise ValueError(f"invalid mode: {mode}")
        with self._lock:
            self.mode = mode
            # Leaving WEB resets the web drive intent.
            if mode != "WEB":
                self.web_drive_left = 0
                self.web_drive_right = 0
            return self.mode

    def set_web_drive(self, left: int, right: int):
        left = max(-255, min(255, int(left)))
        right = max(-255, min(255, int(right)))
        with self._lock:
            self.web_drive_left = left
            self.web_drive_right = right
            self.web_drive_timestamp = time.monotonic()

    def snapshot(self) -> dict:
        """Return a copy of current state as a plain dict (no lock held)."""
        with self._lock:
            return {
                "mode": self.mode,
                "battery_voltage": self.battery_voltage,
                "bump_front_left": self.bump_front_left,
                "bump_front_right": self.bump_front_right,
                "motor_left": self.motor_left,
                "motor_right": self.motor_right,
                "frame": self.frame.copy() if self.frame is not None else None,
                "arduino_connected": self.arduino_connected,
                "camera_active": self.camera_active,
                "controller_connected": self.controller_connected,
                "web_drive_left": self.web_drive_left,
                "web_drive_right": self.web_drive_right,
                "web_drive_timestamp": self.web_drive_timestamp,
            }
