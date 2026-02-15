"""Abstract base class for LMS platform adapters."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod


class PlatformAdapter(ABC):
    """Adapter interface for extracting course info from a specific LMS platform.

    Each adapter knows how to:
    - Recognise URLs belonging to its platform
    - Extract course IDs from download/page URLs
    - Discover course names from Chrome page titles
    - Correlate downloads with recently visited course pages
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable platform name, e.g. 'Canvas', 'Moodle'."""

    @property
    @abstractmethod
    def url_fingerprints(self) -> list[str]:
        """URL substrings that uniquely identify this platform.

        Used by the detector to auto-match domains.  Each string is checked
        against download URLs with a simple ``in`` test.
        """

    @abstractmethod
    def matches_url(self, url: str, domain: str) -> bool:
        """Return True if *url* belongs to this platform on *domain*."""

    @abstractmethod
    def extract_course_id(self, url: str) -> str | None:
        """Extract a course identifier from a download or page URL.

        Returns None if the URL does not contain a recognisable course ID.
        """

    @abstractmethod
    def discover_course_name(
        self, cursor: sqlite3.Cursor, course_id: str, domain: str
    ) -> str:
        """Try to find the course name from Chrome's page title history.

        Returns an empty string if no name could be discovered.
        """

    @abstractmethod
    def infer_course_from_visits(
        self, cursor: sqlite3.Cursor, download_time: int, domain: str
    ) -> str | None:
        """Fallback: find the most recently visited course page before *download_time*.

        Returns a course ID string, or None.
        """
