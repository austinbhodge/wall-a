"""Wall-A GPU server entry point."""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("walla-server")


def main():
    log.info("Wall-A server starting up...")
    # TODO: Start vision pipeline, STT, TTS, LLM services
    # TODO: Listen for incoming video stream from Pi
    # TODO: Assemble context and feed to LLM


if __name__ == "__main__":
    main()
