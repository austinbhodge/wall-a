"""Background worker threads for sensor reading and camera capture."""

import logging
import threading
import time

from walla.camera.capture import Camera
from walla.serial_bridge.bridge import SerialBridge
from walla.state import RobotState

log = logging.getLogger(__name__)


def sensor_loop(
    bridge: SerialBridge,
    state: RobotState,
    stop: threading.Event,
):
    """Continuously read sensor data from Arduino (~10Hz)."""
    log.info("Sensor thread started")
    while not stop.is_set():
        if not bridge.connected:
            # Avoid spinning when the Arduino is unplugged; main loop handles reconnect.
            time.sleep(0.1)
            continue
        try:
            data = bridge.read_sensors()
            if data and data.get("type") == "sensors":
                state.update_sensors(data)
            elif data and data.get("type") == "status":
                log.info("Arduino: %s", data.get("message", ""))
        except Exception:
            log.exception("Error reading sensors")
            time.sleep(0.5)
    log.info("Sensor thread stopped")


def camera_loop(
    camera: Camera,
    state: RobotState,
    stop: threading.Event,
):
    """Continuously capture frames from camera."""
    log.info("Camera thread started")
    while not stop.is_set():
        try:
            ok, frame = camera.read_frame()
            if ok:
                state.update_frame(frame)
            else:
                time.sleep(0.1)
        except Exception:
            log.exception("Error reading camera")
            time.sleep(0.5)
    log.info("Camera thread stopped")
