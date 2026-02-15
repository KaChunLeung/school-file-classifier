"""Qt dialog windows for School File Classifier."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from classifier import ClassifiedFile, NewCourse
from config import save_config
from gui.file_tree import SUB_TYPE_ICONS, SUB_TYPES


# ── Recategorize Dialog ───────────────────────────────────────────────────


class RecategorizeDialog(QDialog):
    """Pick a new sub-category for a file."""

    def __init__(self, cf: ClassifiedFile, parent=None):
        super().__init__(parent)
        self.cf = cf
        self.selected_sub: str | None = None
        self.setWindowTitle("Recategorize File")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Move <b>{cf.path.name}</b> to:"))

        self._radios: dict[str, QRadioButton] = {}
        group = QGroupBox("Category")
        group_layout = QVBoxLayout(group)

        for sub in SUB_TYPES:
            icon = SUB_TYPE_ICONS.get(sub, "")
            label = f"{icon}  {sub}"
            if sub == cf.sub_type:
                label += "  (current)"
            radio = QRadioButton(label)
            if sub == cf.sub_type:
                radio.setChecked(True)
            self._radios[sub] = radio
            group_layout.addWidget(radio)

        root_radio = QRadioButton("\U0001f4c2  Course root (no sub-folder)")
        if cf.sub_type == "":
            root_radio.setChecked(True)
        self._radios[""] = root_radio
        group_layout.addWidget(root_radio)

        layout.addWidget(group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        for sub, radio in self._radios.items():
            if radio.isChecked():
                self.selected_sub = sub
                break
        self.accept()


# ── New Course Dialog ─────────────────────────────────────────────────────


class NewCourseDialog(QDialog):
    """Confirm or edit names for newly discovered courses."""

    def __init__(self, new_courses: list[NewCourse], parent=None):
        super().__init__(parent)
        self.new_courses = new_courses
        self.result_mapping: dict[str, str] | None = None
        self.setWindowTitle("New Courses Detected")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        count = len(new_courses)
        layout.addWidget(QLabel(
            f"<b>{count} new course{'s' if count != 1 else ''} detected!</b><br>"
            "Edit the names below, then click Save to add them."
        ))

        self._inputs: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for nc in new_courses:
            inp = QLineEdit(nc.suggested_name)
            inp.setPlaceholderText("Course name")
            self._inputs[nc.course_id] = inp
            form.addRow(nc.course_id[:12] + "...", inp)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save All")
        save_btn.clicked.connect(self._save)
        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(skip_btn)
        layout.addLayout(btn_layout)

    def _save(self) -> None:
        self.result_mapping = {}
        for cid, inp in self._inputs.items():
            name = inp.text().strip()
            if name:
                self.result_mapping[cid] = name
        self.accept()


# ── Platform Setup Dialog ─────────────────────────────────────────────────


class PlatformSetupDialog(QDialog):
    """First-run wizard to confirm auto-detected platforms."""

    def __init__(self, detected: list[dict], parent=None):
        """detected: list of {"domain": str, "platform_type": str, "download_count": int}"""
        super().__init__(parent)
        self.detected = detected
        self.confirmed: list[dict] | None = None
        self.setWindowTitle("Platform Setup")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<b>Welcome to School File Classifier!</b><br><br>"
            "We scanned your Chrome download history and detected "
            "downloads from these school platforms:"
        ))

        self._checkboxes: list[tuple[dict, QLineEdit]] = []
        for det in detected:
            row = QHBoxLayout()
            from PySide6.QtWidgets import QCheckBox
            cb = QCheckBox()
            cb.setChecked(True)
            row.addWidget(cb)
            label = QLabel(
                f"<b>{det['platform_type'].title()}</b> — {det['domain']} "
                f"({det['download_count']} downloads)"
            )
            row.addWidget(label, 1)
            self._checkboxes.append((det, cb))
            layout.addLayout(row)

        if not detected:
            layout.addWidget(QLabel(
                "<i>No school platforms detected. You can add one manually in Settings.</i>"
            ))

        # Manual add section
        layout.addSpacing(12)
        layout.addWidget(QLabel("Or add a platform manually:"))
        manual_layout = QHBoxLayout()
        self._manual_domain = QLineEdit()
        self._manual_domain.setPlaceholderText("e.g. canvas.myschool.edu")
        manual_layout.addWidget(self._manual_domain, 1)
        self._manual_type = QLineEdit()
        self._manual_type.setPlaceholderText("Type: canvas, moodle, blackboard")
        manual_layout.addWidget(self._manual_type, 1)
        layout.addLayout(manual_layout)

        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("Confirm && Scan")
        confirm_btn.clicked.connect(self._confirm)
        skip_btn = QPushButton("Skip for now")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(skip_btn)
        layout.addLayout(btn_layout)

    def _confirm(self) -> None:
        from PySide6.QtWidgets import QCheckBox

        self.confirmed = []
        for det, cb in self._checkboxes:
            if cb.isChecked():
                self.confirmed.append({
                    "domain": det["domain"],
                    "type": det["platform_type"],
                })

        # Include manual entry if provided
        manual_domain = self._manual_domain.text().strip()
        manual_type = self._manual_type.text().strip().lower()
        if manual_domain and manual_type:
            self.confirmed.append({
                "domain": manual_domain,
                "type": manual_type,
            })

        self.accept()


# ── Settings Dialog ───────────────────────────────────────────────────────


class SettingsDialog(QDialog):
    """Tabbed settings dialog: General, Platforms, Courses."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.saved = False
        self.setWindowTitle("Settings")
        self.setMinimumSize(550, 450)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # ── General tab ──
        general = QWidget()
        gen_layout = QFormLayout(general)
        self._download_dir = QLineEdit(config.get("download_dir", ""))
        gen_layout.addRow("Downloads folder:", self._download_dir)
        self._dest_root = QLineEdit(config.get("destination_root", ""))
        gen_layout.addRow("Destination root:", self._dest_root)
        self._api_key = QLineEdit(config.get("groq_api_key", ""))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        gen_layout.addRow("Groq API key:", self._api_key)
        tabs.addTab(general, "General")

        # ── Platforms tab ──
        platforms_widget = QWidget()
        plat_layout = QVBoxLayout(platforms_widget)
        plat_layout.addWidget(QLabel("Configured platforms:"))

        self._platform_inputs: list[tuple[QLineEdit, QLineEdit]] = []
        platforms = config.get("platforms", [])
        for p in platforms:
            row = QHBoxLayout()
            domain_inp = QLineEdit(p.get("domain", ""))
            domain_inp.setPlaceholderText("Domain")
            type_inp = QLineEdit(p.get("type", ""))
            type_inp.setPlaceholderText("Type")
            row.addWidget(domain_inp, 2)
            row.addWidget(type_inp, 1)
            self._platform_inputs.append((domain_inp, type_inp))
            plat_layout.addLayout(row)

        # Add new platform row
        add_btn = QPushButton("+ Add Platform")
        add_btn.clicked.connect(lambda: self._add_platform_row(plat_layout))
        plat_layout.addWidget(add_btn)
        plat_layout.addStretch()
        tabs.addTab(platforms_widget, "Platforms")

        # ── Courses tab ──
        courses_widget = QWidget()
        courses_layout = QVBoxLayout(courses_widget)
        courses_layout.addWidget(QLabel("Course ID \u2192 Name mappings:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self._courses_layout = QFormLayout(scroll_content)
        self._course_inputs: dict[str, QLineEdit] = {}
        for cid, cname in config.get("courses", {}).items():
            inp = QLineEdit(cname)
            self._course_inputs[cid] = inp
            self._courses_layout.addRow(cid[:16], inp)
        scroll.setWidget(scroll_content)
        courses_layout.addWidget(scroll)
        tabs.addTab(courses_widget, "Courses")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_platform_row(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        domain_inp = QLineEdit()
        domain_inp.setPlaceholderText("Domain (e.g. canvas.myschool.edu)")
        type_inp = QLineEdit()
        type_inp.setPlaceholderText("Type (canvas, moodle, blackboard, insendi)")
        row.addWidget(domain_inp, 2)
        row.addWidget(type_inp, 1)
        self._platform_inputs.append((domain_inp, type_inp))
        # Insert before the stretch
        layout.insertLayout(layout.count() - 2, row)

    def _save(self) -> None:
        self.config["download_dir"] = self._download_dir.text()
        self.config["destination_root"] = self._dest_root.text()
        self.config["groq_api_key"] = self._api_key.text()

        # Save platforms
        platforms = []
        for domain_inp, type_inp in self._platform_inputs:
            domain = domain_inp.text().strip()
            ptype = type_inp.text().strip().lower()
            if domain and ptype:
                platforms.append({"domain": domain, "type": ptype})
        self.config["platforms"] = platforms

        # Save courses
        for cid, inp in self._course_inputs.items():
            self.config["courses"][cid] = inp.text().strip()

        save_config(self.config)
        self.saved = True
        self.accept()
