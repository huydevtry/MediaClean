"""
name_finder.py - Detect media files with the same stem but different extensions.

Example: photo.jpg + photo.png  →  one group keyed by "photo"
         video.mp4  + video.mov →  one group keyed by "video"
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)

# Type alias: stem -> list of absolute path strings (>= 2 different extensions)
SameNameGroups = Dict[str, List[str]]


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------

def find_same_name_different_ext(file_paths: List[str]) -> SameNameGroups:
    """
    Group *file_paths* by lowercase stem; keep only groups where ≥ 2
    distinct extensions are present.

    Returns {stem: [paths…]}.
    """
    by_stem: Dict[str, List[str]] = defaultdict(list)
    for p in file_paths:
        path = Path(p)
        stem = path.stem.lower()
        by_stem[stem].append(p)

    groups: SameNameGroups = {}
    for stem, paths in by_stem.items():
        # Check that at least 2 distinct extensions exist in the group
        exts = {Path(p).suffix.lower() for p in paths}
        if len(exts) >= 2:
            groups[stem] = sorted(paths)

    logger.info("Same-name groups found: %d", len(groups))
    return groups


# ---------------------------------------------------------------------------
# QThread worker
# ---------------------------------------------------------------------------

class SameNameFinderWorker(QObject):
    """
    Signals:
        progress(current, total, current_path)
        finished(groups)   – dict {stem: [paths]}
        error(message)
    """

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, file_paths: List[str]) -> None:
        super().__init__()
        self.file_paths = file_paths
        self._abort = False

    def abort(self) -> None:
        self._abort = True

    def run(self) -> None:
        try:
            total = len(self.file_paths)
            by_stem: Dict[str, List[str]] = defaultdict(list)

            for idx, p in enumerate(self.file_paths):
                if self._abort:
                    self.finished.emit({})
                    return
                path = Path(p)
                by_stem[path.stem.lower()].append(p)
                if idx % 300 == 0 or idx == total - 1:
                    self.progress.emit(idx + 1, total, p)

            groups: SameNameGroups = {}
            for stem, paths in by_stem.items():
                exts = {Path(p).suffix.lower() for p in paths}
                if len(exts) >= 2:
                    groups[stem] = sorted(paths)

            self.finished.emit(groups)
        except Exception as exc:
            logger.exception("SameNameFinder crashed")
            self.error.emit(str(exc))


class SameNameFinder:
    """Manages the QThread for same-name-different-ext detection."""

    def __init__(self) -> None:
        self._thread: QThread | None = None
        self._worker: SameNameFinderWorker | None = None

    def start(
        self,
        file_paths: List[str],
        on_progress,
        on_finished,
        on_error,
    ) -> None:
        self.stop()

        self._worker = SameNameFinderWorker(file_paths)
        self._thread = QThread()

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)

        self._worker.progress.connect(on_progress)
        self._worker.finished.connect(on_finished)
        self._worker.error.connect(on_error)

        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)

        self._thread.start()

    def stop(self) -> None:
        if self._worker:
            self._worker.abort()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)

    def _cleanup(self) -> None:
        self._thread = None
        self._worker = None
