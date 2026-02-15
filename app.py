"""Imperial File Classifier — Textual TUI application."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Static,
    Tree,
)
from textual.widgets.option_list import Option
from textual.widgets.tree import TreeNode

from classifier import ClassifiedFile, NewCourse, scan_downloads
from config import load_config, save_config
from file_ops import FileOps

SUB_TYPE_ICONS = {
    "Lectures": "\U0001f4d6",
    "Tutorials": "\U0001f4dd",
    "Assignments": "\U0001f4cb",
    "Other": "\U0001f4c1",
}

SUB_TYPES = ["Lectures", "Tutorials", "Assignments", "Other"]


# ── Re-categorize Dialog ─────────────────────────────────────────────────────


class RecategorizeDialog(ModalScreen[str | None]):
    """Pick a new sub-category for the selected file."""

    DEFAULT_CSS = """
    RecategorizeDialog {
        align: center middle;
    }
    #recat-box {
        width: 40;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #recat-box Label {
        width: 100%;
        margin-bottom: 1;
    }
    #recat-options {
        width: 100%;
        height: auto;
        max-height: 12;
    }
    """

    def __init__(self, filename: str, current_sub: str) -> None:
        super().__init__()
        self.filename = filename
        self.current_sub = current_sub

    def compose(self) -> ComposeResult:
        with Vertical(id="recat-box"):
            yield Label(f"Move [bold]{self.filename}[/bold] to:")
            options = []
            for sub in SUB_TYPES:
                label = f"{SUB_TYPE_ICONS[sub]} {sub}"
                if sub == self.current_sub:
                    label += " (current)"
                options.append(Option(label, id=sub))
            options.append(Option("\U0001f4c2 Course root (no sub-folder)", id="_root"))
            yield OptionList(*options, id="recat-options")

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(event.option.id)

    def key_escape(self) -> None:
        self.dismiss(None)


# ── New Course Dialog ────────────────────────────────────────────────────────


class NewCourseDialog(ModalScreen[dict | None]):
    """Confirm or edit names for newly discovered courses, then save them."""

    DEFAULT_CSS = """
    NewCourseDialog {
        align: center middle;
    }
    #newcourse-box {
        width: 70;
        height: auto;
        max-height: 30;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #newcourse-box Label {
        width: 100%;
        margin-bottom: 1;
    }
    .nc-row {
        width: 100%;
        height: 3;
        layout: horizontal;
        margin-bottom: 1;
    }
    .nc-row .nc-id {
        width: 16;
        padding: 1 1 0 0;
    }
    .nc-row Input {
        width: 1fr;
    }
    #nc-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    #nc-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, new_courses: list[NewCourse]) -> None:
        super().__init__()
        self.new_courses = new_courses

    def compose(self) -> ComposeResult:
        with Vertical(id="newcourse-box"):
            yield Label(
                f"[bold]\u2728 {len(self.new_courses)} new course"
                f"{'s' if len(self.new_courses) != 1 else ''} detected![/bold]\n"
                "Edit the names below, then click Save to add them."
            )
            for nc in self.new_courses:
                with Horizontal(classes="nc-row"):
                    yield Static(nc.course_id[:12], classes="nc-id")
                    yield Input(
                        value=nc.suggested_name,
                        id=f"nc-{nc.course_id}",
                        placeholder="Course name",
                    )
            with Horizontal(id="nc-buttons"):
                yield Button("Save All", id="nc-save", variant="primary")
                yield Button("Skip", id="nc-skip")

    @on(Button.Pressed, "#nc-save")
    def save(self) -> None:
        mapping: dict[str, str] = {}
        for nc in self.new_courses:
            inp = self.query_one(f"#nc-{nc.course_id}", Input)
            name = inp.value.strip()
            if name:
                mapping[nc.course_id] = name
        self.dismiss(mapping)

    @on(Button.Pressed, "#nc-skip")
    def skip(self) -> None:
        self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)


# ── Settings Screen ──────────────────────────────────────────────────────────


