"""Wall-A Pi application — main orchestrator.

Manages manual (PS controller) and autonomous (vision) driving modes.
"""

import logging
import threading
import time

from walla.autonomy.navigator import Navigator
from walla.camera.capture import Camera
from walla.controller.gamepad import (
    BUTTON_CIRCLE,
    BUTTON_PS,
    BUTTON_TRIANGLE,
    Gamepad,
)
from walla.serial_bridge.bridge import SerialBridge
from walla.state import RobotState
from walla.threads import camera_loop, sensor_loop
from walla.web import WebServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("walla")

TICK_RATE = 20  # Hz
TICK_INTERVAL = 1.0 / TICK_RATE

# If the web client hasn't sent a drive command within this window, cut motors.
WEB_DRIVE_TIMEOUT = 0.5


def main():
    log.info("=== Wall-A starting up ===")

    # Initialize subsystems
    state = RobotState()
    bridge = SerialBridge()
    camera = Camera(device=0, width=320, height=240)
    gamepad = Gamepad()
    navigator = Navigator()

    # Connect hardware — every device is optional; missing ones reconnect in the tick loop.
    log.info("Connecting to Arduino...")
    if bridge.connect():
        time.sleep(2)  # Arduino resets on serial connect
        log.info("Arduino connected")
    else:
        log.warning("Arduino not available — will retry in background")

    log.info("Opening camera...")
    if camera.open():
        log.info("Camera ready")
    else:
        log.warning("Camera not available — will retry in background")

    log.info("Initializing controller...")
    controller_ok = gamepad.init()
    state.controller_connected = controller_ok
    if not controller_ok:
        log.warning("No controller found — waiting for connection in MANUAL mode")

    # Start background threads
    stop = threading.Event()
    sensor_thread = threading.Thread(
        target=sensor_loop, args=(bridge, state, stop), daemon=True, name="sensors"
    )
    camera_thread = threading.Thread(
        target=camera_loop, args=(camera, state, stop), daemon=True, name="camera"
    )
    sensor_thread.start()
    camera_thread.start()

    # Web dashboard — attaches a ring-buffer log handler, then serves on :8080
    web = WebServer(state=state, bridge=bridge, navigator=navigator)
    web.start()

    # Wait for first sensor data (only if the Arduino is actually present)
    if bridge.connected:
        log.info("Waiting for sensor data...")
        for _ in range(20):
            if state.arduino_connected:
                break
            time.sleep(0.1)

    log.info("Wall-A is READY — mode: %s", state.mode)
    log.info("  PS button = toggle mode | Circle = emergency stop | Triangle = recalibrate floor")

    last_status_time = time.monotonic()
    last_reconnect_time = time.monotonic()

    try:
        while True:
            tick_start = time.monotonic()

            # Try reconnecting any missing hardware every 2 seconds.
            now = time.monotonic()
            if now - last_reconnect_time > 2.0:
                last_reconnect_time = now
                if gamepad.try_reconnect():
                    state.controller_connected = True
                    log.info("Controller connected!")
                if bridge.try_reconnect():
                    log.info("Arduino connected!")
                if camera.try_reconnect():
                    log.info("Camera connected!")

            gamepad.update()

            # Emergency stop — Circle button (highest priority)
            if gamepad.button_pressed(BUTTON_CIRCLE):
                bridge.set_motors(0, 0)
                log.warning("!! EMERGENCY STOP !!")
                time.sleep(TICK_INTERVAL)
                continue

            # Mode toggle — PS button
            if gamepad.button_pressed(BUTTON_PS):
                new_mode = state.toggle_mode()
                bridge.set_motors(0, 0)  # safety stop during transition
                log.info("Mode switched to: %s", new_mode)
                if new_mode == "AUTO":
                    snap = state.snapshot()
                    if snap["frame"] is not None:
                        navigator.calibrate(snap["frame"])
                        log.info("Floor calibrated for autonomous mode")
                    else:
                        log.warning("No camera frame for calibration!")

            # Manual floor recalibration — Triangle button
            if gamepad.button_pressed(BUTTON_TRIANGLE):
                snap = state.snapshot()
                if snap["frame"] is not None:
                    navigator.calibrate(snap["frame"])
                    log.info("Floor recalibrated manually")

            snap = state.snapshot()

            if snap["mode"] == "MANUAL":
                left, right = gamepad.get_tank_drive()
                if left != 0 or right != 0:
                    log.debug("Drive: L=%d R=%d", left, right)
                bridge.set_motors(left, right)

            elif snap["mode"] == "AUTO":
                left, right = navigator.update(
                    snap["frame"],
                    {
                        "bump_front_left": snap["bump_front_left"],
                        "bump_front_right": snap["bump_front_right"],
                    },
                )
                bridge.set_motors(left, right)

            elif snap["mode"] == "WEB":
                # Watchdog: if the browser has stopped sending drive updates,
                # treat it as a dead-man switch and cut power.
                ts = snap["web_drive_timestamp"]
                age = time.monotonic() - ts if ts > 0 else float("inf")
                if age > WEB_DRIVE_TIMEOUT:
                    bridge.set_motors(0, 0)
                else:
                    bridge.set_motors(snap["web_drive_left"], snap["web_drive_right"])

            # Periodic status log
            now = time.monotonic()
            if now - last_status_time > 10.0:
                left, right = gamepad.get_tank_drive()
                log.info(
                    "Status — mode=%s battery=%.1fV arduino=%s cam=%s ctrl=%s stick=(%d,%d)",
                    snap["mode"],
                    snap["battery_voltage"],
                    bridge.connected,
                    camera.connected,
                    gamepad.connected,
                    left,
                    right,
                )
                last_status_time = now

            # Rate limit
            elapsed = time.monotonic() - tick_start
            sleep_time = TICK_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        # Stop motors first!
        bridge.set_motors(0, 0)
        stop.set()
        web.stop()
        gamepad.close()
        camera.close()
        bridge.close()
        log.info("=== Wall-A shut down ===")


if __name__ == "__main__":
    main()
