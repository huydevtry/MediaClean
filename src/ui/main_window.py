"""
main_window.py - Primary application window for MediaClean.

Responsibilities:
  • Folder selection + scan controls (shared across both tabs)
  • Spawning Scanner / DuplicateFinder / SameNameFinder workers
  • Routing signals to the two feature tabs
  • Status bar & global app state
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTabWidget, QFileDialog,
    QStatusBar, QFrame, QCheckBox, QComboBox, QProgressBar,
    QMessageBox, QSizePolicy, QToolBar,
)

from src.core.scanner        import Scanner
from src.core.duplicate_finder import DuplicateFinder
from src.core.name_finder    import SameNameFinder
from src.core.file_manager   import is_send2trash_available
from src.ui.duplicate_tab    import DuplicateTab
from src.ui.name_tab         import NameTab
from src.ui.styles           import MAIN_STYLESHEET
from src.utils.constants     import (
    APP_NAME, APP_VERSION,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    ALL_MEDIA_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS,
    COLOR_BG_PANEL, COLOR_BG_DARK, COLOR_BORDER, COLOR_ACCENT,
    COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_HEADER_BG, COLOR_HEADER_TEXT,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._scan_files: List[str] = []
        self._scanner = Scanner()
        self._dup_finder = DuplicateFinder()
        self._name_finder = SameNameFinder()
        self._total_deleted = 0

        self._setup_window()
        self._build_ui()
        self._apply_styles()

    # ──────────────────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1280, 800)

    # ──────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ───────────────────────────────────────────────
        root.addWidget(self._make_header())

        # ── Scan controls ────────────────────────────────────────────
        root.addWidget(self._make_scan_bar())

        # ── Global progress (scanner) ────────────────────────────────
        self._global_progress = QProgressBar()
        self._global_progress.setTextVisible(False)
        self._global_progress.setMaximumHeight(4)
        self._global_progress.hide()
        root.addWidget(self._global_progress)

        # ── Tabs ─────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(False)

        self._dup_tab  = DuplicateTab()
        self._name_tab = NameTab()

        self._tabs.addTab(self._dup_tab,  "🔍  Trùng lặp tuyệt đối")
        self._tabs.addTab(self._name_tab, "📋  Trùng tên khác đuôi")
        root.addWidget(self._tabs, 1)

        # Connect deleted signals to global counter
        self._dup_tab.files_deleted.connect(self._on_files_deleted)
        self._name_tab.files_deleted.connect(self._on_files_deleted)

        # ── Status bar ────────────────────────────────────────────────
        self._setup_statusbar()

    # ──────────────────────────────────────────────────────────────────
    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("AppHeader")
        header.setStyleSheet(
            f"QFrame#AppHeader {{"
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"  stop:0 #1e3a8a, stop:0.4 #2563eb, stop:1 #1e40af);"
            f"border-bottom: 2px solid #1d4ed8;"
            f"}}"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(14)

        # App icon / name
        logo = QLabel("🎬")
        logo.setStyleSheet("font-size: 28px; background: transparent; border: none;")

        app_name = QLabel(APP_NAME)
        app_name.setStyleSheet(
            f"color: #ffffff; font-size: 22px; font-weight: 800;"
            f"letter-spacing: 1px; background: transparent; border: none;"
        )

        tagline = QLabel("Media Deduplication & Cleanup Tool")
        tagline.setStyleSheet(
            f"color: rgba(255,255,255,0.7); font-size: 12px;"
            f"background: transparent; border: none;"
        )

        layout.addWidget(logo)
        layout.addWidget(app_name)
        layout.addWidget(tagline)
        layout.addStretch()

        # Trash info badge
        if is_send2trash_available():
            badge_text = "🛡  Xóa an toàn (Thùng rác)"
            badge_bg   = "rgba(255,255,255,0.15)"
            badge_fg   = "#bbf7d0"
        else:
            badge_text = "⚠  Xóa vĩnh viễn (cài send2trash)"
            badge_bg   = "rgba(255,255,255,0.15)"
            badge_fg   = "#fde68a"

        badge = QLabel(badge_text)
        badge.setStyleSheet(
            f"color: {badge_fg}; font-size: 11px; font-weight: 600;"
            f"background-color: {badge_bg}; border: 1px solid rgba(255,255,255,0.25);"
            f"border-radius: 12px; padding: 4px 12px;"
        )
        layout.addWidget(badge)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet(
            f"color: rgba(255,255,255,0.6); font-size: 11px;"
            f"background: transparent; border: none;"
        )
        layout.addWidget(ver)
        return header

    # ──────────────────────────────────────────────────────────────────
    def _make_scan_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("ScanBar")
        bar.setStyleSheet(
            f"QFrame#ScanBar {{"
            f"background-color: {COLOR_BG_PANEL};"
            f"border-bottom: 1px solid {COLOR_BORDER};"
            f"}}"
        )
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Row 1: folder picker
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        folder_icon = QLabel("📂")
        folder_icon.setStyleSheet(
            "font-size: 16px; background: transparent; border: none;"
        )
        row1.addWidget(folder_icon)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText(
            "Chọn thư mục cần quét…  (hoặc kéo thả thư mục vào đây)"
        )
        self._path_edit.setReadOnly(False)
        row1.addWidget(self._path_edit, 1)

        self._btn_browse = QPushButton("Chọn thư mục")
        self._btn_browse.setObjectName("btn_primary")
        self._btn_browse.setFixedWidth(130)
        self._btn_browse.clicked.connect(self._browse_folder)
        row1.addWidget(self._btn_browse)

        layout.addLayout(row1)

        # Row 2: options + scan button
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        # Recursive
        self._chk_recursive = QCheckBox("Quét đệ quy (bao gồm thư mục con)")
        self._chk_recursive.setChecked(True)
        row2.addWidget(self._chk_recursive)

        # Filter by type
        type_lbl = QLabel("Lọc loại:")
        type_lbl.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 12px;"
            f"background: transparent; border: none;"
        )
        row2.addWidget(type_lbl)

        self._type_combo = QComboBox()
        self._type_combo.setFixedWidth(150)
        self._type_combo.addItems([
            "Tất cả media",
            "Chỉ ảnh",
            "Chỉ video",
            "Chỉ audio",
        ])
        row2.addWidget(self._type_combo)

        row2.addStretch()

        # Scan + Stop buttons
        self._btn_scan = QPushButton("▶  Bắt đầu Quét")
        self._btn_scan.setObjectName("btn_primary")
        self._btn_scan.setFixedWidth(150)
        self._btn_scan.clicked.connect(self._start_scan)
        row2.addWidget(self._btn_scan)

        self._btn_stop = QPushButton("■  Dừng")
        self._btn_stop.setFixedWidth(80)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_scan)
        row2.addWidget(self._btn_stop)

        layout.addLayout(row2)
        return bar

    # ──────────────────────────────────────────────────────────────────
    def _setup_statusbar(self) -> None:
        sb = self.statusBar()
        sb.showMessage("Sẵn sàng.")

        self._sb_files = QLabel("Files: 0")
        self._sb_files.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        sb.addPermanentWidget(self._sb_files)

        self._sb_deleted = QLabel("Đã xóa: 0")
        self._sb_deleted.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 11px;")
        sb.addPermanentWidget(self._sb_deleted)

    # ──────────────────────────────────────────────────────────────────
    def _apply_styles(self) -> None:
        self.setStyleSheet(MAIN_STYLESHEET)

    # ──────────────────────────────────────────────────────────────────
    # Folder selection
    # ──────────────────────────────────────────────────────────────────
    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục cần quét",
            self._path_edit.text() or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self._path_edit.setText(folder)

    # ──────────────────────────────────────────────────────────────────
    # Scan lifecycle
    # ──────────────────────────────────────────────────────────────────
    def _selected_extensions(self) -> Set[str]:
        idx = self._type_combo.currentIndex()
        if idx == 1:
            return IMAGE_EXTENSIONS
        if idx == 2:
            return VIDEO_EXTENSIONS
        if idx == 3:
            return AUDIO_EXTENSIONS
        return ALL_MEDIA_EXTENSIONS

    def _start_scan(self) -> None:
        folder = self._path_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "Chưa chọn thư mục", "Vui lòng chọn thư mục cần quét.")
            return
        if not Path(folder).is_dir():
            QMessageBox.warning(self, "Thư mục không hợp lệ", f"'{folder}' không phải thư mục hợp lệ.")
            return

        self._btn_scan.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._global_progress.setRange(0, 0)
        self._global_progress.show()
        self.statusBar().showMessage("Đang quét tệp…")

        self._dup_tab.on_scan_started()
        self._name_tab.on_scan_started()

        self._scanner.start(
            root_dir   = folder,
            recursive  = self._chk_recursive.isChecked(),
            extensions = self._selected_extensions(),
            on_progress= self._on_scan_progress,
            on_finished= self._on_scan_finished,
            on_error   = self._on_scan_error,
        )

    def _stop_scan(self) -> None:
        self._scanner.stop()
        self._dup_finder.stop()
        self._name_finder.stop()
        self._on_scan_done()
        self.statusBar().showMessage("Đã dừng.")

    def _on_scan_done(self) -> None:
        self._btn_scan.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._global_progress.hide()

    # ──────────────────────────────────────────────────────────────────
    # Scanner signals
    # ──────────────────────────────────────────────────────────────────
    def _on_scan_progress(self, current: int, total: int, path: str) -> None:
        if total > 0:
            self._global_progress.setRange(0, total)
            self._global_progress.setValue(current)
        self.statusBar().showMessage(f"Quét: {Path(path).name if path else ''}  [{current}/{total}]")

    def _on_scan_finished(self, file_paths: List[str]) -> None:
        self._scan_files = file_paths
        self._sb_files.setText(f"Files: {len(file_paths)}")
        self.statusBar().showMessage(
            f"Quét xong: {len(file_paths)} file media. Đang phân tích…"
        )

        if not file_paths:
            QMessageBox.information(
                self, "Không tìm thấy",
                "Không tìm thấy file media nào trong thư mục đã chọn."
            )
            self._on_scan_done()
            return

        # Now launch both finders in parallel
        self._global_progress.setRange(0, 0)

        self._dup_finder.start(
            file_paths   = file_paths,
            on_progress  = self._dup_tab.on_progress,
            on_finished  = self._on_dup_finished,
            on_error     = self._dup_tab.on_error,
        )
        self._name_finder.start(
            file_paths   = file_paths,
            on_progress  = self._name_tab.on_progress,
            on_finished  = self._on_name_finished,
            on_error     = self._name_tab.on_error,
        )

        self._pending_finders = 2

    def _on_dup_finished(self, groups: Dict) -> None:
        self._dup_tab.on_finished(groups)
        self._pending_finders -= 1
        if self._pending_finders <= 0:
            self._on_all_finders_done()

    def _on_name_finished(self, groups: Dict) -> None:
        self._name_tab.on_finished(groups)
        self._pending_finders -= 1
        if self._pending_finders <= 0:
            self._on_all_finders_done()

    def _on_all_finders_done(self) -> None:
        self._on_scan_done()
        self.statusBar().showMessage("Phân tích hoàn tất. Sẵn sàng.")

    def _on_scan_error(self, message: str) -> None:
        self._dup_tab.on_error(message)
        self._name_tab.on_error(message)
        self._on_scan_done()
        QMessageBox.critical(self, "Lỗi quét", message)

    # ──────────────────────────────────────────────────────────────────
    def _on_files_deleted(self, count: int) -> None:
        self._total_deleted += count
        self._sb_deleted.setText(f"Đã xóa: {self._total_deleted}")

    # ──────────────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:
        self._scanner.stop()
        self._dup_finder.stop()
        self._name_finder.stop()
        super().closeEvent(event)