class SettingsScreen(ModalScreen[bool]):
    """Edit app configuration."""

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }
    #settings-box {
        width: 80;
        height: auto;
        max-height: 40;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    .setting-row {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    .setting-row Label {
        width: 100%;
    }
    .setting-row Input {
        width: 100%;
    }
    #settings-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    #settings-buttons Button {
        margin: 0 1;
    }
    #course-list {
        width: 100%;
        height: auto;
        max-height: 15;
        overflow-y: auto;
        border: tall $primary-background;
        padding: 0 1;
    }
    .course-row {
        width: 100%;
        height: 3;
        layout: horizontal;
    }
    .course-row Input {
        width: 1fr;
    }
    .course-row .course-id {
        width: 16;
        padding: 1 1 0 0;
    }
    """

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-box"):
            yield Label("[bold]Settings[/bold]")

            with Vertical(classes="setting-row"):
                yield Label("Downloads folder:")
                yield Input(
                    value=self.config["download_dir"], id="input-download-dir"
                )

            with Vertical(classes="setting-row"):
                yield Label("Destination root folder:")
                yield Input(
                    value=self.config["destination_root"], id="input-dest-root"
                )

            yield Label("[bold]Course Mappings[/bold] (ID : Name)")
            with VerticalScroll(id="course-list"):
                for cid, cname in self.config["courses"].items():
                    with Horizontal(classes="course-row"):
                        yield Static(cid, classes="course-id")
                        yield Input(value=cname, id=f"course-{cid}")

            with Horizontal(id="settings-buttons"):
                yield Button("Save", id="save-settings", variant="primary")
                yield Button("Cancel", id="cancel-settings")

    @on(Button.Pressed, "#save-settings")
    def save(self) -> None:
        self.config["download_dir"] = self.query_one(
            "#input-download-dir", Input
        ).value
        self.config["destination_root"] = self.query_one(
            "#input-dest-root", Input
        ).value

        for cid in list(self.config["courses"]):
            inp = self.query_one(f"#course-{cid}", Input)
            self.config["courses"][cid] = inp.value

        save_config(self.config)
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-settings")
    def cancel(self) -> None:
        self.dismiss(False)


# ── Main App ─────────────────────────────────────────────────────────────────


class ImperialClassifier(App):
    """Imperial File Classifier TUI."""

    TITLE = "Imperial File Classifier"

    CSS = """
    #file-tree {
        width: 100%;
        height: 1fr;
    }
    #toolbar {
        width: 100%;
        height: 3;
        dock: bottom;
        align: center middle;
        background: $primary-background;
        padding: 0 1;
    }
    #toolbar Button {
        margin: 0 1;
    }
    #status-bar {
        width: 100%;
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+r", "scan", "Scan"),
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+s", "settings", "Settings"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("space", "toggle_node", "Toggle", show=False),
        Binding("m", "recategorize", "Re-categorize"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.file_ops = FileOps()
        self.classified_files: list[ClassifiedFile] = []
        self._node_files: dict[int, ClassifiedFile] = {}
        self._selected: set[int] = set()
        self._pending_new_courses: list[NewCourse] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tree("Imperial File Classifier", id="file-tree")
        with Horizontal(id="toolbar"):
            yield Button("Scan", id="btn-scan", variant="primary")
            yield Button("Move Selected", id="btn-move", variant="success")
            yield Button("Select All", id="btn-select-all")
            yield Button("Deselect All", id="btn-deselect-all")
            yield Button("Undo", id="btn-undo", variant="warning")
            yield Button("Settings", id="btn-settings")
        yield Static("Ready", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.run_scan()

    def _set_status(self, text: str) -> None:
        self.query_one("#status-bar", Static).update(text)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_tree(self) -> Tree:
        return self.query_one("#file-tree", Tree)

    # ── Actions ──────────────────────────────────────────────────────────

    def action_scan(self) -> None:
        self.run_scan()

    def action_undo(self) -> None:
        self._do_undo()

    def action_settings(self) -> None:
        self._open_settings()

    def action_toggle_node(self) -> None:
        """Toggle selection on the highlighted tree node."""
        tree = self._get_tree()
        node = tree.cursor_node
        if node is None:
            return
        if id(node) in self._node_files:
            self._toggle_file_node(node)
        else:
            self._toggle_folder_children(node)

    def action_recategorize(self) -> None:
        """Open dialog to move the highlighted file to a different sub-category."""
        tree = self._get_tree()
        node = tree.cursor_node
        if node is None:
            return
        cf = self._node_files.get(id(node))
        if cf is None:
            self._set_status("Select a file to re-categorize")
            return

        def on_result(new_sub: str | None) -> None:
            if new_sub is None:
                return
            if new_sub == "_root":
                cf.sub_type = ""
            elif new_sub == cf.sub_type:
                return
            else:
                cf.sub_type = new_sub
            self._rebuild_tree()
            self._set_status(
                f"Moved '{cf.path.name}' to "
                + (cf.sub_type if cf.sub_type else "course root")
            )

        self.push_screen(
            RecategorizeDialog(cf.path.name, cf.sub_type),
            on_result,
        )

    # ── Toggle helpers ───────────────────────────────────────────────────

    def _toggle_file_node(self, node: TreeNode) -> None:
        node_id = id(node)
        cf = self._node_files.get(node_id)
        if cf is None:
            return
        if node_id in self._selected:
            self._selected.discard(node_id)
            node.set_label(self._file_label(cf, selected=False))
        else:
            self._selected.add(node_id)
            node.set_label(self._file_label(cf, selected=True))
        self._update_move_btn()

    def _toggle_folder_children(self, node: TreeNode) -> None:
        """Toggle all file descendants under a folder node."""
        file_ids = self._collect_file_ids(node)
        if not file_ids:
            return
        all_selected = all(fid in self._selected for fid in file_ids)
        self._set_descendants(node, select=not all_selected)
        self._update_move_btn()

    def _collect_file_ids(self, node: TreeNode) -> list[int]:
        """Recursively collect all file-leaf node IDs under a node."""
        result = []
        for child in node.children:
            cid = id(child)
            if cid in self._node_files:
                result.append(cid)
            else:
                result.extend(self._collect_file_ids(child))
        return result

    def _set_descendants(self, node: TreeNode, select: bool) -> None:
        """Set all file descendants to selected/deselected."""
        for child in node.children:
            cid = id(child)
            cf = self._node_files.get(cid)
            if cf:
                if select:
                    self._selected.add(cid)
                else:
                    self._selected.discard(cid)
                child.set_label(self._file_label(cf, selected=select))
            else:
                self._set_descendants(child, select)

    def _file_label(self, cf: ClassifiedFile, selected: bool) -> str:
        check = "[green]\u2714[/]" if selected else "[dim]\u2718[/]"
        return f"{check} {cf.path.name}"

    def _update_move_btn(self) -> None:
        count = len(self._selected)
        btn = self.query_one("#btn-move", Button)
        btn.label = f"Move Selected ({count})" if count else "Move Selected"

    # ── Scan ─────────────────────────────────────────────────────────────

    @work(thread=True)
    def run_scan(self) -> None:
        self.app.call_from_thread(
            self._set_status, "Scanning Chrome history & classifying files..."
        )
        from classifier import scan_downloads as _scan

        self.classified_files, new_courses = _scan(self.config)
        self._pending_new_courses = new_courses
        self.app.call_from_thread(self._after_scan)

    def _after_scan(self) -> None:
        """Called on the main thread after scan completes."""
        self._rebuild_tree()
        if self._pending_new_courses:
            self._show_new_course_dialog()

    def _rebuild_tree(self) -> None:
        """Clear and repopulate the persistent Tree widget."""
        tree = self._get_tree()
        self._node_files.clear()
        self._selected.clear()

        # Clear all existing nodes
        tree.root.remove_children()

        if not self.classified_files:
            dest_root = Path(self.config["destination_root"])
            tree.root.set_label(str(dest_root))
            tree.root.add_leaf("[dim]No files found. Press Scan to refresh.[/]")
            tree.root.expand()
            self._set_status("Scan complete \u2014 no files found")
            self._update_move_btn()
            return

        dest_root = Path(self.config["destination_root"])
        tree.root.set_label(str(dest_root))
        tree.guide_depth = 3

        # Group: course -> sub_type -> files
        courses: dict[str, dict[str, list[ClassifiedFile]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for cf in self.classified_files:
            courses[cf.course_name][cf.sub_type].append(cf)

        sub_order = ["Lectures", "Tutorials", "Assignments", "Other", ""]

        known_names = set(self.config["courses"].values())

        for course_name in sorted(courses):
            if course_name in known_names:
                label = f"\U0001f4c2 {course_name}"
            else:
                label = f"\u26a0\ufe0f {course_name} [dim](new)[/]"
            course_node = tree.root.add(label, expand=True)

            subs = courses[course_name]
            for sub_type in sub_order:
                if sub_type not in subs:
                    continue
                files = subs[sub_type]

                if sub_type == "":
                    for cf in files:
                        leaf = course_node.add_leaf(
                            self._file_label(cf, selected=True)
                        )
                        self._node_files[id(leaf)] = cf
                        self._selected.add(id(leaf))
                else:
                    icon = SUB_TYPE_ICONS.get(sub_type, "\U0001f4c1")
                    sub_node = course_node.add(
                        f"{icon} {sub_type} ({len(files)})",
                        expand=True,
                    )
                    for cf in files:
                        leaf = sub_node.add_leaf(
                            self._file_label(cf, selected=True)
                        )
                        self._node_files[id(leaf)] = cf
                        self._selected.add(id(leaf))

        tree.root.expand()
        self._update_move_btn()

        total = len(self.classified_files)
        n_courses = len(courses)
        self._set_status(
            f"Found {total} file{'s' if total != 1 else ''} "
            f"across {n_courses} course{'s' if n_courses != 1 else ''}"
        )

    # ── New course discovery ────────────────────────────────────────────

    def _show_new_course_dialog(self) -> None:
        """Show dialog for user to confirm/edit newly discovered courses."""
        courses = self._pending_new_courses
        self._pending_new_courses = []

        def on_result(mapping: dict | None) -> None:
            if not mapping:
                return
            # Save new courses to config
            self.config["courses"].update(mapping)
            save_config(self.config)
            # Update course names on already-classified files
            for cf in self.classified_files:
                if cf.course_id in mapping:
                    cf.course_name = mapping[cf.course_id]
            self._rebuild_tree()
            self._set_status(
                f"Added {len(mapping)} new course"
                f"{'s' if len(mapping) != 1 else ''} to config"
            )

        self.push_screen(NewCourseDialog(courses), on_result)

    # ── Move ─────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-move")
    def on_move(self) -> None:
        dest_root = Path(self.config["destination_root"])
        to_move: list[tuple[Path, Path]] = []

        for node_id in list(self._selected):
            cf = self._node_files.get(node_id)
            if cf:
                if cf.sub_type:
                    dest_dir = dest_root / cf.course_name / cf.sub_type
                else:
                    dest_dir = dest_root / cf.course_name
                to_move.append((cf.path, dest_dir))

        if not to_move:
            self._set_status("No files selected")
            return

        result = self.file_ops.move_files(to_move, on_conflict="skip")

        moved = len(result.success)
        skipped = len(result.skipped)
        parts = [f"Moved {moved} file{'s' if moved != 1 else ''}"]
        if skipped:
            parts.append(f", skipped {skipped} (already exist)")
        self._set_status("".join(parts))

        self.run_scan()

    # ── Select / Deselect ────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-select-all")
    def select_all(self) -> None:
        for node_id in self._node_files:
            self._selected.add(node_id)
        self._refresh_all_labels(True)
        self._update_move_btn()

    @on(Button.Pressed, "#btn-deselect-all")
    def deselect_all(self) -> None:
        self._selected.clear()
        self._refresh_all_labels(False)
        self._update_move_btn()

    def _refresh_all_labels(self, selected: bool) -> None:
        tree = self._get_tree()
        self._walk_and_set(tree.root, selected)

    def _walk_and_set(self, node: TreeNode, selected: bool) -> None:
        nid = id(node)
        cf = self._node_files.get(nid)
        if cf:
            node.set_label(self._file_label(cf, selected))
        for child in node.children:
            self._walk_and_set(child, selected)

    # ── Tree click / enter ───────────────────────────────────────────────

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if id(node) in self._node_files:
            self._toggle_file_node(node)
        else:
            self._toggle_folder_children(node)

    # ── Undo ─────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-undo")
    def on_undo_btn(self) -> None:
        self._do_undo()

    def _do_undo(self) -> None:
        if not self.file_ops.can_undo:
            self._set_status("Nothing to undo")
            return
        undone = self.file_ops.undo_last()
        self._set_status(
            f"Undone {len(undone)} file{'s' if len(undone) != 1 else ''}"
        )
        self.run_scan()

    # ── Settings ─────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-settings")
    def on_settings_btn(self) -> None:
        self._open_settings()

    def _open_settings(self) -> None:
        def on_dismiss(saved: bool | None) -> None:
            if saved:
                self.config = load_config()
                self._set_status("Settings saved")
                self.run_scan()

        self.push_screen(SettingsScreen(self.config), on_dismiss)

    # ── Scan button ──────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-scan")
    def on_scan_btn(self) -> None:
        self.run_scan()


if __name__ == "__main__":
    ImperialClassifier().run()
