"""DualSense (PS5) controller input via evdev (works headless)."""

import logging
import selectors
import threading

import evdev
from evdev import ecodes

log = logging.getLogger(__name__)

# DualSense evdev button codes
BTN_CROSS = ecodes.BTN_SOUTH      # 304
BTN_CIRCLE = ecodes.BTN_EAST      # 305
BTN_SQUARE = ecodes.BTN_WEST      # 308
BTN_TRIANGLE = ecodes.BTN_NORTH   # 307
BTN_L1 = ecodes.BTN_TL            # 310
BTN_R1 = ecodes.BTN_TR            # 311
BTN_SHARE = ecodes.BTN_SELECT     # 314
BTN_OPTIONS = ecodes.BTN_START    # 315
BTN_PS = ecodes.BTN_MODE          # 316
BTN_L3 = ecodes.BTN_THUMBL        # 317
BTN_R3 = ecodes.BTN_THUMBR        # 318

# Export friendly names for main.py
BUTTON_CROSS = BTN_CROSS
BUTTON_CIRCLE = BTN_CIRCLE
BUTTON_SQUARE = BTN_SQUARE
BUTTON_TRIANGLE = BTN_TRIANGLE
BUTTON_PS = BTN_PS

# DualSense axes (evdev ABS codes) — range 0-255, center 128
ABS_LEFT_X = ecodes.ABS_X         # 0
ABS_LEFT_Y = ecodes.ABS_Y         # 1
ABS_L2 = ecodes.ABS_Z             # 2 — L2 trigger (0=released, 255=full)
ABS_RIGHT_X = ecodes.ABS_RX       # 3
ABS_RIGHT_Y = ecodes.ABS_RY       # 4
ABS_R2 = ecodes.ABS_RZ            # 5 — R2 trigger (0=released, 255=full)
ABS_DPAD_X = ecodes.ABS_HAT0X     # 16
ABS_DPAD_Y = ecodes.ABS_HAT0Y     # 17

# Trigger axes don't center at 128 — they go 0 (released) to 255 (pressed)
_TRIGGER_AXES = {ABS_L2, ABS_R2}


def _find_dualsense() -> str | None:
    """Find DualSense controller event device path."""
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if "DualSense" in dev.name and "Touchpad" not in dev.name and "Motion" not in dev.name:
            return path
    return None


class Gamepad:
    """DualSense controller wrapper using evdev (headless-compatible)."""

    def __init__(self, deadzone: float = 0.1):
        self._dev: evdev.InputDevice | None = None
        self._deadzone = deadzone
        self._axes: dict[int, float] = {}  # normalized -1.0 to 1.0
        self._buttons_down: set[int] = set()
        self._buttons_pressed: set[int] = set()  # newly pressed this frame

    def init(self) -> bool:
        path = _find_dualsense()
        if not path:
            log.warning("No DualSense controller found")
            return False
        self._dev = evdev.InputDevice(path)
        log.info("Controller connected: %s at %s", self._dev.name, self._dev.path)
        # Read initial axis values
        caps = self._dev.capabilities()
        if ecodes.EV_ABS in caps:
            for code, absinfo in caps[ecodes.EV_ABS]:
                self._axes[code] = self._normalize_axis(code, absinfo.value)
        return True

    @property
    def connected(self) -> bool:
        return self._dev is not None

    def _normalize_axis(self, code: int, raw: int) -> float:
        """Convert 0-255 range to -1.0..1.0, or -1/0/1 for d-pad."""
        if code in (ABS_DPAD_X, ABS_DPAD_Y):
            return float(raw)  # already -1, 0, 1
        if code in _TRIGGER_AXES:
            # Triggers: 0 (released) to 255 (full press) -> 0.0 to 1.0
            return raw / 255.0
        # Sticks: 0-255 range, center 128
        val = (raw - 128) / 128.0
        if abs(val) < self._deadzone:
            return 0.0
        return max(-1.0, min(1.0, val))

    def update(self):
        """Read all pending events from the device. Call each frame."""
        if not self._dev:
            return
        self._buttons_pressed.clear()
        try:
            while True:
                event = self._dev.read_one()
                if event is None:
                    break
                if event.type == ecodes.EV_ABS:
                    self._axes[event.code] = self._normalize_axis(event.code, event.value)
                elif event.type == ecodes.EV_KEY:
                    if event.value == 1:  # press
                        self._buttons_down.add(event.code)
                        self._buttons_pressed.add(event.code)
                    elif event.value == 0:  # release
                        self._buttons_down.discard(event.code)
        except (OSError, IOError):
            log.warning("Controller disconnected!")
            self._dev = None
            self._axes.clear()
            self._buttons_down.clear()

    def axis(self, code: int) -> float:
        return self._axes.get(code, 0.0)

    def button_pressed(self, btn: int) -> bool:
        """True only on the frame the button was first pressed."""
        return btn in self._buttons_pressed

    def button_held(self, btn: int) -> bool:
        return btn in self._buttons_down

    def get_tank_drive(self) -> tuple[int, int]:
        """Arcade drive: left stick Y = throttle, X = turn.

        Returns (left_speed, right_speed) in -255..255.
        """
        if not self.connected:
            return 0, 0

        throttle = -self.axis(ABS_LEFT_Y)  # negate: stick up = negative
        turn = self.axis(ABS_LEFT_X)

        left = throttle + turn
        right = throttle - turn

        max_val = max(abs(left), abs(right), 1.0)
        left = int((left / max_val) * 255)
        right = int((right / max_val) * 255)
        return left, right

    def close(self):
        if self._dev:
            self._dev.close()
            self._dev = None
