# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
pip install -r requirements.txt
python app.py
```

No test suite or build system exists. Verify changes by running the app and scanning.

## Architecture

This is a Python TUI app that organizes Imperial College course files downloaded from Insendi (imperial.insendi.com). It scans Chrome's download history, classifies files by course and sub-type, then moves them into an organized folder structure.

**Data flow:** Chrome History DB → `classifier.py` → LLM sub-classification (`llm.py`) → Tree UI (`app.py`) → File moves (`file_ops.py`)

### Module Roles

- **app.py** — Textual TUI. Single persistent `Tree` widget (never recreated — avoids DuplicateIds). Three modal screens: `RecategorizeDialog`, `NewCourseDialog`, `SettingsScreen`. Scan runs in a worker thread via `@work(thread=True)`, calls back to main thread with `call_from_thread`.
- **classifier.py** — Copies Chrome's locked History SQLite DB to a temp file, queries the `downloads` table for Insendi URLs. Two URL patterns: `/courses/{courseId}/files` (has course ID) and `/api/v1/imp/files/{uuid}` (needs visit-time correlation via `_infer_course_from_visits`). Returns `(list[ClassifiedFile], list[NewCourse])`.
- **llm.py** — Groq API (`llama-3.1-8b-instant`) batch classification. Sends all filenames in one call as a numbered list. Must use `requests` library (not urllib — Cloudflare blocks it).
- **file_ops.py** — `FileOps` class with batch move and stack-based undo. `on_conflict` modes: skip (default), rename, overwrite.
- **config.py** — JSON config with defaults. Auto-creates `config.json` on first run. Course ID→name mappings live here.

### Key Design Decisions

- **Tree widget is composed once** in `compose()` and never replaced. `_rebuild_tree()` only clears/repopulates `TreeNode` children (synchronous). This avoids Textual's async widget lifecycle issues where `.remove()` leaves widgets in the DOM until the next event loop tick.
- **`_node_files: dict[int, ClassifiedFile]`** maps `id(tree_node)` → file data. `_selected: set[int]` tracks checked nodes. Both are cleared and rebuilt on every `_rebuild_tree()`.
- **New course auto-discovery**: When an unknown course ID appears, `_discover_course_name()` looks up Chrome's `urls` table for page titles (pattern: "Course Name - Files"). A dialog lets the user confirm/edit before saving to config.
- **Chrome History path** is hardcoded to Windows Default profile: `~/AppData/Local/Google/Chrome/User Data/Default/History`.

## Config

`config.json` stores: `download_dir`, `destination_root`, `school_domain`, `programme_id`, `groq_api_key`, `sub_folders`, and `courses` (ID→name map). The Groq API key is required for sub-classification (Lectures/Tutorials/Assignments/Other); without it, all files default to "Other".
