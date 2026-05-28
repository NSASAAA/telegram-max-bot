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


@dataclass(frozen=True)
class ImportStats:
    created: int
    updated: int
    unchanged: int

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged


@dataclass(frozen=True)
class Topic:
    code: str
    title: str
    description: str
    keywords: tuple[str, ...]
