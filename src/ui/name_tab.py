"""
name_tab.py - UI tab for Same-Name-Different-Extension Finder.

Layout (horizontal splitter):
  LEFT   – toolbar, progress, status, QTreeWidget with groups, bottom bar
  RIGHT  – preview panel (shows the file selected in the tree)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFrame, QComboBox,
    QMessageBox, QProgressBar, QAbstractItemView,
    QHeaderView, QSplitter, QSizePolicy,
)

from src.core.file_manager import batch_move_to_trash, format_size, is_send2trash_available
from src.ui.preview_widget import PreviewWidget, ClickablePathLabel
from src.utils.constants import (
    COLOR_BG_PANEL, COLOR_BG_CARD, COLOR_BORDER,
    COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY,
    COLOR_ACCENT, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS,
    PREVIEW_FULL_MAX_SIZE,
)

logger = logging.getLogger(__name__)

# Column indices
COL_NAME = 0
COL_EXT  = 1
COL_SIZE = 2
COL_PATH = 3


def _ext_color(ext: str) -> str:
    if ext in IMAGE_EXTENSIONS:
        return COLOR_ACCENT
    if ext in VIDEO_EXTENSIONS:
        return COLOR_SUCCESS
    if ext in AUDIO_EXTENSIONS:
        return COLOR_WARNING
    return COLOR_TEXT_MUTED


class NameTab(QWidget):
    """Tab widget for the Same-Name-Different-Extension finder."""

    files_deleted = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._groups: Dict[str, List[str]] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────────────
        # Tree must be created FIRST so toolbar can connect signals to it
        self._tree = self._make_tree()

        root.addWidget(self._make_toolbar())

        # ── Progress bar ─────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setMaximumHeight(6)
        self._progress.hide()
        root.addWidget(self._progress)

        # ── Status label ─────────────────────────────────────────────
        self._status_lbl = QLabel("Chưa quét. Chọn thư mục và nhấn Quét.")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.setContentsMargins(16, 7, 16, 4)
        root.addWidget(self._status_lbl)

        # ── Main splitter: tree | preview ────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left side: tree widget in a container (so bottom bar stays below it)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self._tree, 1)
        left_layout.addWidget(self._make_bottom_bar())

        # Right side: preview panel
        right_panel = self._make_preview_panel()

        splitter.addWidget(left_container)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([780, 280])

        root.addWidget(splitter, 1)

        # Connect tree selection → preview
        self._tree.itemClicked.connect(self._on_tree_item_clicked)

    # ------------------------------------------------------------------
    def _make_tree(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setColumnCount(4)
        tree.setHeaderLabels(["Tên file", "Định dạng", "Kích thước", "Đường dẫn"])
        tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.setAlternatingRowColors(True)
        tree.setAnimated(True)
        tree.setRootIsDecorated(True)
        tree.setUniformRowHeights(False)
        tree.setStyleSheet(
            "QTreeWidget::item:alternate { background-color: #f8fafc; }"
        )
        hdr = tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        return tree

    # ------------------------------------------------------------------
    def _make_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background-color: {COLOR_BG_PANEL}; "
            f"border-bottom: 1px solid {COLOR_BORDER}; }}"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        icon_lbl = QLabel("📋")
        icon_lbl.setStyleSheet(
            "font-size: 20px; border: none; background: transparent;"
        )
        title = QLabel("Tìm file trùng tên khác đuôi")
        title.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: 15px; font-weight: 700;"
            f"border: none; background: transparent;"
        )

        layout.addWidget(icon_lbl)
        layout.addWidget(title)
        layout.addStretch()

        self._btn_expand = QPushButton("⊞  Mở rộng tất cả")
        self._btn_expand.clicked.connect(self._tree.expandAll)

        self._btn_collapse = QPushButton("⊟  Thu gọn tất cả")
        self._btn_collapse.clicked.connect(self._tree.collapseAll)

        layout.addWidget(self._btn_expand)
        layout.addWidget(self._btn_collapse)
        return bar

    # ------------------------------------------------------------------
    def _make_preview_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(360)
        panel.setStyleSheet(
            f"QWidget {{ background-color: {COLOR_BG_CARD}; "
            f"border-left: 1px solid {COLOR_BORDER}; }}"
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(10)

        # Section title
        title_row = QHBoxLayout()
        icon = QLabel("🖼")
        icon.setStyleSheet(
            "font-size: 16px; border: none; background: transparent;"
        )
        title = QLabel("Xem trước")
        title.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: 700;"
            f"text-transform: uppercase; letter-spacing: 1px;"
            f"border: none; background: transparent;"
        )
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {COLOR_BORDER};")
        layout.addWidget(div)

        # Preview widget
        self._preview = PreviewWidget(
            thumb_size=PREVIEW_FULL_MAX_SIZE,
            show_info=True,
        )
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._preview)

        # Extension badge
        self._ext_badge = QLabel()
        self._ext_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ext_badge.setStyleSheet(
            "background: transparent; border: none; font-size: 12px;"
        )
        layout.addWidget(self._ext_badge)

        # Clickable path label (click → open Explorer)
        self._path_lbl = ClickablePathLabel()
        layout.addWidget(self._path_lbl)
        layout.addStretch()

        return panel

    # ------------------------------------------------------------------
    def _make_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background-color: {COLOR_BG_PANEL}; "
            f"border-top: 1px solid {COLOR_BORDER}; }}"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Quick-delete by extension
        ext_label = QLabel("Xóa nhanh theo đuôi:")
        ext_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px;")

        self._ext_combo = QComboBox()
        self._ext_combo.setFixedWidth(100)
        self._ext_combo.setToolTip("Chọn định dạng muốn xóa khỏi tất cả các nhóm")

        self._btn_delete_ext = QPushButton("🗑  Xóa đuôi này")
        self._btn_delete_ext.setObjectName("btn_danger")
        self._btn_delete_ext.clicked.connect(self._delete_by_extension)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setObjectName("label_muted")

        layout.addWidget(ext_label)
        layout.addWidget(self._ext_combo)
        layout.addWidget(self._btn_delete_ext)
        layout.addSpacing(20)
        layout.addWidget(self._stats_lbl)
        layout.addStretch()

        self._btn_delete_sel = QPushButton("🗑  Xóa file đã chọn")
        self._btn_delete_sel.setObjectName("btn_danger")
        self._btn_delete_sel.clicked.connect(self._delete_selected)
        layout.addWidget(self._btn_delete_sel)

        return bar

    # ------------------------------------------------------------------
    # Tree item click → update preview
    # ------------------------------------------------------------------
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        path = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
        if not path:
            # Clicked a group header — clear preview
            self._preview.set_file(None)
            self._path_lbl.set_path(None)
            self._ext_badge.setText("")
            return

        # Update preview
        self._preview.set_file(path)
        self._path_lbl.set_path(path)

        # Extension badge with color
        ext = Path(path).suffix.lower()
        color = _ext_color(ext)
        self._ext_badge.setText(f"Định dạng: <b style='color:{color}'>{ext}</b>")



    # ------------------------------------------------------------------
    # Public API (called by MainWindow)
    # ------------------------------------------------------------------
    def on_scan_started(self) -> None:
        self._progress.setRange(0, 0)
        self._progress.show()
        self._status_lbl.setText("Đang quét…")

    def on_progress(self, current: int, total: int, path: str) -> None:
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
        name = Path(path).name if path else ""
        self._status_lbl.setText(f"Đang xử lý: {name}  ({current}/{total})")

    def on_finished(self, groups: Dict[str, List[str]]) -> None:
        self._progress.hide()
        self._groups = groups
        self._render_tree()
        total_files = sum(len(v) for v in groups.values())
        self._status_lbl.setText(
            f"Hoàn tất — {len(groups)} nhóm, {total_files} file"
        )

    def on_error(self, message: str) -> None:
        self._progress.hide()
        self._status_lbl.setText(f"Lỗi: {message}")

    # ------------------------------------------------------------------
    def _render_tree(self) -> None:
        self._tree.clear()
        self._ext_combo.clear()
        self._preview.set_file(None)
        self._path_lbl.set_path(None)
        self._ext_badge.setText("")

        if not self._groups:
            item = QTreeWidgetItem(["✅  Không tìm thấy file trùng tên khác đuôi."])
            item.setForeground(0, QBrush(QColor(COLOR_TEXT_MUTED)))
            self._tree.addTopLevelItem(item)
            return

        all_exts: set[str] = set()

        for stem, paths in sorted(self._groups.items()):
            # Group root item
            root_item = QTreeWidgetItem()
            root_item.setText(COL_NAME, f"📁  {stem}")
            root_item.setText(COL_EXT, f"{len(paths)} định dạng")
            root_item.setFont(COL_NAME, QFont("Segoe UI", 12, QFont.Weight.Bold))
            root_item.setForeground(COL_NAME, QBrush(QColor(COLOR_TEXT_PRIMARY)))
            root_item.setForeground(COL_EXT, QBrush(QColor(COLOR_TEXT_MUTED)))
            root_item.setData(COL_NAME, Qt.ItemDataRole.UserRole, None)  # group marker

            # Child items — one per file
            for p in paths:
                path_obj = Path(p)
                ext = path_obj.suffix.lower()
                all_exts.add(ext)

                try:
                    size_str = format_size(path_obj.stat().st_size)
                except OSError:
                    size_str = "?"

                child = QTreeWidgetItem(root_item)
                child.setText(COL_NAME, path_obj.name)
                child.setText(COL_EXT, ext)
                child.setText(COL_SIZE, size_str)
                child.setText(COL_PATH, p)
                child.setData(COL_NAME, Qt.ItemDataRole.UserRole, p)

                color = _ext_color(ext)
                child.setForeground(COL_EXT, QBrush(QColor(color)))
                child.setForeground(COL_NAME, QBrush(QColor(COLOR_TEXT_PRIMARY)))
                child.setForeground(COL_SIZE, QBrush(QColor(COLOR_TEXT_MUTED)))
                child.setForeground(COL_PATH, QBrush(QColor(COLOR_TEXT_MUTED)))
                child.setCheckState(COL_NAME, Qt.CheckState.Unchecked)

            self._tree.addTopLevelItem(root_item)

        self._tree.expandAll()

        for ext in sorted(all_exts):
            self._ext_combo.addItem(ext)

        self._update_stats()

    # ------------------------------------------------------------------
    def _get_checked_paths(self) -> List[str]:
        paths = []
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            group = root.child(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.checkState(COL_NAME) == Qt.CheckState.Checked:
                    p = child.data(COL_NAME, Qt.ItemDataRole.UserRole)
                    if p:
                        paths.append(p)
        return paths

    def _get_selected_paths(self) -> List[str]:
        paths = []
        for item in self._tree.selectedItems():
            p = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
            if p:
                paths.append(p)
        return paths

    # ------------------------------------------------------------------
    def _delete_by_extension(self) -> None:
        ext = self._ext_combo.currentText().strip()
        if not ext:
            return

        to_delete: List[str] = []
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            group = root.child(i)
            if group.childCount() <= 1:
                continue
            for j in range(group.childCount()):
                child = group.child(j)
                if child.text(COL_EXT) == ext:
                    p = child.data(COL_NAME, Qt.ItemDataRole.UserRole)
                    if p:
                        to_delete.append(p)

        if not to_delete:
            QMessageBox.information(
                self, "Không tìm thấy",
                f"Không có file nào với đuôi {ext} trong các nhóm trùng."
            )
            return

        self._confirm_and_delete(
            to_delete,
            f"Xóa tất cả {len(to_delete)} file '{ext}'?"
        )

    def _delete_selected(self) -> None:
        paths = self._get_selected_paths()
        if not paths:
            paths = self._get_checked_paths()
        if not paths:
            QMessageBox.information(
                self, "Chưa chọn",
                "Hãy chọn (click) hoặc đánh dấu checkbox các file cần xóa."
            )
            return
        self._confirm_and_delete(paths, f"Xóa {len(paths)} file đã chọn?")

    # ------------------------------------------------------------------
    def _confirm_and_delete(self, paths: List[str], question: str) -> None:
        trash_note = (
            "Các file sẽ được chuyển vào Thùng rác."
            if is_send2trash_available()
            else "⚠️  send2trash không khả dụng — file sẽ bị XÓA VĨNH VIỄN!"
        )
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"{question}\n\n{trash_note}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, fail, errors = batch_move_to_trash(paths)
        if errors:
            QMessageBox.warning(self, "Lỗi", "\n".join(errors[:10]))

        # Refresh
        deleted_set = set(paths)
        new_groups: Dict[str, List[str]] = {}
        for stem, ps in self._groups.items():
            remaining = [p for p in ps if p not in deleted_set]
            exts = {Path(p).suffix.lower() for p in remaining}
            if len(exts) >= 2:
                new_groups[stem] = remaining
        self._groups = new_groups
        self._render_tree()

        self.files_deleted.emit(ok)
        self._status_lbl.setText(
            f"Đã xóa {ok} file.{(' Lỗi: ' + str(fail)) if fail else ''}"
        )

    # ------------------------------------------------------------------
    def _update_stats(self) -> None:
        self._stats_lbl.setText(
            f"{len(self._groups)} nhóm  •  "
            f"{sum(len(v) for v in self._groups.values())} file"
        )
