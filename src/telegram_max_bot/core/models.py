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
    buttons: tuple["LinkButton", ...] = ()
    parse_mode: Optional[str] = None
    photo_path: Optional[str] = None
    cards: tuple["PreviewCard", ...] = ()


@dataclass(frozen=True)
class LinkButton:
    text: str
    url: str


@dataclass(frozen=True)
class PreviewCard:
    text: str
    buttons: tuple[LinkButton, ...] = ()
    parse_mode: Optional[str] = None
    photo_path: Optional[str] = None


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
