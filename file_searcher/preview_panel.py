# -*- coding: utf-8 -*-
"""
文件预览面板：选中结果时显示缩略图与详细信息
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont

from .theme import get_theme
from .utils import (
    format_size, format_time, get_category_name, get_category_icon
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
              ".svg", ".ico", ".tiff", ".tif"}


class PreviewPanel(QWidget):
    THUMB_W = 262
    THUMB_H = 170

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._file = None

        # 渲染防抖：快速切换选中项时避免卡顿
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)
        self._debounce.timeout.connect(self._render)

        self._build_ui()
        self.apply_theme(theme)
        self.clear()

    def _build_ui(self):
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        title = QLabel("预览")
        title.setObjectName("previewTitle")
        title_font = QFont("Microsoft YaHei UI")
        title_font.setPointSizeF(9)
        title_font.setWeight(QFont.DemiBold)
        title.setFont(title_font)
        layout.addWidget(title)

        # 缩略图
        self.thumb = QLabel()
        self.thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
        self.thumb.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.thumb, 0, Qt.AlignHCenter)

        # 文件名
        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        self.name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        name_font = QFont("Microsoft YaHei UI")
        name_font.setPointSizeF(12)
        name_font.setWeight(QFont.DemiBold)
        self.name_label.setFont(name_font)
        layout.addWidget(self.name_label)

        # 路径
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_font = QFont("Microsoft YaHei UI")
        path_font.setPointSizeF(9.5)
        self.path_label.setFont(path_font)
        layout.addWidget(self.path_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("previewLine")
        layout.addWidget(line)

        # 信息
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        info_font = QFont("Microsoft YaHei UI")
        info_font.setPointSizeF(10)
        self.info_label.setFont(info_font)
        layout.addWidget(self.info_label)

        layout.addStretch()

    def apply_theme(self, t):
        self.theme = t
        self.setStyleSheet(f"""
            QWidget {{ background: {t['panel']}; border-left: 1px solid {t['border']}; }}
            QLabel#previewTitle {{
                color: {t['dim']};
                letter-spacing: 1px;
            }}
            QFrame#previewLine {{
                color: {t['border']};
                background: {t['border']};
                max-height: 1px;
                border: none;
            }}
        """)
        self.thumb.setStyleSheet(f"""
            QLabel {{
                background: {t['hover']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
        """)
        self.name_label.setStyleSheet(f"color: {t['text']};")
        self.path_label.setStyleSheet(f"color: {t['dim']};")
        self.info_label.setStyleSheet(f"color: {t['text']};")
        if self._file is not None:
            self._render()

    def showFile(self, file):
        self._file = file
        self._debounce.start()

    def clear(self):
        self._file = None
        self._debounce.stop()
        self._set_emoji("🔍")
        self.name_label.setText("未选择文件")
        self.path_label.setText("")
        self.info_label.setText("")

    def _set_emoji(self, emoji):
        self.thumb.clear()
        font = QFont("Microsoft YaHei UI")
        font.setPointSizeF(40)
        self.thumb.setFont(font)
        self.thumb.setText(emoji)

    def _render(self):
        file = self._file
        if file is None:
            self.clear()
            return

        # 缩略图：图片直接加载，超大文件跳过
        if file.ext in IMAGE_EXTS and 0 < file.size <= 80 * 1024 * 1024:
            try:
                pm = QPixmap(file.path)
                if not pm.isNull():
                    scaled = pm.scaled(
                        self.THUMB_W - 16, self.THUMB_H - 16,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.thumb.setPixmap(scaled)
                else:
                    self._set_emoji(get_category_icon(file.category))
            except Exception:
                self._set_emoji(get_category_icon(file.category))
        else:
            self._set_emoji(get_category_icon(file.category))

        self.name_label.setText(file.name)
        self.path_label.setText(file.path)

        cat = get_category_name(file.category)
        type_text = f"{cat}  {file.ext}" if file.ext else cat
        size_text = "文件夹" if file.is_dir else format_size(file.size)
        t = self.theme
        dim = t['dim']
        self.info_label.setText(
            f'<span style="color:{dim};">类型</span>&nbsp;&nbsp;{type_text}<br>'
            f'<span style="color:{dim};">大小</span>&nbsp;&nbsp;{size_text}<br>'
            f'<span style="color:{dim};">修改</span>&nbsp;&nbsp;'
            f'{format_time(file.mtime)}')
