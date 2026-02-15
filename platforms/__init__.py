"""Platform adapter registry for LMS detection."""

from __future__ import annotations

from .base import PlatformAdapter
from .insendi import InsendiAdapter
from .canvas import CanvasAdapter
from .moodle import MoodleAdapter
from .blackboard import BlackboardAdapter

# Ordered list — checked in order during detection.
ALL_ADAPTERS: list[PlatformAdapter] = [
    CanvasAdapter(),
    MoodleAdapter(),
    BlackboardAdapter(),
    InsendiAdapter(),
]

ADAPTER_MAP: dict[str, PlatformAdapter] = {a.name.lower(): a for a in ALL_ADAPTERS}


def get_adapter(platform_type: str) -> PlatformAdapter | None:
    """Look up an adapter by its type string (e.g. 'canvas')."""
    return ADAPTER_MAP.get(platform_type.lower())


__all__ = [
    "PlatformAdapter",
    "ALL_ADAPTERS",
    "ADAPTER_MAP",
    "get_adapter",
    "InsendiAdapter",
    "CanvasAdapter",
    "MoodleAdapter",
    "BlackboardAdapter",
]
