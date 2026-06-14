"""
styles.py - Light-theme QSS stylesheet for MediaClean.
"""
from src.utils.constants import (
    COLOR_BG_DARK, COLOR_BG_PANEL, COLOR_BG_CARD,
    COLOR_ACCENT, COLOR_ACCENT_HOVER,
    COLOR_DANGER, COLOR_DANGER_HOVER,
    COLOR_SUCCESS, COLOR_WARNING,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_BORDER, COLOR_SELECTION,
    COLOR_HEADER_BG, COLOR_HEADER_TEXT,
)

MAIN_STYLESHEET = f"""
/* ============================================================
   Global
   ============================================================ */
QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {COLOR_BG_DARK};
}}

/* ============================================================
   Tabs
   ============================================================ */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 0px;
    background-color: {COLOR_BG_DARK};
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_MUTED};
    padding: 11px 28px;
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 13px;
    min-width: 170px;
}}

QTabBar::tab:selected {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_ACCENT};
    border-color: {COLOR_BORDER};
    border-bottom: 3px solid {COLOR_ACCENT};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLOR_SELECTION};
    color: {COLOR_ACCENT};
}}

/* ============================================================
   Buttons
   ============================================================ */
QPushButton {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 500;
    min-height: 32px;
}}

QPushButton:hover {{
    background-color: {COLOR_SELECTION};
    border-color: {COLOR_ACCENT};
    color: {COLOR_ACCENT};
}}

QPushButton:pressed {{
    background-color: #bfdbfe;
}}

QPushButton:disabled {{
    color: #a0aec0;
    border-color: {COLOR_BORDER};
    background-color: {COLOR_BG_CARD};
}}

QPushButton#btn_primary {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
    border: none;
    font-weight: 600;
}}

QPushButton#btn_primary:hover {{
    background-color: {COLOR_ACCENT_HOVER};
    color: #ffffff;
}}

QPushButton#btn_primary:pressed {{
    background-color: #1e3a8a;
}}

QPushButton#btn_danger {{
    background-color: {COLOR_DANGER};
    color: white;
    border: none;
    font-weight: 600;
}}

QPushButton#btn_danger:hover {{
    background-color: {COLOR_DANGER_HOVER};
}}

QPushButton#btn_danger:disabled {{
    background-color: #fca5a5;
    color: #fef2f2;
}}

/* ============================================================
   LineEdit / path bar
   ============================================================ */
QLineEdit {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 7px 12px;
    selection-background-color: {COLOR_SELECTION};
    selection-color: {COLOR_ACCENT};
}}

QLineEdit:focus {{
    border-color: {COLOR_ACCENT};
    background-color: #ffffff;
}}

QLineEdit::placeholder {{
    color: {COLOR_TEXT_MUTED};
}}

/* ============================================================
   Progress Bar
   ============================================================ */
QProgressBar {{
    background-color: {COLOR_BORDER};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 4px;
}}

/* ============================================================
   ScrollArea / ScrollBar
   ============================================================ */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {COLOR_BG_DARK};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #94a3b8;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLOR_BG_DARK};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: #cbd5e1;
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #94a3b8;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ============================================================
   Labels
   ============================================================ */
QLabel#label_muted {{
    color: {COLOR_TEXT_MUTED};
    font-size: 12px;
}}

QLabel#label_heading {{
    color: {COLOR_TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 700;
}}

QLabel#label_stat {{
    color: {COLOR_ACCENT};
    font-size: 22px;
    font-weight: 700;
}}

QLabel#label_danger {{
    color: {COLOR_DANGER};
    font-size: 12px;
}}

QLabel#label_success {{
    color: {COLOR_SUCCESS};
    font-size: 12px;
}}

/* ============================================================
   TreeWidget / ListWidget
   ============================================================ */
QTreeWidget, QListWidget {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    outline: none;
    show-decoration-selected: 1;
    alternate-background-color: #f8fafc;
}}

QTreeWidget::item, QListWidget::item {{
    padding: 6px 8px;
    border-bottom: 1px solid #f1f5f9;
}}

QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {COLOR_SELECTION};
    color: {COLOR_ACCENT};
    border-radius: 4px;
}}

QTreeWidget::item:hover:!selected, QListWidget::item:hover:!selected {{
    background-color: #f0f7ff;
}}

QHeaderView::section {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_MUTED};
    border: none;
    border-right: 1px solid {COLOR_BORDER};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 8px 12px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ============================================================
   CheckBox
   ============================================================ */
QCheckBox {{
    color: {COLOR_TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid #94a3b8;
    border-radius: 4px;
    background-color: {COLOR_BG_PANEL};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_ACCENT};
}}

/* ============================================================
   ComboBox
   ============================================================ */
QComboBox {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 32px;
}}

QComboBox:focus {{
    border-color: {COLOR_ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    selection-background-color: {COLOR_SELECTION};
    selection-color: {COLOR_ACCENT};
    outline: none;
}}

/* ============================================================
   GroupBox
   ============================================================ */
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 600;
    color: {COLOR_TEXT_MUTED};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background-color: {COLOR_BG_PANEL};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: {COLOR_BG_PANEL};
}}

/* ============================================================
   Splitter
   ============================================================ */
QSplitter::handle {{
    background-color: {COLOR_BORDER};
    width: 1px;
    height: 1px;
}}

/* ============================================================
   ToolTip
   ============================================================ */
QToolTip {{
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ============================================================
   StatusBar
   ============================================================ */
QStatusBar {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_MUTED};
    border-top: 1px solid {COLOR_BORDER};
    font-size: 12px;
    padding: 0 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ============================================================
   MessageBox
   ============================================================ */
QMessageBox {{
    background-color: {COLOR_BG_PANEL};
}}

QMessageBox QLabel {{
    color: {COLOR_TEXT_PRIMARY};
}}
"""


def get_card_style(selected: bool = False, marked_delete: bool = False) -> str:
    """Return inline style for a clickable file card widget."""
    if marked_delete:
        bg     = "#fef2f2"
        border = COLOR_DANGER
    elif selected:
        bg     = "#eff6ff"
        border = COLOR_ACCENT
    else:
        bg     = COLOR_BG_PANEL
        border = COLOR_BORDER

    return (
        f"background-color: {bg}; "
        f"border: 1.5px solid {border}; "
        f"border-radius: 8px; "
        f"padding: 6px;"
    )
