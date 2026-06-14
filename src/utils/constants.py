"""
constants.py - Global constants and configuration for MediaClean
"""

APP_NAME = "MediaClean"
APP_VERSION = "1.0.0"
APP_AUTHOR = "MediaClean Dev"

# --------------------------------------------------------------------------
# Supported media extensions (lowercase, with leading dot)
# --------------------------------------------------------------------------
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif",
    ".heic", ".heif", ".raw", ".cr2", ".nef", ".arw", ".dng", ".orf",
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".m4v", ".webm",
    ".3gp", ".ts", ".mts", ".m2ts",
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus",
    ".aiff", ".aif",
}

ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Extensions that support inline thumbnail preview via Pillow
PREVIEWABLE_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif",
}

# --------------------------------------------------------------------------
# Hashing configuration
# --------------------------------------------------------------------------
HASH_ALGORITHM = "md5"          # "md5" or "sha256"
HASH_CHUNK_SIZE = 65_536         # 64 KB read chunk for streaming hash

# --------------------------------------------------------------------------
# UI / layout defaults
# --------------------------------------------------------------------------
WINDOW_MIN_WIDTH  = 1_100
WINDOW_MIN_HEIGHT = 700
PREVIEW_THUMB_SIZE    = 160      # px, square thumbnail in duplicate view
PREVIEW_FULL_MAX_SIZE = 460      # px, max dimension for full preview panel

# --------------------------------------------------------------------------
# Colours used across stylesheets (LIGHT theme)
# --------------------------------------------------------------------------
COLOR_BG_DARK      = "#f0f4f8"   # main window / outer background
COLOR_BG_PANEL     = "#ffffff"   # panels, cards, dialogs
COLOR_BG_CARD      = "#f8fafc"   # secondary card surfaces
COLOR_ACCENT       = "#2563eb"   # primary blue
COLOR_ACCENT_HOVER = "#1d4ed8"   # darker blue on hover
COLOR_DANGER       = "#dc2626"   # red for delete actions
COLOR_DANGER_HOVER = "#b91c1c"
COLOR_SUCCESS      = "#16a34a"   # green
COLOR_WARNING      = "#d97706"   # amber
COLOR_TEXT_PRIMARY = "#1e293b"   # near-black text
COLOR_TEXT_MUTED   = "#64748b"   # secondary / helper text
COLOR_BORDER       = "#e2e8f0"   # subtle divider lines
COLOR_SELECTION    = "#dbeafe"   # light-blue row selection
COLOR_HEADER_BG    = "#1e40af"   # deep blue for app header bar
COLOR_HEADER_TEXT  = "#ffffff"
