"""Custom QTreeWidget with checkboxes, drag-drop, and multi-select."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
)

from classifier import ClassifiedFile

# Role for storing ClassifiedFile on tree items
CF_ROLE = Qt.ItemDataRole.UserRole

SUB_TYPE_ICONS = {
    "Lectures": "\U0001f4d6",
    "Tutorials": "\U0001f4dd",
    "Assignments": "\U0001f4cb",
    "Other": "\U0001f4c1",
}

SUB_TYPES = ["Lectures", "Tutorials", "Assignments", "Other"]
_SUB_ORDER = ["Lectures", "Tutorials", "Assignments", "Other", ""]


class FileTreeWidget(QTreeWidget):
    """Tree widget showing classified files grouped by course and sub-type.

    Features:
    - Checkboxes on file items (check = selected for move)
    - Shift+click / Ctrl+click multi-select
    - Drag files between sub-type folders to recategorize
    - Right-click context menu
    - Folder checkbox cascades to children
    """

    # Emitted when the set of checked files changes.  Argument is the count.
    selection_changed = Signal(int)
    # Emitted when a file is recategorized via drag-drop or context menu.
    file_recategorized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setIndentation(24)
        self.setAnimated(True)
        self.setRootIsDecorated(True)

        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemChanged.connect(self._on_item_changed)

        self._classified_files: list[ClassifiedFile] = []
        self._suppress_signals = False

    # ── Public API ────────────────────────────────────────────────────────

    def populate(
        self,
        files: list[ClassifiedFile],
        dest_root: str,
        known_courses: set[str],
    ) -> None:
        """Clear and rebuild the tree from classified files."""
        self._suppress_signals = True
        self._classified_files = files
        self.clear()

        if not files:
            empty = QTreeWidgetItem(self, ["No files found. Press Scan to refresh."])
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._suppress_signals = False
            self.selection_changed.emit(0)
            return

        # Group: course -> sub_type -> files
        courses: dict[str, dict[str, list[ClassifiedFile]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for cf in files:
            courses[cf.course_name][cf.sub_type].append(cf)

        for course_name in sorted(courses):
            if course_name in known_courses:
                label = f"\U0001f4c2 {course_name}"
            else:
                label = f"\u26a0\ufe0f {course_name} (new)"
            course_item = QTreeWidgetItem(self, [label])
            course_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsAutoTristate
            )
            course_item.setCheckState(0, Qt.CheckState.Checked)
            course_item.setExpanded(True)

            subs = courses[course_name]
            for sub_type in _SUB_ORDER:
                if sub_type not in subs:
                    continue
                sub_files = subs[sub_type]

                if sub_type == "":
                    # Files at course root (no sub-folder)
                    for cf in sub_files:
                        self._add_file_item(course_item, cf)
                else:
                    icon = SUB_TYPE_ICONS.get(sub_type, "\U0001f4c1")
                    sub_item = QTreeWidgetItem(
                        course_item,
                        [f"{icon} {sub_type} ({len(sub_files)})"],
                    )
                    sub_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsUserCheckable
                        | Qt.ItemFlag.ItemIsAutoTristate
                        | Qt.ItemFlag.ItemIsDropEnabled
                    )
                    sub_item.setCheckState(0, Qt.CheckState.Checked)
                    sub_item.setExpanded(True)
                    for cf in sub_files:
                        self._add_file_item(sub_item, cf)

        self._suppress_signals = False
        self.selection_changed.emit(self.checked_count())

    def checked_files(self) -> list[ClassifiedFile]:
        """Return all ClassifiedFile objects that are currently checked."""
        result = []
        for i in range(self.topLevelItemCount()):
            self._collect_checked(self.topLevelItem(i), result)
        return result

    def checked_count(self) -> int:
        """Return the number of checked file items."""
        return len(self.checked_files())

    def set_all_checked(self, checked: bool) -> None:
        """Check or uncheck all file items."""
        self._suppress_signals = True
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(0, state)
        self._suppress_signals = False
        self.selection_changed.emit(self.checked_count())

    # ── Private helpers ───────────────────────────────────────────────────

    def _add_file_item(
        self, parent: QTreeWidgetItem, cf: ClassifiedFile
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [cf.path.name])
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setData(0, CF_ROLE, cf)
        return item

    def _collect_checked(
        self, item: QTreeWidgetItem, result: list[ClassifiedFile]
    ) -> None:
        cf = item.data(0, CF_ROLE)
        if cf and item.checkState(0) == Qt.CheckState.Checked:
            result.append(cf)
        for i in range(item.childCount()):
            self._collect_checked(item.child(i), result)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if not self._suppress_signals and column == 0:
            self.selection_changed.emit(self.checked_count())

    # ── Context menu ──────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if not item:
            return
        cf = item.data(0, CF_ROLE)
        if not cf:
            return

        menu = QMenu(self)

        # Recategorize submenu
        recat_menu = menu.addMenu("Move to...")
        for sub in SUB_TYPES:
            icon = SUB_TYPE_ICONS.get(sub, "")
            label = f"{icon} {sub}"
            if sub == cf.sub_type:
                label += " (current)"
            action = recat_menu.addAction(label)
            action.setData(sub)
        recat_menu.addSeparator()
        root_action = recat_menu.addAction("\U0001f4c2 Course root")
        root_action.setData("")

        recat_menu.triggered.connect(
            lambda a: self._recategorize_item(item, cf, a.data())
        )

        # Open file location
        open_action = menu.addAction("Open file location")
        open_action.triggered.connect(
            lambda: self._open_file_location(cf.path)
        )

        menu.exec(self.viewport().mapToGlobal(pos))

    def _recategorize_item(
        self, item: QTreeWidgetItem, cf: ClassifiedFile, new_sub: str
    ) -> None:
        if new_sub == cf.sub_type:
            return
        cf.sub_type = new_sub
        self.file_recategorized.emit()

    def _open_file_location(self, path: Path) -> None:
        import subprocess
        import sys

        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])

    # ── Drag and drop ─────────────────────────────────────────────────────

    def dropEvent(self, event) -> None:
        """Handle drops: recategorize files when dropped on a sub-type folder."""
        target = self.itemAt(event.position().toPoint())
        if not target:
            event.ignore()
            return

        # Determine the sub-type of the drop target
        target_cf = target.data(0, CF_ROLE)
        if target_cf:
            # Dropped on a file — use its sub_type
            new_sub = target_cf.sub_type
        else:
            # Dropped on a folder — parse sub-type from label
            label = target.text(0)
            new_sub = None
            for sub in SUB_TYPES:
                if sub in label:
                    new_sub = sub
                    break
            if new_sub is None:
                # Dropped on a course node — move to course root
                new_sub = ""

        # Update all dragged items
        changed = False
        for item in self.selectedItems():
            cf = item.data(0, CF_ROLE)
            if cf and cf.sub_type != new_sub:
                cf.sub_type = new_sub
                changed = True

        if changed:
            self.file_recategorized.emit()

        # Don't call super — we handle the move by rebuilding the tree
        event.accept()
