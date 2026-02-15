"""Configuration management for School File Classifier."""

import json
import sys
from pathlib import Path

# When running as a PyInstaller exe, __file__ points to a temp extraction dir.
# Use the exe's directory instead so config.json lives next to the exe.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).parent

CONFIG_PATH = _BASE_DIR / "config.json"

DEFAULTS = {
    "download_dir": str(Path.home() / "Downloads"),
    "destination_root": str(Path.home() / "Documents" / "School"),
    "groq_api_key": "",
    "sub_folders": ["Lectures", "Tutorials", "Assignments", "Other"],
    "platforms": [],   # Auto-detected: [{"domain": "...", "type": "canvas"}, ...]
    "courses": {},     # Populated via auto-discovery
}


def _migrate_v1_config(config: dict) -> dict:
    """Migrate from v1 config format (single school_domain) to v2 (platforms list).

    Preserves existing course mappings and settings.
    """
    if "school_domain" not in config:
        return config

    domain = config.pop("school_domain", "")
    config.pop("programme_id", None)

    if domain and "platforms" not in config:
        # Guess platform type from domain
        if "insendi" in domain:
            ptype = "insendi"
        elif "instructure" in domain:
            ptype = "canvas"
        else:
            ptype = "generic"
        config["platforms"] = [{"domain": domain, "type": ptype}]

    return config


def load_config() -> dict:
    """Load config from disk, creating with defaults if missing."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Migrate old format if needed
        config = _migrate_v1_config(config)
        # Merge any new default keys the user doesn't have yet
        for key, value in DEFAULTS.items():
            if key not in config:
                config[key] = value
        return config
    # First run — write defaults
    save_config(DEFAULTS)
    return dict(DEFAULTS)


def save_config(config: dict) -> None:
    """Persist config to disk."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_course_name(config: dict, course_id: str) -> str:
    """Look up a course name by ID, returning 'Unknown Course' if not mapped."""
    return config["courses"].get(course_id, "Unknown Course")
