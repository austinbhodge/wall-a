"""Camera capture and streaming to GPU server."""

import logging

import cv2

log = logging.getLogger(__name__)


class Camera:
    def __init__(self, device: int = 0, width: int = 320, height: int = 240):
        self.device = device
        self.width = width
        self.height = height
        self._cap: cv2.VideoCapture | None = None

    def open(self):
        log.info("Opening camera device %d (%dx%d)", self.device, self.width, self.height)
        self._cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not self._cap.isOpened():
            log.error("Failed to open camera device %d", self.device)

    def read_frame(self):
        """Read a single frame. Returns (success, frame)."""
        if not self._cap:
            return False, None
        return self._cap.read()

    def close(self):
        if self._cap:
            self._cap.release()
