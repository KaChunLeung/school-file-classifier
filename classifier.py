"""Scan Chrome download history and classify files by Insendi course."""

import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClassifiedFile:
    path: Path
    course_id: str
    course_name: str
    download_url: str
    sub_type: str = "Other"  # Lectures, Tutorials, Assignments, Other


def _get_chrome_history_db() -> Path:
    """Return the path to Chrome's History SQLite database."""
    return (
        Path.home()
        / "AppData"
        / "Local"
        / "Google"
        / "Chrome"
        / "User Data"
        / "Default"
        / "History"
    )


def _extract_course_id(url: str) -> str | None:
    """Extract the course ID from an Insendi URL.

    Handles the pattern: /programmes/{pid}/courses/{courseId}/...
    Returns None for API-style URLs (/api/v1/imp/files/...).
    """
    match = re.search(r"/courses/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def _infer_course_from_visits(
    cursor: sqlite3.Cursor, download_time: int, domain: str
) -> str | None:
    """For API-style downloads with no course ID in the URL, find the most
    recently visited course page before the download happened."""
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
        return _extract_course_id(row[0])
    return None


def _discover_course_name(
    cursor: sqlite3.Cursor, course_id: str, domain: str
) -> str:
    """Try to discover a course name from Chrome's page titles.

    Insendi page titles follow patterns like:
      "Course Name - Files", "Course Name - Newsfeed", etc.
    """
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
    rows = cursor.fetchall()
    for (title,) in rows:
        # Strip common Insendi suffixes: " - Files", " - Newsfeed", etc.
        cleaned = re.sub(r"\s*[-–—]\s*(Files|Newsfeed|Weeks|Grades|People|Settings)\s*$", "", title).strip()
        if cleaned and cleaned.lower() not in ("", "insendi", "loading"):
            return cleaned
    return ""


@dataclass
class NewCourse:
    """A newly discovered course not yet in config."""
    course_id: str
    suggested_name: str


def scan_downloads(config: dict) -> tuple[list[ClassifiedFile], list[NewCourse]]:
    """Scan Chrome history for Insendi downloads still in the Downloads folder.

    Returns (classified_files, new_courses) where new_courses contains
    any course IDs found in downloads that aren't in the config yet.
    """
    chrome_db = _get_chrome_history_db()
    if not chrome_db.exists():
        return [], []

    download_dir = Path(config["download_dir"])
    domain = config["school_domain"]

    # Copy DB to temp file to avoid Chrome's lock
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    tmp_path = Path(tmp.name)
    try:
        shutil.copy2(chrome_db, tmp_path)
        results, new_courses = _query_downloads(tmp_path, download_dir, domain, config)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Sub-classify files using LLM
    api_key = config.get("groq_api_key", "")
    if results and api_key:
        from llm import classify_batch

        filenames = [cf.path.name for cf in results]
        categories = classify_batch(filenames, api_key)
        for cf, cat in zip(results, categories):
            cf.sub_type = cat

    return results, new_courses


def _query_downloads(
    db_path: Path, download_dir: Path, domain: str, config: dict
) -> tuple[list[ClassifiedFile], list[NewCourse]]:
    """Query the copied Chrome history DB for matching downloads."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tab_url, target_path, referrer, start_time
            FROM downloads
            WHERE (tab_url LIKE ? OR referrer LIKE ?)
            ORDER BY start_time DESC
            """,
            (f"%{domain}%", f"%{domain}%"),
        )

        seen_paths: set[str] = set()
        results: list[ClassifiedFile] = []
        discovered: dict[str, str] = {}  # course_id -> suggested_name

        for tab_url, target_path, referrer, start_time in cursor.fetchall():
            file_path = Path(target_path)

            # Only include files still sitting in the Downloads folder
            if not file_path.exists():
                continue
            try:
                if file_path.parent.resolve() != download_dir.resolve():
                    continue
            except (OSError, ValueError):
                continue

            # Deduplicate (Chrome can log the same file multiple times)
            path_key = str(file_path).lower()
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)

            # Extract course ID — try tab_url first, then referrer
            course_id = _extract_course_id(tab_url) or _extract_course_id(
                referrer or ""
            )

            # Fallback: for API-style downloads, correlate with the most
            # recently visited course page before the download time
            if not course_id:
                course_id = _infer_course_from_visits(
                    cursor, start_time, domain
                )

            if course_id and course_id in config["courses"]:
                course_name = config["courses"][course_id]
            elif course_id:
                # Unknown course — try to discover its name
                if course_id not in discovered:
                    name = _discover_course_name(cursor, course_id, domain)
                    discovered[course_id] = name if name else f"New Course ({course_id[:8]})"
                course_name = discovered[course_id]
            else:
                course_name = "Unknown Course"

            results.append(
                ClassifiedFile(
                    path=file_path,
                    course_id=course_id or "unknown",
                    course_name=course_name,
                    download_url=tab_url,
                )
            )

        new_courses = [
            NewCourse(course_id=cid, suggested_name=name)
            for cid, name in discovered.items()
        ]
        return results, new_courses
    finally:
        conn.close()
