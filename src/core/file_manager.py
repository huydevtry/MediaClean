"""
file_manager.py - Safe file operations (move to Recycle Bin / Trash).

Uses send2trash so that deleted files are recoverable.  Falls back to a
permanent delete ONLY if send2trash is not available AND the user has
explicitly acknowledged the risk (controlled by the caller).
"""
from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from typing import List, Tuple

try:
    from send2trash import send2trash as _send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    SEND2TRASH_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def move_to_trash(path: str | Path) -> Tuple[bool, str]:
    """
    Move *path* to the system Recycle Bin / Trash.

    Returns:
        (success: bool, message: str)
    """
    path = Path(path)

    if not path.exists():
        return False, f"File không tồn tại: {path}"

    if SEND2TRASH_AVAILABLE:
        try:
            _send2trash(str(path))
            logger.info("Moved to trash: %s", path)
            return True, f"Đã chuyển vào Thùng rác: {path.name}"
        except Exception as exc:
            logger.error("send2trash failed for %s: %s", path, exc)
            return False, f"Không thể chuyển vào Thùng rác: {exc}"
    else:
        # Fallback: permanent delete (caller must confirm separately)
        try:
            path.unlink()
            logger.warning("Permanently deleted (send2trash unavailable): %s", path)
            return True, f"Đã xóa vĩnh viễn (send2trash không khả dụng): {path.name}"
        except Exception as exc:
            logger.error("Permanent delete failed for %s: %s", path, exc)
            return False, f"Xóa thất bại: {exc}"


def batch_move_to_trash(paths: List[str | Path]) -> Tuple[int, int, List[str]]:
    """
    Move multiple files to trash.

    Returns:
        (success_count, fail_count, error_messages)
    """
    success = 0
    fail = 0
    errors: List[str] = []

    for p in paths:
        ok, msg = move_to_trash(p)
        if ok:
            success += 1
        else:
            fail += 1
            errors.append(msg)

    return success, fail, errors


def format_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_file_info(path: str | Path) -> dict:
    """Return a dict with common metadata for *path*."""
    path = Path(path)
    try:
        stat = path.stat()
        return {
            "name": path.name,
            "stem": path.stem,
            "suffix": path.suffix.lower(),
            "size": stat.st_size,
            "size_str": format_size(stat.st_size),
            "modified": stat.st_mtime,
            "path": str(path),
        }
    except OSError as exc:
        logger.error("Cannot stat %s: %s", path, exc)
        return {}


def is_send2trash_available() -> bool:
    return SEND2TRASH_AVAILABLE
