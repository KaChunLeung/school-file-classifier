"""Generic fallback adapter for unknown LMS platforms.

Uses heuristic URL parsing and optional LLM assistance to identify
course structure from download URLs.  Designed as a one-time setup
helper — detected patterns are saved to config for deterministic reuse.
"""

from __future__ import annotations

import re
import sqlite3

from .base import PlatformAdapter

# Common path segments that often precede a course identifier.
_HEURISTIC_PATTERNS = [
    re.compile(r"/courses?/([A-Za-z0-9_-]+)"),
    re.compile(r"/class(?:es)?/([A-Za-z0-9_-]+)"),
    re.compile(r"/sections?/([A-Za-z0-9_-]+)"),
    re.compile(r"[?&]course_?id=([A-Za-z0-9_-]+)"),
]


class GenericAdapter(PlatformAdapter):
    """Best-effort adapter for platforms without a dedicated adapter.

    Tries common URL patterns heuristically.  For truly unknown platforms
    the UI should offer LLM-assisted pattern detection (one-time setup).
    """

    @property
    def name(self) -> str:
        return "Generic"

    @property
    def url_fingerprints(self) -> list[str]:
        # The generic adapter never auto-matches during detection.
        return []

    def matches_url(self, url: str, domain: str) -> bool:
        return domain in url

    def extract_course_id(self, url: str) -> str | None:
        for pattern in _HEURISTIC_PATTERNS:
            m = pattern.search(url)
            if m:
                return m.group(1)
        return None

    def discover_course_name(
        self, cursor: sqlite3.Cursor, course_id: str, domain: str
    ) -> str:
        # Generic: just look for any page title containing the course ID.
        cursor.execute(
            """
            SELECT title
            FROM urls
            WHERE url LIKE ?
              AND title != ''
            ORDER BY last_visit_time DESC
            LIMIT 5
            """,
            (f"%{domain}%{course_id}%",),
        )
        for (title,) in cursor.fetchall():
            cleaned = title.strip()
            if cleaned and len(cleaned) < 120:
                return cleaned
        return ""

    def infer_course_from_visits(
        self, cursor: sqlite3.Cursor, download_time: int, domain: str
    ) -> str | None:
        # Try to find any recent page visit on this domain with a course-like URL.
        cursor.execute(
            """
            SELECT u.url
            FROM visits v
            JOIN urls u ON v.url = u.id
            WHERE u.url LIKE ?
              AND v.visit_time <= ?
            ORDER BY v.visit_time DESC
            LIMIT 5
            """,
            (f"%{domain}%", download_time),
        )
        for (url,) in cursor.fetchall():
            cid = self.extract_course_id(url)
            if cid:
                return cid
        return None
