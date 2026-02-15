"""School File Classifier — PySide6 GUI application."""

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import DARK_STYLE


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    app.setApplicationName("School File Classifier")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
