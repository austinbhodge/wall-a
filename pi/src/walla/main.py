"""Wall-A Pi application entry point."""

import logging

from walla.serial_bridge.bridge import SerialBridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("walla")


def main():
    log.info("Wall-A starting up...")

    bridge = SerialBridge()
    bridge.connect()

    try:
        while True:
            data = bridge.read_sensors()
            if data:
                log.debug("Sensors: %s", data)
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
