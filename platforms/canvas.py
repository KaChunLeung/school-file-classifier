"""Canvas (Instructure) LMS platform adapter."""

from __future__ import annotations

import re
import sqlite3

from .base import PlatformAdapter

_COURSE_RE = re.compile(r"/courses/(\d+)")
_TITLE_SUFFIX_RE = re.compile(
    r"\s*[:–—-]\s*(Files|Modules|Assignments|Grades|People|Pages|Syllabus|Discussions|Quizzes|Announcements|Settings)\s*$"
)


class CanvasAdapter(PlatformAdapter):
    """Adapter for Canvas by Instructure."""

    @property
    def name(self) -> str:
        return "Canvas"

    @property
    def url_fingerprints(self) -> list[str]:
        return [".instructure.com", "/download?download_frd="]

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
            if cleaned and cleaned.lower() not in ("", "canvas", "loading"):
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
