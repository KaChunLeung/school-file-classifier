"""Auto-detect LMS platforms from Chrome download history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from urllib.parse import urlparse

from .base import PlatformAdapter
from . import ALL_ADAPTERS


@dataclass
class DetectedPlatform:
    """A platform detected in Chrome's download history."""
    domain: str
    platform_type: str  # lowercase adapter name, e.g. "canvas"
    adapter: PlatformAdapter
    download_count: int


class PlatformDetector:
    """Scan Chrome history to identify which LMS platforms are present."""

    def __init__(self, adapters: list[PlatformAdapter] | None = None):
        self._adapters = adapters or ALL_ADAPTERS

    def detect_from_history(
        self, cursor: sqlite3.Cursor
    ) -> list[DetectedPlatform]:
        """Scan the downloads table for known LMS URL fingerprints.

        Returns a list of detected platforms with their domains and adapters.
        """
        # Get all unique download domains with counts
        cursor.execute(
            """
            SELECT tab_url, referrer
            FROM downloads
            WHERE tab_url != '' OR referrer != ''
            """
        )

        # Collect domain -> set of URLs for fingerprint matching
        domain_urls: dict[str, set[str]] = {}
        domain_counts: dict[str, int] = {}
        for tab_url, referrer in cursor.fetchall():
            for url in (tab_url, referrer):
                if not url:
                    continue
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    if not domain:
                        continue
                except Exception:
                    continue
                domain_urls.setdefault(domain, set()).add(url)
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # Match each domain against adapters
        results: list[DetectedPlatform] = []
        matched_domains: set[str] = set()

        for domain, urls in domain_urls.items():
            if domain in matched_domains:
                continue
            for adapter in self._adapters:
                if self._domain_matches(domain, urls, adapter):
                    results.append(DetectedPlatform(
                        domain=domain,
                        platform_type=adapter.name.lower(),
                        adapter=adapter,
                        download_count=domain_counts.get(domain, 0),
                    ))
                    matched_domains.add(domain)
                    break

        # Sort by download count (most downloads first)
        results.sort(key=lambda p: p.download_count, reverse=True)
        return results

    def _domain_matches(
        self, domain: str, urls: set[str], adapter: PlatformAdapter
    ) -> bool:
        """Check if a domain's URLs match any fingerprint of the adapter."""
        for fingerprint in adapter.url_fingerprints:
            # Check if the fingerprint matches the domain itself
            if fingerprint in domain:
                return True
            # Check if any URL from this domain contains the fingerprint
            for url in urls:
                if fingerprint in url:
                    return True
        return False
