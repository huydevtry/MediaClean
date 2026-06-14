#!/usr/bin/env python3
"""
main.py - Entry point for MediaClean.

Usage:
    python main.py
"""
import sys
import logging
import os
import traceback

# Make sure the project root is on the path when running directly
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.ui.main_window import MainWindow
from src.utils.constants import APP_NAME

CRASH_LOG = os.path.join(os.path.dirname(__file__), "crash.log")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(CRASH_LOG, encoding="utf-8"),
        ],
    )


def _handle_exception(exc_type, exc_value, exc_tb):
    """Write unhandled exceptions to crash.log and show a dialog."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", msg)
    # Show error dialog if QApplication exists
    app = QApplication.instance()
    if app:
        box = QMessageBox()
        box.setWindowTitle("MediaClean — Lỗi không mong muốn")
        box.setIcon(QMessageBox.Icon.Critical)
        box.setText("App gặp lỗi. Chi tiết đã ghi vào crash.log")
        box.setDetailedText(msg)
        box.exec()
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _handle_exception


def main() -> None:
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("MediaClean")

    # Enable high-DPI scaling
    try:
        app.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass

    # Default application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception:
        logging.critical("Fatal error during startup:", exc_info=True)
        raise


if __name__ == "__main__":
    main()
