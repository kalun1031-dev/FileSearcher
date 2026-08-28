# -*- coding: utf-8 -*-
"""
主题系统：亮色/暗色调色板 + Qt 样式表生成器
"""
from string import Template

LIGHT = {
    "name": "light",
    "app_bg": "#f1f5f9",
    "panel": "#ffffff",
    "sidebar": "#f8fafc",
    "hover": "#eef2f7",
    "border": "#e2e8f0",
    "border_soft": "#f1f5f9",
    "text": "#0f172a",
    "dim": "#64748b",
    "dimmer": "#94a3b8",
    "accent": "#6366f1",
    "accent_hover": "#4f46e5",
    "accent_soft": "#eef2ff",
    "accent_soft_text": "#4338ca",
    "accent_text": "#ffffff",
    "input_bg": "#ffffff",
    "row_hover": "#f8fafc",
    "row_selected": "#e0e7ff",
    "row_selected_text": "#3730a3",
    "overlay_text": "#94a3b8",
    "hl_bg": "#fef08a",
    "scroll_handle": "#cbd5e1",
    "scroll_handle_hover": "#94a3b8",
    "tooltip_bg": "#1e293b",
    "tooltip_text": "#f1f5f9",
    "pill_bg": "#eef2ff",
    "pill_text": "#4f46e5",
}

DARK = {
    "name": "dark",
    "app_bg": "#0b0f16",
    "panel": "#151a23",
    "sidebar": "#101521",
    "hover": "#1d2430",
    "border": "#2a3341",
    "border_soft": "#1d2430",
    "text": "#e6eaf2",
    "dim": "#8b96a8",
    "dimmer": "#5d6a7d",
    "accent": "#818cf8",
    "accent_hover": "#a5b4fc",
    "accent_soft": "#232642",
    "accent_soft_text": "#c7d2fe",
    "accent_text": "#0b0f16",
    "input_bg": "#1a212c",
    "row_hover": "#1a212c",
    "row_selected": "#2b3350",
    "row_selected_text": "#c7d2fe",
    "overlay_text": "#5d6a7d",
    "hl_bg": "#5b4708",
    "scroll_handle": "#3a4453",
    "scroll_handle_hover": "#4d5a6b",
    "tooltip_bg": "#0b0f16",
    "tooltip_text": "#e6eaf2",
    "pill_bg": "#232642",
    "pill_text": "#a5b4fc",
}


def get_theme(name):
    return DARK if str(name or "light").lower() == "dark" else LIGHT


def app_qss(t):
    return Template("""
        QToolTip {
            background: $tooltip_bg;
            color: $tooltip_text;
            border: 1px solid $border;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        QScrollBar:vertical {
            width: 10px;
            background: transparent;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: $scroll_handle;
            border-radius: 5px;
            min-height: 30px;
            margin: 2px;
        }
        QScrollBar::handle:vertical:hover { background: $scroll_handle_hover; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            height: 10px;
            background: transparent;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: $scroll_handle;
            border-radius: 5px;
            min-width: 30px;
            margin: 2px;
        }
        QScrollBar::handle:horizontal:hover { background: $scroll_handle_hover; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QMenu {
            background: $panel;
            border: 1px solid $border;
            border-radius: 10px;
            padding: 6px;
            font-size: 13px;
            color: $text;
        }
        QMenu::item {
            padding: 8px 14px 8px 12px;
            border-radius: 6px;
            margin: 1px 0;
        }
        QMenu::item:selected {
            background: $accent_soft;
            color: $accent_soft_text;
        }
        QMenu::separator {
            height: 1px;
            background: $border;
            margin: 5px 8px;
        }
        QMessageBox { background: $panel; color: $text; }
        QMessageBox QLabel { color: $text; font-size: 13px; }
    """).substitute(t)


def searchbox_qss(t):
    return Template("""
        QLineEdit {
            padding: 11px 56px 11px 16px;
            border: 2px solid $border;
            border-radius: 12px;
            font-size: 14px;
            background: $input_bg;
            color: $text;
            selection-background-color: $accent;
            selection-color: #ffffff;
        }
        QLineEdit:focus { border-color: $accent; }
        QLineEdit::placeholder { color: $dimmer; }
    """).substitute(t)


