"""QSS stylesheet definitions for School File Classifier."""

DARK_STYLE = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QTreeWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    font-size: 13px;
    outline: none;
}

QTreeWidget::item {
    padding: 4px 2px;
    border-bottom: 1px solid #1e1e2e;
}

QTreeWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}

QTreeWidget::item:hover {
    background-color: #313244;
}

QTreeWidget::indicator:checked {
    image: none;
    background-color: #89b4fa;
    border: 2px solid #89b4fa;
    border-radius: 3px;
    width: 14px;
    height: 14px;
}

QTreeWidget::indicator:unchecked {
    image: none;
    background-color: transparent;
    border: 2px solid #585b70;
    border-radius: 3px;
    width: 14px;
    height: 14px;
}

QToolBar {
    background-color: #1e1e2e;
    border-bottom: 1px solid #313244;
    spacing: 6px;
    padding: 4px;
}

QToolBar QToolButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QToolBar QToolButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}

QToolBar QToolButton:pressed {
    background-color: #585b70;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton#btn-scan {
    background-color: #89b4fa;
    color: #1e1e2e;
    border-color: #89b4fa;
    font-weight: 600;
}

QPushButton#btn-scan:hover {
    background-color: #74c7ec;
    border-color: #74c7ec;
}

QPushButton#btn-move {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border-color: #a6e3a1;
    font-weight: 600;
}

QPushButton#btn-move:hover {
    background-color: #94e2d5;
    border-color: #94e2d5;
}

QPushButton#btn-undo {
    background-color: #f9e2af;
    color: #1e1e2e;
    border-color: #f9e2af;
}

QPushButton#btn-undo:hover {
    background-color: #f5c2e7;
    border-color: #f5c2e7;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 12px;
    padding: 2px 8px;
}

QMenuBar {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
}

QMenuBar::item:selected {
    background-color: #45475a;
}

QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
}

QMenu::item:selected {
    background-color: #45475a;
}

QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QLabel {
    color: #cdd6f4;
    font-size: 13px;
}

QLineEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #89b4fa;
}

QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-bottom-color: #1e1e2e;
}

QRadioButton {
    color: #cdd6f4;
    font-size: 13px;
    spacing: 8px;
}

QGroupBox {
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    padding: 0 6px;
}

QScrollBar:vertical {
    background: #181825;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
