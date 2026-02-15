"""Scan Chrome download history and classify files by course using platform adapters."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from platforms import ALL_ADAPTERS, get_adapter
from platforms.base import PlatformAdapter
from platforms.generic import GenericAdapter


@dataclass
class ClassifiedFile:
    path: Path
    course_id: str
    course_name: str
    download_url: str
    platform: str = ""       # adapter name, e.g. "Canvas"
    sub_type: str = "Other"  # Lectures, Tutorials, Assignments, Other


@dataclass
class NewCourse:
    """A newly discovered course not yet in config."""
    course_id: str
    suggested_name: str


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


def _resolve_adapter(
    url: str, platform_configs: list[dict]
) -> tuple[PlatformAdapter, str] | None:
    """Find the adapter + domain that matches a URL.

    Checks configured platforms first, then falls back to the generic adapter.
    """
    for pcfg in platform_configs:
        domain = pcfg["domain"]
        if domain not in url:
            continue
        adapter = get_adapter(pcfg["type"])
        if adapter and adapter.matches_url(url, domain):
            return adapter, domain

    # Fallback: try to extract domain from URL and use generic adapter
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
    except Exception:
        return None

    if not domain:
        return None

    # Check if any configured platform domain is in this URL's domain
    for pcfg in platform_configs:
        if pcfg["domain"] in domain or domain in pcfg["domain"]:
            adapter = get_adapter(pcfg["type"])
            if adapter:
                return adapter, pcfg["domain"]

    return None


def scan_downloads(config: dict) -> tuple[list[ClassifiedFile], list[NewCourse]]:
    """Scan Chrome history for LMS downloads still in the Downloads folder.

    Returns (classified_files, new_courses) where new_courses contains
    any course IDs found in downloads that aren't in the config yet.
    """
    chrome_db = _get_chrome_history_db()
    if not chrome_db.exists():
        return [], []

    download_dir = Path(config["download_dir"])
    platform_configs = config.get("platforms", [])

    if not platform_configs:
        return [], []

    # Copy DB to temp file to avoid Chrome's lock
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    tmp_path = Path(tmp.name)
    try:
        shutil.copy2(chrome_db, tmp_path)
        results, new_courses = _query_downloads(
            tmp_path, download_dir, platform_configs, config
        )
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
    db_path: Path,
    download_dir: Path,
    platform_configs: list[dict],
    config: dict,
) -> tuple[list[ClassifiedFile], list[NewCourse]]:
    """Query the copied Chrome history DB for matching downloads."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()

        # Build a SQL filter for all configured platform domains
        domain_filters = []
        params: list[str] = []
        for pcfg in platform_configs:
            domain_filters.append("tab_url LIKE ? OR referrer LIKE ?")
            like = f"%{pcfg['domain']}%"
            params.extend([like, like])

        where_clause = " OR ".join(f"({f})" for f in domain_filters)
        cursor.execute(
            f"""
            SELECT tab_url, target_path, referrer, start_time
            FROM downloads
            WHERE {where_clause}
            ORDER BY start_time DESC
            """,
            params,
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

            # Deduplicate
            path_key = str(file_path).lower()
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)

            # Find matching adapter
            resolved = _resolve_adapter(tab_url, platform_configs)
            if not resolved:
                resolved = _resolve_adapter(referrer or "", platform_configs)
            if not resolved:
                continue

            adapter, domain = resolved

            # Extract course ID — try tab_url first, then referrer
            course_id = adapter.extract_course_id(tab_url) or adapter.extract_course_id(
                referrer or ""
            )

            # Fallback: correlate with recently visited course pages
            if not course_id:
                course_id = adapter.infer_course_from_visits(
                    cursor, start_time, domain
                )

            if course_id and course_id in config["courses"]:
                course_name = config["courses"][course_id]
            elif course_id:
                # Unknown course — try to discover its name
                if course_id not in discovered:
                    name = adapter.discover_course_name(cursor, course_id, domain)
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
                    platform=adapter.name,
                )
            )

        new_courses = [
            NewCourse(course_id=cid, suggested_name=name)
            for cid, name in discovered.items()
        ]
        return results, new_courses
    finally:
        conn.close()
