"""Camera capture and streaming to GPU server."""

import logging

import cv2

log = logging.getLogger(__name__)


class Camera:
    def __init__(self, device: int = 0, width: int = 1280, height: int = 720):
        self.device = device
        self.width = width
        self.height = height
        self._cap: cv2.VideoCapture | None = None

    def open(self):
        log.info("Opening camera device %d", self.device)
        self._cap = cv2.VideoCapture(self.device)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def read_frame():
        """Read a single frame. Returns (success, frame)."""
        if not self._cap:
            return False, None
        return self._cap.read()

    def close(self):
        if self._cap:
            self._cap.release()
