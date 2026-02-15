"""Moodle LMS platform adapter."""

from __future__ import annotations

import re
import sqlite3

from .base import PlatformAdapter

# Moodle course IDs appear in page URLs, not in download URLs.
_COURSE_RE = re.compile(r"/course/view\.php\?id=(\d+)")
_MOD_RE = re.compile(r"/mod/\w+/view\.php\?id=(\d+)")
_TITLE_SUFFIX_RE = re.compile(
    r"\s*[-–—:]\s*(Moodle|Dashboard)\s*$", re.IGNORECASE
)
_TITLE_PREFIX_RE = re.compile(r"^Course:\s*", re.IGNORECASE)


class MoodleAdapter(PlatformAdapter):
    """Adapter for Moodle LMS.

    Moodle download URLs use ``/pluginfile.php/`` with context IDs that do not
    directly map to course IDs.  We rely heavily on the referrer URL and
    visit-time correlation to identify the course.
    """

    @property
    def name(self) -> str:
        return "Moodle"

    @property
    def url_fingerprints(self) -> list[str]:
        return ["/pluginfile.php/", "/mod/resource/view.php"]

    def matches_url(self, url: str, domain: str) -> bool:
        return domain in url

    def extract_course_id(self, url: str) -> str | None:
        # Try the direct course page URL first
        m = _COURSE_RE.search(url)
        if m:
            return m.group(1)
        # Moodle module URLs don't contain the course ID directly,
        # but we try anyway in case the referrer is a course page.
        return None

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
            (f"%{domain}%/course/view.php?id={course_id}%",),
        )
        for (title,) in cursor.fetchall():
            cleaned = _TITLE_SUFFIX_RE.sub("", title).strip()
            cleaned = _TITLE_PREFIX_RE.sub("", cleaned).strip()
            if cleaned and cleaned.lower() not in ("", "moodle", "loading", "dashboard"):
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
            (f"%{domain}%/course/view.php?id=%", download_time),
        )
        row = cursor.fetchone()
        if row:
            return self.extract_course_id(row[0])
        return None
