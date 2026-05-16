import logging

from aiohttp import web

from webrtc_template.config import config
from webrtc_template.signaling.server import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    web.run_app(create_app(), host=config.host, port=config.port)


if __name__ == "__main__":
    main()