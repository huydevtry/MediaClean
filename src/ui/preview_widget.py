"""
preview_widget.py - Reusable image/media preview panel.

THREAD-SAFETY: QPixmap must only be created on the main (GUI) thread.
The background _ThumbLoader emits a QImage (which IS thread-safe), and the
main thread converts it to QPixmap inside _on_image_ready.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont, QImage, QCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSizePolicy, QFrame,
)

from src.utils.constants import (
    PREVIEWABLE_IMAGE_EXTENSIONS,
    COLOR_BG_PANEL, COLOR_BG_CARD, COLOR_TEXT_MUTED, COLOR_BORDER,
    COLOR_ACCENT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    VIDEO_EXTENSIONS, AUDIO_EXTENSIONS,
)
from src.core.file_manager import format_size

logger = logging.getLogger(__name__)

# RAW extensions supported by rawpy
RAW_EXTENSIONS = {
    ".arw", ".cr2", ".cr3", ".nef", ".orf", ".raf", ".rw2",
    ".pef", ".srw", ".x3f", ".dng", ".raw",
}

try:
    import rawpy as _rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False
    logger.info("rawpy not installed — RAW files will show icon badge")


# ---------------------------------------------------------------------------
# Helper: open Explorer and highlight a file
# ---------------------------------------------------------------------------

def _open_in_explorer(path: str) -> None:
    try:
        subprocess.Popen(f'explorer /select,"{path}"')
    except Exception as exc:
        logger.warning("Cannot open Explorer for %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Background loader — emits QImage (thread-safe, NOT QPixmap)
# ---------------------------------------------------------------------------

class _ThumbLoader(QObject):
    """Loads an image file in a background thread.
    Emits a QImage (bytes-level, thread-safe). The caller converts to QPixmap
    on the main thread."""

    ready = pyqtSignal(QImage)   # ← QImage, NOT QPixmap

    def __init__(self, path: str, max_dim: int) -> None:
        super().__init__()
        self.path    = path
        self.max_dim = max_dim

    def run(self) -> None:
        qimg = _load_qimage(self.path, self.max_dim)
        self.ready.emit(qimg)


def _load_qimage(path: str, max_dim: int) -> QImage:
    """
    Load image from disk and return a QImage.
    QImage is safe to construct in any thread; QPixmap is NOT.
    Returns a null QImage on failure.
    """
    ext = Path(path).suffix.lower()

    # ── RAW files via rawpy ───────────────────────────────────────────
    if ext in RAW_EXTENSIONS and RAWPY_AVAILABLE:
        try:
            import rawpy, numpy as np
            with rawpy.imread(path) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=True,        # 2× faster decode
                    no_auto_bright=False,
                    output_bps=8,
                )
            h, w, ch = rgb.shape
            # Make a copy so the numpy array lives past the rawpy context
            data = rgb.tobytes()
            qimg = QImage(data, w, h, w * ch, QImage.Format.Format_RGB888)
            qimg = qimg.copy()            # detach from buffer
            if max_dim:
                qimg = qimg.scaled(
                    max_dim, max_dim,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            return qimg
        except Exception as exc:
            logger.debug("rawpy failed for %s: %s", path, exc)
            return QImage()   # null → badge fallback

    # ── Standard images via Pillow ────────────────────────────────────
    if ext in PREVIEWABLE_IMAGE_EXTENSIONS:
        try:
            from PIL import Image
            img = Image.open(path)
            if max_dim:
                img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
            return qimg.copy()   # detach from buffer
        except Exception as exc:
            logger.debug("Pillow failed for %s: %s", path, exc)

    return QImage()   # null


# ---------------------------------------------------------------------------
# Badge pixmap helper — MUST be called on the main thread
# ---------------------------------------------------------------------------

def _make_icon_pixmap(label: str, color: str, size: int) -> QPixmap:
    """Draw a circular badge. Call only from the main/GUI thread."""
    size = max(size, 40)
    px = QPixmap(size, size)
    px.fill(QColor("#f8fafc"))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size // 7
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    font = QFont("Segoe UI", max(7, size // 7), QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    return px


# ---------------------------------------------------------------------------
# Public widget
# ---------------------------------------------------------------------------

class PreviewWidget(QFrame):
    """
    Self-contained preview panel for one media file.

    show_info=False  →  fixed-size thumbnail card (duplicate group cards)
    show_info=True   →  responsive full-preview (expands, rescales on resize,
                        clickable path label)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        thumb_size: int = 160,
        show_info: bool = True,
    ) -> None:
        super().__init__(parent)
        self._thumb_size      = thumb_size
        self._show_info       = show_info
        self._current_path:   str | None     = None
        self._current_pixmap: QPixmap | None = None   # stored for rescaling
        self._thread:         QThread | None = None
        self._loader:         _ThumbLoader | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setObjectName("PreviewCard")
        self.setStyleSheet(
            f"QFrame#PreviewCard {{"
            f"background-color: {COLOR_BG_PANEL};"
            f"border: 1.5px solid {COLOR_BORDER};"
            f"border-radius: 10px;"
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._thumb_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setScaledContents(False)

        if self._show_info:
            self._thumb_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._thumb_label.setMinimumSize(80, 80)
        else:
            self._thumb_label.setFixedSize(self._thumb_size, self._thumb_size)

        layout.addWidget(self._thumb_label, stretch=1)

        if self._show_info:
            self._name_label = QLabel()
            self._name_label.setObjectName("label_muted")
            self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._name_label.setWordWrap(True)

            self._size_label = QLabel()
            self._size_label.setObjectName("label_muted")
            self._size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(self._name_label)
            layout.addWidget(self._size_label)

        self._clear_thumb()

    # ------------------------------------------------------------------
    # Rescale on resize
    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._show_info:
            self._repaint_pixmap()

    def _repaint_pixmap(self) -> None:
        if not self._current_pixmap or self._current_pixmap.isNull():
            return
        avail = self._thumb_label.size()
        if avail.width() < 1 or avail.height() < 1:
            return
        scaled = self._current_pixmap.scaled(
            avail.width(), avail.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumb_label.setPixmap(scaled)

    # ------------------------------------------------------------------
    def set_file(self, path: str | None) -> None:
        # Cancel any in-flight load
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(500)

        self._current_path   = path
        self._current_pixmap = None

        if path is None:
            self._clear_thumb()
            return

        p   = Path(path)
        ext = p.suffix.lower()

        if self._show_info:
            name = p.name
            if len(name) > 30:
                name = name[:13] + "…" + name[-13:]
            self._name_label.setText(name)
            try:
                self._size_label.setText(format_size(p.stat().st_size))
            except OSError:
                self._size_label.setText("—")

        if ext in PREVIEWABLE_IMAGE_EXTENSIONS or ext in RAW_EXTENSIONS:
            self._load_async(path)
        elif ext in VIDEO_EXTENSIONS:
            self._show_badge("VIDEO", COLOR_ACCENT)
        elif ext in AUDIO_EXTENSIONS:
            self._show_badge("AUDIO", COLOR_SUCCESS)
        else:
            self._show_badge("FILE", COLOR_TEXT_MUTED)

    # ------------------------------------------------------------------
    def _load_async(self, path: str) -> None:
        """Start background load; worker emits QImage, main thread converts."""
        self._thumb_label.clear()
        self._thumb_label.setText("⏳")
        self._thumb_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 22px; background: transparent;"
        )

        decode_size = max(self._thumb_size, 900)

        self._thread = QThread()
        self._loader = _ThumbLoader(path, decode_size)
        self._loader.moveToThread(self._thread)

        self._thread.started.connect(self._loader.run)
        self._loader.ready.connect(self._on_image_ready)    # QImage signal
        self._loader.ready.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        self._thread.start()

    def _on_image_ready(self, qimg: QImage) -> None:
        """Called on the main thread — safe to create QPixmap here."""
        self._thumb_label.setText("")
        self._thumb_label.setStyleSheet("")

        if qimg.isNull():
            # Fallback badge: show extension name
            ext   = Path(self._current_path).suffix.upper().lstrip(".") if self._current_path else "?"
            label = ext[:5] if ext else "ERR"
            self._show_badge(label, COLOR_WARNING)
            return

        # Convert QImage → QPixmap here on the main thread ✓
        px = QPixmap.fromImage(qimg)
        self._current_pixmap = px

        if self._show_info:
            self._repaint_pixmap()
        else:
            self._thumb_label.setPixmap(
                px.scaled(
                    self._thumb_size, self._thumb_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def _cleanup_thread(self) -> None:
        self._thread  = None
        self._loader  = None

    # ------------------------------------------------------------------
    def _show_badge(self, label: str, color: str) -> None:
        size = self._thumb_size if not self._show_info else 110
        px   = _make_icon_pixmap(label, color, size)
        self._current_pixmap = px
        self._thumb_label.setStyleSheet("")
        self._thumb_label.setText("")
        self._thumb_label.setPixmap(px)

    def _clear_thumb(self) -> None:
        self._current_pixmap = None
        size = self._thumb_size if not self._show_info else 80
        px   = _make_icon_pixmap("—", "#94a3b8", size)
        self._thumb_label.setStyleSheet("")
        self._thumb_label.setText("")
        self._thumb_label.setPixmap(px)
        if self._show_info:
            self._name_label.setText("Chưa chọn")
            self._size_label.setText("")

    # ------------------------------------------------------------------
    @property
    def current_path(self) -> str | None:
        return self._current_path


# ---------------------------------------------------------------------------
# Clickable path label — opens containing folder in Explorer
# ---------------------------------------------------------------------------

class ClickablePathLabel(QLabel):
    """
    Label showing a file path that opens the containing folder in Explorer
    when clicked.  Styled as a blue hyperlink.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._path: str | None = None
        self.setWordWrap(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style(has_path=False)

    def set_path(self, path: str | None) -> None:
        self._path = path
        if path:
            display = str(path)
            if len(display) > 70:
                display = "…" + display[-65:]
            self.setText(f"📄 {display}")
            self._apply_style(has_path=True)
            self.setToolTip(f"Click để mở thư mục chứa:\n{path}")
        else:
            self.setText("—")
            self._apply_style(has_path=False)
            self.setToolTip("")

    def _apply_style(self, has_path: bool) -> None:
        if has_path:
            self.setStyleSheet(
                f"color: {COLOR_ACCENT}; font-size: 10px;"
                f"text-decoration: underline;"
                f"background: transparent; border: none;"
            )
        else:
            self.setStyleSheet(
                f"color: {COLOR_TEXT_MUTED}; font-size: 10px;"
                f"background: transparent; border: none;"
            )

    def mousePressEvent(self, event) -> None:
        if self._path and event.button() == Qt.MouseButton.LeftButton:
            _open_in_explorer(self._path)
        super().mousePressEvent(event)
