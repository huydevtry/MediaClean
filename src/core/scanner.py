"""
scanner.py - Filesystem walker that emits progress signals.

Runs inside a QThread so the UI stays responsive during long scans.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Set

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.utils.constants import ALL_MEDIA_EXTENSIONS

logger = logging.getLogger(__name__)


class ScanWorker(QObject):
    """
    Worker object that scans a directory tree for media files.

    Signals:
        progress(current, total, current_path)
        finished(file_list)
        error(message)
    """

    progress = pyqtSignal(int, int, str)   # current, total, path
    finished = pyqtSignal(list)            # list of absolute path strings
    error    = pyqtSignal(str)

    def __init__(
        self,
        root_dir: str,
        recursive: bool = True,
        extensions: Set[str] | None = None,
    ) -> None:
        super().__init__()
        self.root_dir   = root_dir
        self.recursive  = recursive
        self.extensions = extensions or ALL_MEDIA_EXTENSIONS
        self._abort     = False

    # ------------------------------------------------------------------
    def abort(self) -> None:
        self._abort = True

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Entry point called by QThread.started signal."""
        try:
            found: List[str] = []
            root = Path(self.root_dir)

            if not root.exists():
                self.error.emit(f"Thư mục không tồn tại: {self.root_dir}")
                return

            # First pass: collect all candidate paths (for progress total)
            logger.info("Starting scan in: %s", root)
            self.progress.emit(0, 0, "Đang lập danh sách tệp…")

            all_paths: List[Path] = []
            walker = root.rglob("*") if self.recursive else root.glob("*")
            for entry in walker:
                if self._abort:
                    self.finished.emit([])
                    return
                if entry.is_file() and entry.suffix.lower() in self.extensions:
                    all_paths.append(entry)

            total = len(all_paths)
            logger.info("Candidate media files found: %d", total)

            for idx, path in enumerate(all_paths):
                if self._abort:
                    self.finished.emit([])
                    return
                self.progress.emit(idx + 1, total, str(path))
                found.append(str(path))

            self.finished.emit(found)

        except Exception as exc:
            logger.exception("Scan worker crashed")
            self.error.emit(str(exc))


class Scanner:
    """
    Convenience wrapper that manages QThread lifetime.

    Usage:
        scanner = Scanner(parent_qobject)
        scanner.start(root_dir, on_progress, on_finished, on_error)
    """

    def __init__(self) -> None:
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None

    # ------------------------------------------------------------------
    def start(
        self,
        root_dir: str,
        recursive: bool,
        extensions: Set[str] | None,
        on_progress,
        on_finished,
        on_error,
    ) -> None:
        self.stop()  # cancel any running scan

        self._worker = ScanWorker(root_dir, recursive, extensions)
        self._thread = QThread()

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)

        self._worker.progress.connect(on_progress)
        self._worker.finished.connect(on_finished)
        self._worker.error.connect(on_error)

        # Cleanup: quit thread when worker finishes
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)

        self._thread.start()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        if self._worker:
            self._worker.abort()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)

    # ------------------------------------------------------------------
    def _cleanup(self) -> None:
        self._thread = None
        self._worker = None
