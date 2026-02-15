"""Insendi LMS platform adapter."""

from __future__ import annotations

import re
import sqlite3

from .base import PlatformAdapter

_COURSE_RE = re.compile(r"/courses/([A-Za-z0-9_-]+)")
_TITLE_SUFFIX_RE = re.compile(
    r"\s*[-–—]\s*(Files|Newsfeed|Weeks|Grades|People|Settings)\s*$"
)


class InsendiAdapter(PlatformAdapter):
    """Adapter for the Insendi LMS (used by Imperial College and others)."""

    @property
    def name(self) -> str:
        return "Insendi"

    @property
    def url_fingerprints(self) -> list[str]:
        return ["/api/v1/imp/", "insendi.com"]

    def matches_url(self, url: str, domain: str) -> bool:
        return domain in url

    def extract_course_id(self, url: str) -> str | None:
        m = _COURSE_RE.search(url)
        return m.group(1) if m else None

    def discover_course_name(
        self, cursor: sqlite3.Cursor, course_id: str, domain: str
    ) -> str:
        cursor.execute(
            """
            SELECT title
            FROM urls
            WHERE url LIKE ?
              AND title != ''
            ORDER BY last_visit_time DESC
            LIMIT 5
            """,
            (f"%{domain}%/courses/{course_id}%",),
        )
        for (title,) in cursor.fetchall():
            cleaned = _TITLE_SUFFIX_RE.sub("", title).strip()
            if cleaned and cleaned.lower() not in ("", "insendi", "loading"):
                return cleaned
        return ""

    def infer_course_from_visits(
        self, cursor: sqlite3.Cursor, download_time: int, domain: str
    ) -> str | None:
        cursor.execute(
            """
            SELECT u.url
            FROM visits v
            JOIN urls u ON v.url = u.id
            WHERE u.url LIKE ?
              AND v.visit_time <= ?
            ORDER BY v.visit_time DESC
            LIMIT 1
            """,
            (f"%{domain}%/courses/%", download_time),
        )
        row = cursor.fetchone()
        if row:
            return self.extract_course_id(row[0])
        return None
