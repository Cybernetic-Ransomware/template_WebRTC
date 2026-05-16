import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    stun_url: str = field(default_factory=lambda: os.getenv("STUN_URL", "stun:stun.l.google.com:19302"))
    turn_url: str = field(default_factory=lambda: os.getenv("TURN_URL", "turn:coturn:3478"))
    turn_username: str = field(default_factory=lambda: os.getenv("TURN_USERNAME", "webrtc"))
    turn_password: str = field(default_factory=lambda: os.getenv("TURN_PASSWORD", "webrtc_secret"))
    # comma-separated list of allowed origins; "*" disables the whitelist (dev only)
    cors_origins: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))

    @property
    def ice_servers(self) -> list[dict]:
        return [
            {"urls": self.stun_url},
            {
                "urls": self.turn_url,
                "username": self.turn_username,
                "credential": self.turn_password,
            },
        ]


config = Config()