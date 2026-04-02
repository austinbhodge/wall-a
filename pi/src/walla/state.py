"""Thread-safe shared robot state."""

import dataclasses
import threading

import numpy as np


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

    # Control mode
    mode: str = "MANUAL"

    # Connection status
    arduino_connected: bool = False
    camera_active: bool = False
    controller_connected: bool = False

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
        with self._lock:
            self.mode = "AUTO" if self.mode == "MANUAL" else "MANUAL"
            return self.mode

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
            }
