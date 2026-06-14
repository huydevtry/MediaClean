"""
duplicate_finder.py - Exact duplicate detection via content hashing.

Algorithm:
  1. Quick-filter by file size (files with unique sizes are never duplicates).
  2. For size-collision groups, compute a partial hash (first 64 KB) to
     eliminate near-misses cheaply.
  3. Full hash only for files surviving step 2.

This gives good performance even on very large files.
"""
from __future__ import annotations

import hashlib
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.utils.constants import HASH_CHUNK_SIZE

logger = logging.getLogger(__name__)

# Type alias: hash_str -> list of absolute path strings
DuplicateGroups = Dict[str, List[str]]


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def _file_hash(path: str, partial: bool = False) -> str | None:
    """
    Return hex digest for *path*.

    If *partial* is True, only the first HASH_CHUNK_SIZE bytes are hashed
    (used as a cheap pre-filter).
    """
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            if partial:
                h.update(f.read(HASH_CHUNK_SIZE))
            else:
                while chunk := f.read(HASH_CHUNK_SIZE):
                    h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError) as exc:
        logger.warning("Cannot hash %s: %s", path, exc)
        return None


def find_exact_duplicates(file_paths: List[str]) -> DuplicateGroups:
    """
    Pure function – find exact duplicates among *file_paths*.

    Returns a dict mapping full-hash → [paths…] where len(paths) >= 2.
    """
    # Step 1: group by size
    by_size: Dict[int, List[str]] = defaultdict(list)
    for p in file_paths:
        try:
            by_size[os.path.getsize(p)].append(p)
        except OSError:
            pass

    # Candidates: only files that share a size with at least one other
    candidates = [p for paths in by_size.values() if len(paths) > 1 for p in paths]
    logger.debug("After size filter: %d candidates", len(candidates))

    # Step 2: partial hash
    by_partial: Dict[str, List[str]] = defaultdict(list)
    for p in candidates:
        h = _file_hash(p, partial=True)
        if h:
            by_partial[h].append(p)

    candidates2 = [p for paths in by_partial.values() if len(paths) > 1 for p in paths]
    logger.debug("After partial-hash filter: %d candidates", len(candidates2))

    # Step 3: full hash
    by_full: Dict[str, List[str]] = defaultdict(list)
    for p in candidates2:
        h = _file_hash(p, partial=False)
        if h:
            by_full[h].append(p)

    duplicates = {h: paths for h, paths in by_full.items() if len(paths) > 1}
    logger.info("Duplicate groups found: %d", len(duplicates))
    return duplicates


# ---------------------------------------------------------------------------
# QThread worker wrapper
# ---------------------------------------------------------------------------

class DuplicateFinderWorker(QObject):
    """
    Signals:
        progress(current, total, current_path)
        finished(groups)   – groups is a dict {hash: [paths]}
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
            # --- Step 1: group by size ---
            self.progress.emit(0, len(self.file_paths), "Phân nhóm theo kích thước…")
            by_size: Dict[int, List[str]] = defaultdict(list)
            for idx, p in enumerate(self.file_paths):
                if self._abort:
                    self.finished.emit({})
                    return
                try:
                    by_size[os.path.getsize(p)].append(p)
                except OSError:
                    pass
                if idx % 200 == 0:
                    self.progress.emit(idx, len(self.file_paths), p)

            candidates = [
                p for paths in by_size.values() if len(paths) > 1 for p in paths
            ]

            # --- Step 2: partial hash ---
            self.progress.emit(0, len(candidates), "Tính hash sơ bộ (64 KB)…")
            by_partial: Dict[str, List[str]] = defaultdict(list)
            for idx, p in enumerate(candidates):
                if self._abort:
                    self.finished.emit({})
                    return
                h = _file_hash(p, partial=True)
                if h:
                    by_partial[h].append(p)
                self.progress.emit(idx + 1, len(candidates), p)

            candidates2 = [
                p for paths in by_partial.values() if len(paths) > 1 for p in paths
            ]

            # --- Step 3: full hash ---
            self.progress.emit(0, len(candidates2), "Tính hash đầy đủ…")
            by_full: Dict[str, List[str]] = defaultdict(list)
            for idx, p in enumerate(candidates2):
                if self._abort:
                    self.finished.emit({})
                    return
                h = _file_hash(p, partial=False)
                if h:
                    by_full[h].append(p)
                self.progress.emit(idx + 1, len(candidates2), p)

            duplicates = {h: paths for h, paths in by_full.items() if len(paths) > 1}
            self.finished.emit(duplicates)

        except Exception as exc:
            logger.exception("DuplicateFinder crashed")
            self.error.emit(str(exc))


class DuplicateFinder:
    """Manages the QThread for duplicate detection."""

    def __init__(self) -> None:
        self._thread: QThread | None = None
        self._worker: DuplicateFinderWorker | None = None

    def start(
        self,
        file_paths: List[str],
        on_progress,
        on_finished,
        on_error,
    ) -> None:
        self.stop()

        self._worker = DuplicateFinderWorker(file_paths)
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
