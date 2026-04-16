"""Camera capture for the Pi Camera Module 3 via libcamera (Picamera2)."""

import logging

from picamera2 import Picamera2

log = logging.getLogger(__name__)


class Camera:
    def __init__(self, device: int = 0, width: int = 320, height: int = 240):
        self.device = device
        self.width = width
        self.height = height
        self._cam: Picamera2 | None = None

    def open(self):
        log.info("Opening Pi Camera %d (%dx%d)", self.device, self.width, self.height)
        self._cam = Picamera2(self.device)
        # Picamera2's "RGB888" format produces byte-order BGR arrays — cv2-compatible.
        config = self._cam.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self._cam.configure(config)
        self._cam.start()

    def read_frame(self):
        """Read a single frame. Returns (success, BGR ndarray)."""
        if not self._cam:
            return False, None
        try:
            return True, self._cam.capture_array("main")
        except Exception:
            log.exception("capture_array failed")
            return False, None

    def close(self):
        if self._cam:
            self._cam.stop()
            self._cam.close()
            self._cam = None
