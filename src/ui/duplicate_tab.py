"""
duplicate_tab.py - UI tab for Exact Duplicate Image/Media Finder.

Layout (horizontal split):
  LEFT  – scrollable grid of duplicate groups (cards with checkboxes)
  RIGHT – full-size preview panel for the currently selected file
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSplitter, QCheckBox, QMessageBox,
    QProgressBar, QSizePolicy, QSpacerItem, QGroupBox,
    QProgressDialog, QApplication
)

from src.core.file_manager import batch_move_to_trash, format_size, is_send2trash_available
from src.ui.preview_widget import PreviewWidget, ClickablePathLabel
from src.utils.constants import (
    COLOR_BG_PANEL, COLOR_BG_CARD, COLOR_BORDER, COLOR_DANGER,
    COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY, COLOR_ACCENT, COLOR_SUCCESS,
    COLOR_WARNING, PREVIEW_FULL_MAX_SIZE, PREVIEW_THUMB_SIZE,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File card inside a group
# ---------------------------------------------------------------------------

class _FileCard(QFrame):
    """A clickable card representing one file in a duplicate group."""

    clicked    = pyqtSignal(str)          # emits path
    check_changed = pyqtSignal(str, bool) # path, checked

    def __init__(self, path: str, is_keeper: bool = False) -> None:
        super().__init__()
        self.path = path
        self._is_keeper = is_keeper
        self._selected = False
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setFixedWidth(PREVIEW_THUMB_SIZE + 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Thumbnail
        self._preview = PreviewWidget(thumb_size=PREVIEW_THUMB_SIZE, show_info=False)
        self._preview.set_file(self.path)
        layout.addWidget(self._preview)

        # Filename
        p = Path(self.path)
        name = p.name
        if len(name) > 22:
            name = name[:10] + "…" + name[-10:]
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        # Size
        try:
            size_str = format_size(p.stat().st_size)
        except OSError:
            size_str = "?"
        size_lbl = QLabel(size_str)
        size_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        size_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(size_lbl)

        # Checkbox (delete this file?)
        cb_row = QHBoxLayout()
        cb_row.setContentsMargins(0, 0, 0, 0)
        if self._is_keeper:
            keeper_lbl = QLabel("✓ Giữ lại")
            keeper_lbl.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 11px; font-weight: 600;")
            keeper_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_row.addWidget(keeper_lbl)
            self._checkbox = None
        else:
            self._checkbox = QCheckBox("Xóa")
            self._checkbox.setStyleSheet(f"color: {COLOR_DANGER}; font-size: 11px;")
            self._checkbox.stateChanged.connect(self._on_check)
            cb_row.addWidget(self._checkbox)
        layout.addLayout(cb_row)

    # ------------------------------------------------------------------
    def _on_check(self, state: int) -> None:
        checked = state == Qt.CheckState.Checked.value
        self.check_changed.emit(self.path, checked)
        self._apply_style(marked=checked)

    def _apply_style(self, marked: bool = False) -> None:
        if marked:
            border = COLOR_DANGER
            bg = "#fff1f2"
        elif self._selected:
            border = COLOR_ACCENT
            bg = "#eff6ff"
        else:
            border = COLOR_BORDER
            bg = "#ffffff"
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1.5px solid {border};"
            f"border-radius: 8px; }}"
        )

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.path)
        super().mousePressEvent(event)

    @property
    def is_checked(self) -> bool:
        return bool(self._checkbox and self._checkbox.isChecked())

    def set_keeper(self, is_keeper: bool) -> None:
        self._is_keeper = is_keeper


# ---------------------------------------------------------------------------
# One duplicate group widget
# ---------------------------------------------------------------------------

class _GroupWidget(QFrame):
    """Horizontal row of _FileCard widgets for one duplicate group."""

    selection_changed = pyqtSignal(str)     # path of selected card
    delete_requested  = pyqtSignal(list)    # list of paths to delete

    def __init__(self, group_idx: int, hash_key: str, paths: List[str]) -> None:
        super().__init__()
        self.group_idx = group_idx
        self.hash_key  = hash_key
        self.paths     = paths
        self._cards: List[_FileCard] = []
        self._selected_path: str | None = None
        self._to_delete: set[str] = set()
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"QFrame {{ background-color: {COLOR_BG_PANEL}; "
            f"border: 1px solid {COLOR_BORDER}; border-radius: 10px; "
            f"box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(8)

        # Group header
        hdr = QHBoxLayout()
        idx_lbl = QLabel(f"Nhóm #{self.group_idx + 1}")
        idx_lbl.setStyleSheet(
            f"color: {COLOR_ACCENT}; font-weight: 700; font-size: 13px;"
        )
        cnt_lbl = QLabel(f"  ({len(self.paths)} bản sao)")
        cnt_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px;")

        # Total wasted space (all minus one original)
        try:
            sizes = [Path(p).stat().st_size for p in self.paths]
            wasted = sum(sorted(sizes)[:-1])
            waste_lbl = QLabel(f"  •  Có thể giải phóng: {format_size(wasted)}")
            waste_lbl.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 12px;")
        except Exception:
            waste_lbl = QLabel()

        hdr.addWidget(idx_lbl)
        hdr.addWidget(cnt_lbl)
        hdr.addWidget(waste_lbl)
        hdr.addStretch()

        btn_del = QPushButton("🗑  Xóa đã chọn")
        btn_del.setObjectName("btn_danger")
        btn_del.setFixedHeight(30)
        btn_del.clicked.connect(self._request_delete)
        hdr.addWidget(btn_del)

        outer.addLayout(hdr)

        # Cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)
        cards_row.setContentsMargins(0, 0, 0, 0)
        for i, path in enumerate(self.paths):
            card = _FileCard(path, is_keeper=(i == 0))
            card.clicked.connect(self._on_card_clicked)
            card.check_changed.connect(self._on_check_changed)
            self._cards.append(card)
            cards_row.addWidget(card)
        cards_row.addStretch()
        outer.addLayout(cards_row)

    # ------------------------------------------------------------------
    def _on_card_clicked(self, path: str) -> None:
        self._selected_path = path
        for card in self._cards:
            card.set_selected(card.path == path)
        self.selection_changed.emit(path)

    def _on_check_changed(self, path: str, checked: bool) -> None:
        if checked:
            self._to_delete.add(path)
        else:
            self._to_delete.discard(path)

    def _request_delete(self) -> None:
        if not self._to_delete:
            QMessageBox.information(
                self, "Chưa chọn", "Hãy đánh dấu ít nhất một bản sao cần xóa."
            )
            return
        self.delete_requested.emit(list(self._to_delete))

    # ------------------------------------------------------------------
    def paths_to_delete(self) -> List[str]:
        return list(self._to_delete)


# ---------------------------------------------------------------------------
# Main duplicate tab
# ---------------------------------------------------------------------------

class DuplicateTab(QWidget):
    """Tab widget for the Exact Duplicate finder feature."""

    # Emitted when files are actually deleted so parent can update status
    files_deleted = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._groups: Dict[str, List[str]] = {}
        self._group_widgets: List[_GroupWidget] = []
        self._selected_preview_path: str | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── toolbar ──────────────────────────────────────────────────
        toolbar = self._make_toolbar()
        root.addWidget(toolbar)

        # ── progress bar (hidden by default) ─────────────────────────
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setMaximumHeight(6)
        self._progress.hide()
        root.addWidget(self._progress)

        # ── status label ─────────────────────────────────────────────
        self._status_lbl = QLabel("Chưa quét. Chọn thư mục và nhấn Quét.")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.setContentsMargins(16, 8, 16, 4)
        root.addWidget(self._status_lbl)

        # ── main splitter: groups list | preview ─────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left: scrollable groups
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._groups_container = QWidget()
        self._groups_layout    = QVBoxLayout(self._groups_container)
        self._groups_layout.setContentsMargins(12, 12, 12, 12)
        self._groups_layout.setSpacing(12)
        self._groups_layout.addStretch()

        self._scroll_area.setWidget(self._groups_container)

        # Right: preview panel
        right_panel = self._make_right_panel()

        splitter.addWidget(self._scroll_area)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

        # ── bottom action bar ─────────────────────────────────────────
        bottom = self._make_bottom_bar()
        root.addWidget(bottom)

    # ------------------------------------------------------------------
    def _make_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background-color: {COLOR_BG_PANEL}; "
            f"border-bottom: 1px solid {COLOR_BORDER}; }}"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        title = QLabel("Tìm ảnh/file trùng lặp tuyệt đối")
        title.setObjectName("label_heading")
        title.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: 15px; font-weight: 700;"
            f"border: none; background: transparent;"
        )

        layout.addWidget(icon_lbl)
        layout.addWidget(title)
        layout.addStretch()

        self._btn_select_all = QPushButton("☑  Chọn tất cả bản sao")
        self._btn_select_all.clicked.connect(self._select_all_copies)
        self._btn_select_all.setEnabled(False)

        self._btn_clear_sel = QPushButton("☐  Bỏ chọn")
        self._btn_clear_sel.clicked.connect(self._clear_selections)
        self._btn_clear_sel.setEnabled(False)

        layout.addWidget(self._btn_select_all)
        layout.addWidget(self._btn_clear_sel)
        return bar

    # ------------------------------------------------------------------
    def _make_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(230)
        panel.setMaximumWidth(360)
        panel.setStyleSheet(
            f"QWidget {{ background-color: {COLOR_BG_CARD}; "
            f"border-left: 1px solid {COLOR_BORDER}; }}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(10)

        # Title row
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
        from PyQt6.QtWidgets import QFrame as _QFrame
        div = _QFrame()
        div.setFrameShape(_QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {COLOR_BORDER};")
        layout.addWidget(div)

        self._preview = PreviewWidget(
            thumb_size=PREVIEW_FULL_MAX_SIZE,
            show_info=True,
        )
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._preview)

        # Clickable file path label
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

        self._stats_lbl = QLabel("")
        self._stats_lbl.setObjectName("label_muted")
        layout.addWidget(self._stats_lbl)
        layout.addStretch()

        self._btn_delete_all = QPushButton("🗑  Xóa tất cả đã chọn")
        self._btn_delete_all.setObjectName("btn_danger")
        self._btn_delete_all.setEnabled(False)
        self._btn_delete_all.clicked.connect(self._delete_all_selected)
        layout.addWidget(self._btn_delete_all)

        return bar

    # ------------------------------------------------------------------
    # Public API called by MainWindow
    # ------------------------------------------------------------------

    def on_scan_started(self) -> None:
        self._progress.setRange(0, 0)
        self._progress.show()
        self._status_lbl.setText("Đang quét…")
        self._btn_select_all.setEnabled(False)
        self._btn_clear_sel.setEnabled(False)
        self._btn_delete_all.setEnabled(False)

    def on_progress(self, current: int, total: int, path: str) -> None:
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
        name = Path(path).name if path else ""
        self._status_lbl.setText(
            f"Đang phân tích: {name}  ({current}/{total})"
        )

    def on_finished(self, groups: Dict[str, List[str]]) -> None:
        self._progress.hide()
        self._groups = groups
        self._render_groups()
        total_files = sum(len(v) for v in groups.values())
        self._status_lbl.setText(
            f"Hoàn tất — {len(groups)} nhóm trùng lặp, "
            f"{total_files} file"
        )
        has = bool(groups)
        self._btn_select_all.setEnabled(has)
        self._btn_clear_sel.setEnabled(has)
        self._btn_delete_all.setEnabled(has)

    def on_error(self, message: str) -> None:
        self._progress.hide()
        self._status_lbl.setText(f"Lỗi: {message}")

    # ------------------------------------------------------------------
    def _render_groups(self) -> None:
        # Clear existing widgets
        while self._groups_layout.count() > 1:  # keep stretch
            item = self._groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._group_widgets.clear()

        if not self._groups:
            empty = QLabel("✅  Không tìm thấy file trùng lặp.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {COLOR_TEXT_MUTED}; font-size: 14px; padding: 40px;"
            )
            self._groups_layout.insertWidget(0, empty)
            return

        for idx, (hash_key, paths) in enumerate(self._groups.items()):
            gw = _GroupWidget(idx, hash_key, paths)
            gw.selection_changed.connect(self._on_card_selected)
            gw.delete_requested.connect(self._delete_paths)
            self._group_widgets.append(gw)
            self._groups_layout.insertWidget(
                self._groups_layout.count() - 1, gw
            )

        self._update_stats()

    # ------------------------------------------------------------------
    def _on_card_selected(self, path: str) -> None:
        self._selected_preview_path = path
        self._preview.set_file(path)
        self._path_lbl.set_path(path)

    # ------------------------------------------------------------------
    def _select_all_copies(self) -> None:
        """Check all non-keeper checkboxes."""
        for gw in self._group_widgets:
            for card in gw._cards:
                if not card._is_keeper and card._checkbox:
                    card._checkbox.setChecked(True)
        self._update_stats()

    def _clear_selections(self) -> None:
        for gw in self._group_widgets:
            for card in gw._cards:
                if card._checkbox:
                    card._checkbox.setChecked(False)
        self._update_stats()

    # ------------------------------------------------------------------
    def _delete_paths(self, paths: List[str]) -> None:
        """Confirm + delete a list of paths."""
        if not paths:
            return

        trash_note = (
            "Các file sẽ được chuyển vào Thùng rác."
            if is_send2trash_available()
            else "⚠️  send2trash không khả dụng — file sẽ bị XÓA VĨNH VIỄN!"
        )

        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa {len(paths)} file?\n\n{trash_note}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        progress = QProgressDialog("Đang chuẩn bị xóa...", "Hủy", 0, len(paths), self)
        progress.setWindowTitle("Xóa file")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def progress_callback(current: int, total: int, path_name: str) -> bool:
            progress.setValue(current)
            progress.setLabelText(f"Đang xóa...\n{path_name}")
            QApplication.processEvents()
            if progress.wasCanceled():
                return False
            return True

        ok, fail, errors = batch_move_to_trash(paths, progress_callback)
        progress.close()
        if errors:
            QMessageBox.warning(
                self,
                "Một số file không xóa được",
                "\n".join(errors[:10]),
            )

        # Update groups: remove deleted paths
        deleted_set = set(paths)
        new_groups: Dict[str, List[str]] = {}
        for h, ps in self._groups.items():
            remaining = [p for p in ps if p not in deleted_set]
            if len(remaining) >= 2:
                new_groups[h] = remaining
        self._groups = new_groups
        self._render_groups()
        self.files_deleted.emit(ok)
        self._status_lbl.setText(
            f"Đã xóa {ok} file.{(' Lỗi: ' + str(fail)) if fail else ''}"
        )

    def _delete_all_selected(self) -> None:
        to_delete = []
        for gw in self._group_widgets:
            to_delete.extend(gw.paths_to_delete())
        if not to_delete:
            QMessageBox.information(
                self, "Chưa chọn", "Hãy đánh dấu ít nhất một file cần xóa."
            )
            return
        self._delete_paths(to_delete)

    # ------------------------------------------------------------------
    def _update_stats(self) -> None:
        total_marked = sum(
            len(gw.paths_to_delete()) for gw in self._group_widgets
        )
        self._stats_lbl.setText(
            f"{len(self._groups)} nhóm  •  {total_marked} file đã chọn để xóa"
        )
