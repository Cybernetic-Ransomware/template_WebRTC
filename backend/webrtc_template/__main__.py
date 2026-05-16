import logging

import structlog
from aiohttp import web

from webrtc_template.config import config
from webrtc_template.signaling.server import create_app

logging.basicConfig(level=logging.INFO, format="%(message)s")

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)


def main() -> None:
    web.run_app(create_app(), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
