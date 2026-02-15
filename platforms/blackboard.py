"""Blackboard Learn LMS platform adapter."""

from __future__ import annotations

import re
import sqlite3

from .base import PlatformAdapter

# Blackboard course IDs look like _123_1 in both Classic and Ultra.
_COURSE_RE = re.compile(r"(?:/courses/|course_id=)(_\d+_\d+)")
_ULTRA_RE = re.compile(r"/ultra/courses/(_\d+_\d+)")


class BlackboardAdapter(PlatformAdapter):
    """Adapter for Blackboard Learn (Classic and Ultra)."""

    @property
    def name(self) -> str:
        return "Blackboard"

    @property
    def url_fingerprints(self) -> list[str]:
        return ["/bbcswebdav/", "/webapps/blackboard/", "/ultra/courses/"]

    def matches_url(self, url: str, domain: str) -> bool:
        return domain in url

    def extract_course_id(self, url: str) -> str | None:
        for regex in (_COURSE_RE, _ULTRA_RE):
            m = regex.search(url)
            if m:
                return m.group(1)
        return None

    def discover_course_name(
        self, cursor: sqlite3.Cursor, course_id: str, domain: str
    ) -> str:
        # Blackboard page titles vary by institution, so we cast a wide net.
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
            # Remove common Blackboard suffixes
            cleaned = re.sub(
                r"\s*[-–—:]\s*(Content|Announcements|Grades|Course Materials)\s*$",
                "", cleaned
            ).strip()
            if cleaned and cleaned.lower() not in ("", "blackboard", "loading", "blackboard learn"):
                return cleaned
        return ""

    def infer_course_from_visits(
        self, cursor: sqlite3.Cursor, download_time: int, domain: str
    ) -> str | None:
        # Look for recent visits to Blackboard course pages.
        cursor.execute(
            """
            SELECT u.url
            FROM visits v
            JOIN urls u ON v.url = u.id
            WHERE (u.url LIKE ? OR u.url LIKE ?)
              AND v.visit_time <= ?
            ORDER BY v.visit_time DESC
            LIMIT 1
            """,
            (
                f"%{domain}%/ultra/courses/%",
                f"%{domain}%course_id=_%",
                download_time,
            ),
        )
        row = cursor.fetchone()
        if row:
            return self.extract_course_id(row[0])
        return None
