"""Main application window for School File Classifier."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
)

from classifier import ClassifiedFile, NewCourse, scan_downloads
from config import load_config, save_config
from file_ops import FileOps
from gui.dialogs import (
    NewCourseDialog,
    PlatformSetupDialog,
    RecategorizeDialog,
    SettingsDialog,
)
from gui.file_tree import FileTreeWidget
from platforms.detector import PlatformDetector


# ── Background scan worker ────────────────────────────────────────────────


class ScanWorker(QThread):
    """Run the Chrome history scan in a background thread."""

    finished = Signal(list, list)  # (classified_files, new_courses)
    error = Signal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config

    def run(self) -> None:
        try:
            files, new_courses = scan_downloads(self.config)
            self.finished.emit(files, new_courses)
        except Exception as e:
            self.error.emit(str(e))


# ── Main Window ───────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("School File Classifier")
        self.setMinimumSize(700, 500)
        self.resize(850, 600)

        self.config = load_config()
        self.file_ops = FileOps()
        self.classified_files: list[ClassifiedFile] = []
        self._scan_worker: ScanWorker | None = None

        self._build_ui()
        self._build_menu()
        self._setup_shortcuts()

        # First-run check: if no platforms configured, run detection
        if not self.config.get("platforms"):
            self._first_run_setup()
        else:
            self._run_scan()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # File tree (central widget)
        self.file_tree = FileTreeWidget(self)
        self.setCentralWidget(self.file_tree)
        self.file_tree.selection_changed.connect(self._on_selection_changed)
        self.file_tree.file_recategorized.connect(self._on_file_recategorized)

        # Toolbar
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("btn-scan")
        self.btn_scan.clicked.connect(self._run_scan)
        toolbar.addWidget(self.btn_scan)

        self.btn_move = QPushButton("Move Selected")
        self.btn_move.setObjectName("btn-move")
        self.btn_move.clicked.connect(self._move_selected)
        toolbar.addWidget(self.btn_move)

        toolbar.addSeparator()

        btn_select = QPushButton("Select All")
        btn_select.clicked.connect(lambda: self.file_tree.set_all_checked(True))
        toolbar.addWidget(btn_select)

        btn_deselect = QPushButton("Deselect All")
        btn_deselect.clicked.connect(lambda: self.file_tree.set_all_checked(False))
        toolbar.addWidget(btn_deselect)

        toolbar.addSeparator()

        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setObjectName("btn-undo")
        self.btn_undo.clicked.connect(self._undo)
        toolbar.addWidget(self.btn_undo)

        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self._open_settings)
        toolbar.addWidget(btn_settings)

        # Status bar
        self.setStatusBar(QStatusBar(self))
        self._set_status("Ready")

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        scan_action = file_menu.addAction("&Scan")
        scan_action.setShortcut(QKeySequence("Ctrl+R"))
        scan_action.triggered.connect(self._run_scan)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        undo_action = edit_menu.addAction("&Undo")
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._undo)
        edit_menu.addSeparator()
        select_all = edit_menu.addAction("Select &All")
        select_all.setShortcut(QKeySequence("Ctrl+A"))
        select_all.triggered.connect(lambda: self.file_tree.set_all_checked(True))
        deselect_all = edit_menu.addAction("&Deselect All")
        deselect_all.triggered.connect(lambda: self.file_tree.set_all_checked(False))
        edit_menu.addSeparator()
        settings_action = edit_menu.addAction("Se&ttings")
        settings_action.setShortcut(QKeySequence("Ctrl+S"))
        settings_action.triggered.connect(self._open_settings)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self._show_about)

    def _setup_shortcuts(self) -> None:
        # Space to toggle is handled natively by QTreeWidget checkboxes
        # M to recategorize
        recat_action = QAction(self)
        recat_action.setShortcut(QKeySequence("M"))
        recat_action.triggered.connect(self._recategorize_selected)
        self.addAction(recat_action)

    # ── Status ────────────────────────────────────────────────────────────

    def _set_status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    @Slot(int)
    def _on_selection_changed(self, count: int) -> None:
        self.btn_move.setText(f"Move Selected ({count})" if count else "Move Selected")

    # ── First-run platform detection ──────────────────────────────────────

    def _first_run_setup(self) -> None:
        """Auto-detect platforms from Chrome history on first run."""
        self._set_status("Detecting school platforms from Chrome history...")

        chrome_db = (
            Path.home()
            / "AppData" / "Local" / "Google" / "Chrome"
            / "User Data" / "Default" / "History"
        )
        if not chrome_db.exists():
            self._set_status("Chrome history not found. Configure platforms in Settings.")
            return

        # Copy DB to avoid lock
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.close()
        tmp_path = Path(tmp.name)
        try:
            shutil.copy2(chrome_db, tmp_path)
            conn = sqlite3.connect(str(tmp_path))
            detector = PlatformDetector()
            detected = detector.detect_from_history(conn.cursor())
            conn.close()
        finally:
            tmp_path.unlink(missing_ok=True)

        # Show setup dialog
        det_list = [
            {
                "domain": d.domain,
                "platform_type": d.platform_type,
                "download_count": d.download_count,
            }
            for d in detected
        ]

        dialog = PlatformSetupDialog(det_list, self)
        if dialog.exec() and dialog.confirmed:
            self.config["platforms"] = dialog.confirmed
            save_config(self.config)
            self._set_status(
                f"Configured {len(dialog.confirmed)} platform"
                f"{'s' if len(dialog.confirmed) != 1 else ''}"
            )
            self._run_scan()
        else:
            self._set_status("No platforms configured. Use Settings to add one.")

    # ── Scan ──────────────────────────────────────────────────────────────

    def _run_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return

        self._set_status("Scanning Chrome history & classifying files...")
        self.btn_scan.setEnabled(False)

        self._scan_worker = ScanWorker(self.config, self)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    @Slot(list, list)
    def _on_scan_finished(
        self, files: list[ClassifiedFile], new_courses: list[NewCourse]
    ) -> None:
        self.btn_scan.setEnabled(True)
        self.classified_files = files
        self._rebuild_tree()

        if new_courses:
            self._show_new_course_dialog(new_courses)

    @Slot(str)
    def _on_scan_error(self, error_msg: str) -> None:
        self.btn_scan.setEnabled(True)
        self._set_status(f"Scan error: {error_msg}")

    def _rebuild_tree(self) -> None:
        known_courses = set(self.config.get("courses", {}).values())
        dest_root = self.config.get("destination_root", "")
        self.file_tree.populate(self.classified_files, dest_root, known_courses)

        total = len(self.classified_files)
        if total:
            courses = {cf.course_name for cf in self.classified_files}
            self._set_status(
                f"Found {total} file{'s' if total != 1 else ''} "
                f"across {len(courses)} course{'s' if len(courses) != 1 else ''}"
            )
        else:
            self._set_status("Scan complete \u2014 no files found")

    # ── New courses ───────────────────────────────────────────────────────

    def _show_new_course_dialog(self, new_courses: list[NewCourse]) -> None:
        dialog = NewCourseDialog(new_courses, self)
        if dialog.exec() and dialog.result_mapping:
            mapping = dialog.result_mapping
            self.config["courses"].update(mapping)
            save_config(self.config)
            # Update course names on classified files
            for cf in self.classified_files:
                if cf.course_id in mapping:
                    cf.course_name = mapping[cf.course_id]
            self._rebuild_tree()
            self._set_status(
                f"Added {len(mapping)} new course"
                f"{'s' if len(mapping) != 1 else ''} to config"
            )

    # ── Move ──────────────────────────────────────────────────────────────

    def _move_selected(self) -> None:
        checked = self.file_tree.checked_files()
        if not checked:
            self._set_status("No files selected")
            return

        dest_root = Path(self.config["destination_root"])
        to_move: list[tuple[Path, Path]] = []
        for cf in checked:
            if cf.sub_type:
                dest_dir = dest_root / cf.course_name / cf.sub_type
            else:
                dest_dir = dest_root / cf.course_name
            to_move.append((cf.path, dest_dir))

        result = self.file_ops.move_files(to_move, on_conflict="skip")

        moved = len(result.success)
        skipped = len(result.skipped)
        parts = [f"Moved {moved} file{'s' if moved != 1 else ''}"]
        if skipped:
            parts.append(f", skipped {skipped} (already exist)")
        self._set_status("".join(parts))

        self._run_scan()

    # ── Undo ──────────────────────────────────────────────────────────────

    def _undo(self) -> None:
        if not self.file_ops.can_undo:
            self._set_status("Nothing to undo")
            return
        undone = self.file_ops.undo_last()
        self._set_status(
            f"Undone {len(undone)} file{'s' if len(undone) != 1 else ''}"
        )
        self._run_scan()

    # ── Recategorize ──────────────────────────────────────────────────────

    def _recategorize_selected(self) -> None:
        items = self.file_tree.selectedItems()
        if not items:
            self._set_status("Select a file to re-categorize")
            return

        from gui.file_tree import CF_ROLE

        item = items[0]
        cf = item.data(0, CF_ROLE)
        if not cf:
            self._set_status("Select a file to re-categorize")
            return

        dialog = RecategorizeDialog(cf, self)
        if dialog.exec() and dialog.selected_sub is not None:
            if dialog.selected_sub != cf.sub_type:
                cf.sub_type = dialog.selected_sub
                self._rebuild_tree()
                label = cf.sub_type if cf.sub_type else "course root"
                self._set_status(f"Moved '{cf.path.name}' to {label}")

    @Slot()
    def _on_file_recategorized(self) -> None:
        """Called when a file is recategorized via drag-drop or context menu."""
        self._rebuild_tree()

    # ── Settings ──────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() and dialog.saved:
            self.config = load_config()
            self._set_status("Settings saved")
            self._run_scan()

    # ── About ─────────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About School File Classifier",
            "<b>School File Classifier</b><br><br>"
            "Organizes files downloaded from school platforms "
            "(Canvas, Moodle, Blackboard, Insendi, and more).<br><br>"
            "Scans your Chrome download history, classifies files by course "
            "and category, then moves them into organized folders.<br><br>"
            "Open source — contributions welcome!",
        )
