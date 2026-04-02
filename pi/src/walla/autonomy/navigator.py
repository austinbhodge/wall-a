"""Obstacle avoidance using HSV floor color segmentation."""

import logging
import time

import cv2
import numpy as np

log = logging.getLogger(__name__)

# Navigation states
PATROL = "PATROL"
TURN_LEFT = "TURN_LEFT"
TURN_RIGHT = "TURN_RIGHT"
REVERSE = "REVERSE"

# Speeds
PATROL_SPEED = 120
TURN_SPEED = 140
REVERSE_SPEED = -100

# Thresholds
FLOOR_RATIO_OK = 0.35  # zone must be >35% floor to be considered clear
ALL_BLOCKED_RATIO = 0.15  # if all zones below this, reverse


class Navigator:
    """Webcam-based obstacle avoidance using floor color detection.

    On calibration, samples the bottom-center of the frame to learn
    what "floor" looks like in HSV. Then steers to stay on the floor.
    """

    def __init__(self):
        self.state = PATROL
        self._state_start = 0.0
        self._turn_duration = 0.0
        self._reverse_duration = 0.5
        self._calibrated = False
        self._floor_low = None
        self._floor_high = None

    def calibrate(self, frame: np.ndarray):
        """Sample bottom-center patch to learn floor color."""
        h, w = frame.shape[:2]
        # 50x50 patch from bottom center
        patch = frame[h - 60 : h - 10, w // 2 - 25 : w // 2 + 25]
        hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)

        mean = np.mean(hsv_patch.reshape(-1, 3), axis=0)
        std = np.std(hsv_patch.reshape(-1, 3), axis=0)

        # Floor range: mean +/- 2 sigma, clamped to valid HSV ranges
        self._floor_low = np.clip(mean - 2 * std, [0, 0, 0], [179, 255, 255]).astype(
            np.uint8
        )
        self._floor_high = np.clip(mean + 2 * std, [0, 0, 0], [179, 255, 255]).astype(
            np.uint8
        )
        self._calibrated = True
        log.info(
            "Floor calibrated — HSV low=%s high=%s",
            self._floor_low.tolist(),
            self._floor_high.tolist(),
        )

    def _analyze_frame(self, frame: np.ndarray) -> tuple[float, float, float]:
        """Returns (left_ratio, center_ratio, right_ratio) of floor pixels."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._floor_low, self._floor_high)

        h, w = mask.shape
        # Only look at bottom half
        bottom = mask[h // 2 :, :]
        bh, bw = bottom.shape
        third = bw // 3

        left_zone = bottom[:, :third]
        center_zone = bottom[:, third : 2 * third]
        right_zone = bottom[:, 2 * third :]

        def ratio(zone):
            return np.count_nonzero(zone) / zone.size if zone.size > 0 else 0.0

        return ratio(left_zone), ratio(center_zone), ratio(right_zone)

    def update(self, frame: np.ndarray | None, sensors: dict) -> tuple[int, int]:
        """Compute motor command based on vision + sensors.

        Returns (left_speed, right_speed) in -255..255.
        """
        now = time.monotonic()

        # Bump sensor override — highest priority
        bump_left = sensors.get("bump_front_left", False)
        bump_right = sensors.get("bump_front_right", False)
        if bump_left or bump_right:
            log.info("Bump detected! left=%s right=%s", bump_left, bump_right)
            self.state = REVERSE
            self._state_start = now
            self._reverse_duration = 0.6
            # Will turn away from bump side after reversing
            self._bump_turn = TURN_RIGHT if bump_left else TURN_LEFT
            return REVERSE_SPEED, REVERSE_SPEED

        # Handle timed states
        elapsed = now - self._state_start

        if self.state == REVERSE:
            if elapsed < self._reverse_duration:
                return REVERSE_SPEED, REVERSE_SPEED
            # Done reversing, turn
            turn_dir = getattr(self, "_bump_turn", TURN_LEFT)
            self.state = turn_dir
            self._state_start = now
            self._turn_duration = 0.6
            return self._turn_command(turn_dir)

        if self.state in (TURN_LEFT, TURN_RIGHT):
            if elapsed < self._turn_duration:
                return self._turn_command(self.state)
            self.state = PATROL
            self._state_start = now

        # Vision-based navigation
        if frame is None or not self._calibrated:
            # No frame — creep forward slowly
            return PATROL_SPEED // 2, PATROL_SPEED // 2

        left_r, center_r, right_r = self._analyze_frame(frame)

        # All blocked — reverse
        if (
            left_r < ALL_BLOCKED_RATIO
            and center_r < ALL_BLOCKED_RATIO
            and right_r < ALL_BLOCKED_RATIO
        ):
            log.info("All zones blocked (L=%.2f C=%.2f R=%.2f) — reversing",
                     left_r, center_r, right_r)
            self.state = REVERSE
            self._state_start = now
            self._reverse_duration = 0.5
            self._bump_turn = TURN_LEFT  # default
            return REVERSE_SPEED, REVERSE_SPEED

        # Center clear — drive forward
        if center_r >= FLOOR_RATIO_OK:
            return PATROL_SPEED, PATROL_SPEED

        # Center blocked — turn toward clearer side
        if left_r > right_r:
            log.debug("Center blocked, turning left (L=%.2f R=%.2f)", left_r, right_r)
            self.state = TURN_LEFT
            self._state_start = now
            self._turn_duration = 0.4
            return self._turn_command(TURN_LEFT)
        else:
            log.debug("Center blocked, turning right (L=%.2f R=%.2f)", left_r, right_r)
            self.state = TURN_RIGHT
            self._state_start = now
            self._turn_duration = 0.4
            return self._turn_command(TURN_RIGHT)

    @staticmethod
    def _turn_command(direction: str) -> tuple[int, int]:
        if direction == TURN_LEFT:
            return -TURN_SPEED, TURN_SPEED
        return TURN_SPEED, -TURN_SPEED
