from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IncomingMessage:
    text: str
    user_id: str
    username: Optional[str] = None


@dataclass(frozen=True)
class OutgoingMessage:
    text: str