def ghost_button_qss(t):
    return Template("""
        QPushButton {
            padding: 0 14px;
            border: 1px solid $border;
            border-radius: 10px;
            background: $panel;
            color: $dim;
            font-size: 13px;
        }
        QPushButton:hover {
            background: $hover;
            border-color: $dimmer;
            color: $text;
        }
        QPushButton:pressed { background: $accent_soft; }
    """).substitute(t)


def pill_qss(t):
    return Template("""
        QLabel {
            font-size: 12px;
            color: $pill_text;
            font-weight: 600;
            padding: 4px 12px;
            background: $pill_bg;
            border-radius: 16px;
        }
    """).substitute(t)


def combo_qss(t):
    return Template("""
        QComboBox {
            padding: 5px 10px;
            border: 1px solid $border;
            border-radius: 8px;
            background: $panel;
            color: $dim;
            font-size: 12px;
            min-width: 92px;
        }
        QComboBox:hover { color: $text; border-color: $dimmer; }
        QComboBox::drop-down { border: none; width: 22px; }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid $dim;
            margin-right: 8px;
        }
        QComboBox QAbstractItemView {
            background: $panel;
            border: 1px solid $border;
            border-radius: 8px;
            selection-background-color: $accent_soft;
            selection-color: $accent_soft_text;
            color: $text;
            outline: none;
        }
    """).substitute(t)


def toggle_qss(t):
    return Template("""
        QToolButton {
            padding: 5px 10px;
            border: 1px solid $border;
            border-radius: 8px;
            background: $panel;
            color: $dim;
            font-size: 12px;
            font-weight: 600;
        }
        QToolButton:hover { color: $text; border-color: $dimmer; }
        QToolButton:checked {
            background: $accent_soft;
            color: $accent_soft_text;
            border-color: $accent;
        }
    """).substitute(t)


def list_qss(t):
    return Template("""
        QTreeView {
            background: $panel;
            border: none;
            outline: none;
            font-size: 13px;
        }
        QTreeView::item { padding: 0; border: none; }
    """).substitute(t)


def statusbar_qss(t):
    return Template("""
        QStatusBar {
            background: $sidebar;
            border-top: 1px solid $border;
            font-size: 12px;
            color: $dim;
            padding: 3px 14px;
        }
        QStatusBar::item { border: none; }
    """).substitute(t)


def sortbar_qss(t):
    return Template("""
        QWidget#sortBar {
            background: $panel;
            border-bottom: 1px solid $border;
        }
        QPushButton {
            border: none;
            border-radius: 6px;
            padding: 5px 10px;
            background: transparent;
            color: $dim;
            font-size: 12px;
        }
        QPushButton:hover { background: $hover; color: $text; }
        QPushButton:checked {
            background: $accent_soft;
            color: $accent_soft_text;
            font-weight: 600;
        }
    """).substitute(t)


def progress_qss(t):
    return Template("""
        QProgressBar {
            border: none;
            background: $border;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 $accent, stop:1 $accent_hover);
        }
    """).substitute(t)


def sidebar_qss(t):
    return Template("""
        QWidget#sidebar {
            background: $sidebar;
            border-right: 1px solid $border;
        }
        QScrollArea {
            background: transparent;
            border: none;
        }
        QWidget#scrollInner { background: transparent; }
    """).substitute(t)


def sidebar_button_qss(t):
    return Template("""
        QPushButton {
            padding: 9px 14px;
            border: none;
            border-radius: 8px;
            background: transparent;
            color: $dim;
            font-size: 12.5px;
            text-align: left;
        }
        QPushButton:hover {
            background: $hover;
            color: $text;
        }
        QPushButton:pressed { background: $accent_soft; }
    """).substitute(t)


def history_btn_qss(t):
    return Template("""
        QToolButton {
            border: none;
            color: $dimmer;
            font-size: 11px;
            background: transparent;
        }
        QToolButton:hover { color: $accent; }
    """).substitute(t)
