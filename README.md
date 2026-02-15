# School File Classifier

**Your Downloads folder is a war zone. This app is the peace treaty.**

You know the drill. It's week 6, you've downloaded 47 PDFs named things like `Lecture_13_FINAL_v2_REAL.pdf` and `Topic 2 Solutions.docx`, they're all sitting in your Downloads folder in one massive pile, and you have no idea which course half of them belong to. You tell yourself you'll organize them later. You won't.

This app does it for you. It reads your Chrome download history, figures out which school platform you use, sorts everything by course and category (Lectures, Tutorials, Assignments, etc.), and moves them into neat folders. One click. Done. Go touch grass.

## How It Works

1. Scans your Chrome download history (don't worry, it's all local)
2. Auto-detects your school's LMS platform (Canvas, Moodle, Blackboard, Insendi)
3. Groups files by course using URL patterns and page titles
4. Uses AI to classify files into Lectures / Tutorials / Assignments / Other
5. Shows you a nice tree view so you can confirm before anything moves
6. Moves files into organized folders. Has an undo button because we're not monsters.

## Supported Platforms

| Platform | Status | Used By |
|----------|--------|---------|
| **Canvas** | Supported | MIT, Stanford, thousands of universities |
| **Moodle** | Supported | Open-source, used worldwide |
| **Blackboard** | Supported | Many large universities |
| **Insendi** | Supported | Imperial College London |
| **Something else?** | Heuristic fallback | Best-effort detection |

Don't see yours? The app has a generic fallback that tries common URL patterns. It also has a plugin system — PRs welcome!

## Quick Start

### Option 1: Run from source (all platforms)

```bash
git clone https://github.com/KaChunLeung/school-file-classifier.git
cd school-file-classifier
pip install -r requirements.txt
python app.py
```

### Option 2: Windows exe (no Python needed)

Download `SchoolFileClassifier.exe` from [Releases](https://github.com/KaChunLeung/school-file-classifier/releases). Double-click. That's it.

## First Run

On your first launch, the app will:

1. **Detect your school platform** — it scans your Chrome history and figures out which LMS you use. No config needed.
2. **Ask for a Groq API key** — this powers the AI file classification (Lectures vs Tutorials vs Assignments). It's free: grab one at [console.groq.com/keys](https://console.groq.com/keys). You only enter it once.
3. **Scan and classify** — your files appear in a tree, sorted by course and category. Check the ones you want to move, click "Move Selected", done.

No API key? No problem. Everything still works — files just won't be sub-categorized (they'll all land under "Other").

## Features

- **Auto-detection** — knows which school platform you use without any config
- **AI classification** — sorts files into Lectures, Tutorials, Assignments, Other
- **Drag and drop** — drag files between categories to recategorize
- **Shift+click / Ctrl+click** — bulk select like a normal human being
- **Right-click menu** — recategorize or open file location
- **Undo** — moved something wrong? Ctrl+Z and it's like nothing happened
- **Dark mode** — because your eyes have suffered enough from lecture slides at 2am
- **Cross-platform** — works on Windows, macOS, and Linux

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Scan |
| `Ctrl+Z` | Undo last move |
| `Ctrl+A` | Select all |
| `Ctrl+S` | Settings |
| `Ctrl+Q` | Quit |
| `M` | Recategorize selected file |

## Requirements

- Python 3.10+
- Google Chrome (the app reads Chrome's download history)
- A [free Groq API key](https://console.groq.com/keys) (optional, for AI classification)

## Building the exe

```bash
pip install pyinstaller
pyinstaller school-file-classifier.spec --noconfirm
```

Output lands in `dist/SchoolFileClassifier.exe`. Place your `config.json` next to it if you have one.

## Adding a New Platform

The app uses a plugin-style adapter pattern. To add support for a new LMS:

1. Create `platforms/yourplatform.py` subclassing `PlatformAdapter`
2. Implement the URL pattern matching and course ID extraction
3. Register it in `platforms/__init__.py`

See `platforms/canvas.py` for a clean example.

## Contributing

PRs are welcome! Especially:

- New platform adapters (if your school uses something we don't support yet)
- Browser support beyond Chrome (Firefox, Edge, Safari)
- Bug fixes from testing on different LMS instances

## License

MIT

---

*Built by a student who got tired of a messy Downloads folder.*
