"""Configuration management for Imperial File Classifier."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULTS = {
    "download_dir": str(Path.home() / "Downloads"),
    "destination_root": str(Path.home() / "Documents" / "Imperial"),
    "school_domain": "imperial.insendi.com",
    "programme_id": "qSErlKBRX",
    "groq_api_key": "",
    "sub_folders": ["Lectures", "Tutorials", "Assignments", "Other"],
    "courses": {
        "ZNgm66ic_z": "Big Data in Finance",
        "eQzfK6_unk": "Derivatives",
        "gHijJWnoEw": "Accounting & Corporate Finance",
        "pcp5uqKK73": "Blockchain and Applications",
        "GUUrYtOA2e": "C++ for Finance",
        "FD9R_qtRds": "Introduction to Maths",
        "uEgGTaPYYx": "International Finance",
        "br3yeiapUK": "Financial Econometrics",
        "3G5A73tb39": "Application of R for Finance",
        "PsG5VmwXkz": "Mathematics for Finance",
        "xzaXFRvZo5": "Markets and Securities",
    },
}


def load_config() -> dict:
    """Load config from disk, creating with defaults if missing."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
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
