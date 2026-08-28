# -*- coding: utf-8 -*-
"""
主窗口：全新三栏 UI
左侧导航栏（分类统计 + 磁盘位置）· 中部搜索与结果列表 · 右侧预览面板
支持亮/暗主题切换、点击排序、分类即时过滤
"""
import os
import sys
import shutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QToolButton, QComboBox, QTreeView, QSplitter,
    QStatusBar, QLabel, QProgressBar, QMenu, QFileDialog,
    QMessageBox, QSystemTrayIcon, QStyle, QStyledItemDelegate,
    QScrollArea, QApplication,
)
from PySide6.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QTimer, Signal, QRect,
    QPoint, QPointF, QSize, QObject,
)
from PySide6.QtGui import (
    QIcon, QPixmap, QFont, QColor, QPainter, QKeySequence, QShortcut,
    QTextDocument, QAction,
)

from .settings import Settings
from .indexer import IndexEngine
from .searcher import Searcher
from .settings_dialog import SettingsDialog
from .preview_panel import PreviewPanel
from .theme import (
    get_theme, app_qss, searchbox_qss, ghost_button_qss, pill_qss,
    combo_qss, toggle_qss, list_qss, statusbar_qss, sortbar_qss,
    progress_qss, sidebar_qss, sidebar_button_qss, history_btn_qss,
)
from .utils import (
    format_size, format_time, open_file, open_in_explorer,
    get_category_name, get_drives,
)

# 分类元数据: key, 名称, 图标, 颜色
CATEGORY_META = [
    ("all", "全部文件", "🔍", "#6366f1"),
    ("documents", "文档", "📄", "#3b82f6"),
    ("images", "图片", "🖼️", "#10b981"),
    ("videos", "视频", "🎬", "#f59e0b"),
    ("audio", "音频", "🎵", "#ec4899"),
    ("archives", "压缩包", "📦", "#a855f7"),
    ("programs", "程序", "⚙️", "#64748b"),
    ("design", "设计", "🎨", "#d946ef"),
    ("fonts", "字体", "🔤", "#14b8a6"),
    ("others", "其他", "📎", "#94a3b8"),
]

CATEGORY_COLORS = {k: c for k, _, _, c in CATEGORY_META}
CATEGORY_ICONS = {k: i for k, _, i, _ in CATEGORY_META}

SORT_FIELDS = [
    ("mtime", "修改时间"),
    ("name", "名称"),
    ("size", "大小"),
    ("path", "路径"),
]

SORT_FNS = {
    "name": lambda f: f.name.lower(),
    "size": lambda f: f.size,
    "mtime": lambda f: f.mtime,
    "path": lambda f: f.path.lower(),
}


# ---------- 应用图标 ----------
def create_app_icon(size=64):
    from PySide6.QtGui import QPen
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    m = size / 64.0

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#6366f1"))
    painter.drawRoundedRect(QRect(0, 0, size, size), 14 * m, 14 * m)

    pen = QPen(QColor("#ffffff"), 6 * m)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRect(16 * m, 14 * m, 30 * m, 30 * m))
    painter.drawLine(QPointF(44 * m, 44 * m), QPointF(52 * m, 52 * m))
    painter.end()
    return pixmap


# ---------- 结果模型 ----------
class ResultListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.results)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.results):
            return None
        file = self.results[index.row()]
        if role == Qt.DisplayRole:
            return file.name
        if role == Qt.UserRole:
            return file
        if role == Qt.ToolTipRole:
            return (f"{file.name}\n{file.path}\n"
                    f"大小: {format_size(file.size)}\n"
                    f"修改时间: {format_time(file.mtime)}")
        return None

    def set_results(self, results):
        self.beginResetModel()
        self.results = results
        self.endResetModel()

    def get_file(self, row):
        if 0 <= row < len(self.results):
            return self.results[row]
        return None


# ---------- 结果行自绘代理（图标 + 名称 + 路径 + 尺寸/日期） ----------
class ResultDelegate(QStyledItemDelegate):
    ROW_H = 52

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keywords = []
        self.theme = get_theme("light")
        self._doc = QTextDocument()

        self.name_font = QFont("Microsoft YaHei UI")
        self.name_font.setPointSizeF(12.5)
        self.name_font.setWeight(QFont.DemiBold)
        self.sub_font = QFont("Microsoft YaHei UI")
        self.sub_font.setPointSizeF(10.5)
        self.icon_font = QFont("Microsoft YaHei UI")
        self.icon_font.setPointSizeF(10)

    def setKeywords(self, keywords):
        self.keywords = [k for k in keywords if k]

    def apply_theme(self, t):
        self.theme = t

    def sizeHint(self, option, index):
        return QSize(340, self.ROW_H)

    def _name_html(self, name, t):
        escaped = (name.replace('&', '&amp;')
                       .replace('<', '&lt;')
                       .replace('>', '&gt;'))
        kws = [k.lower() for k in self.keywords if k]
        if not kws:
            return escaped
        name_l = name.lower()
        spans = []
        for kw in kws:
            start = 0
            while True:
                pos = name_l.find(kw, start)
                if pos < 0:
                    break
                spans.append((pos, pos + len(kw)))
                start = pos + len(kw)
        spans.sort()
        merged = []
        for s, e in spans:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        parts, last = [], 0
        for s, e in merged:
            parts.append(escaped[last:s])
            parts.append(
                f'<span style="background-color:{t["hl_bg"]};">'
                f'{escaped[s:e]}</span>')
            last = e
        parts.append(escaped[last:])
        return "".join(parts)

    def paint(self, painter, option, index):
        file = index.data(Qt.UserRole)
        if file is None:
            super().paint(painter, option, index)
            return

        t = self.theme
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = option.rect.adjusted(8, 3, -8, -3)

        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(t["row_selected"]))
            painter.drawRoundedRect(rect, 9, 9)
        elif hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(t["row_hover"]))
            painter.drawRoundedRect(rect, 9, 9)

        # 分类图标
        icon_rect = QRect(rect.left() + 8, rect.top() + 11, 30, 30)
        color = QColor(CATEGORY_COLORS.get(file.category, "#94a3b8"))
        icon_bg = QColor(color)
        icon_bg.setAlphaF(0.16)
        painter.setPen(Qt.NoPen)
        painter.setBrush(icon_bg)
        painter.drawRoundedRect(icon_rect, 7, 7)
        painter.setFont(self.icon_font)
        painter.setPen(color)
        painter.drawText(icon_rect, Qt.AlignCenter,
                         CATEGORY_ICONS.get(file.category, "📎"))

        text_left = icon_rect.right() + 10

        painter.setFont(self.sub_font)
        metrics = painter.fontMetrics()

        # 右侧：大小（第一行）、日期（第二行）
        size_str = "文件夹" if file.is_dir else format_size(file.size)
        date_str = format_time(file.mtime)
        size_w = metrics.horizontalAdvance(size_str)
        date_w = metrics.horizontalAdvance(date_str)
        painter.setPen(QColor(t["dim"]))
        painter.drawText(QPoint(rect.right() - 10 - size_w, rect.top() + 24),
                         size_str)
        painter.setPen(QColor(t["dimmer"]))
        painter.drawText(QPoint(rect.right() - 10 - date_w, rect.top() + 42),
                         date_str)

        # 名称（带关键词高亮）
        name_color = t["row_selected_text"] if selected else t["text"]
        name_rect = QRect(text_left, rect.top() + 2,
                          rect.right() - 10 - size_w - 14 - text_left, 24)
        doc = self._doc
        doc.setDefaultFont(self.name_font)
        doc.setHtml(f'<span style="color:{name_color};">'
                    f'{self._name_html(file.name, t)}</span>')
        doc.setTextWidth(name_rect.width())
        painter.setClipRect(name_rect)
        y = name_rect.top() + (name_rect.height() - doc.size().height()) / 2
        painter.translate(name_rect.left(), max(y, name_rect.top()))
        doc.drawContents(painter)
        painter.restore()
        painter.save()

        # 路径（第二行，省略号）
        painter.setFont(self.sub_font)
        path_rect = QRect(text_left, rect.top() + 26,
                          rect.right() - 10 - date_w - 14 - text_left, 20)
        painter.setClipRect(path_rect)
        path_text = metrics.elidedText(file.path, Qt.ElideMiddle,
                                       path_rect.width())
        painter.setPen(QColor(t["dimmer"]))
        painter.drawText(path_rect, Qt.AlignVCenter | Qt.AlignLeft, path_text)
        painter.restore()


# ---------- 侧边栏行 ----------
class CategoryRow(QWidget):
    clicked = Signal(str)

    def __init__(self, key, name, icon, color):
        super().__init__()
        self.key = key
        self._name = name
        self._icon = icon
        self._color = color
        self._count = None
        self._active = False
        self._hover = False
        self._theme = get_theme("light")
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)

    def set_active(self, active):
        self._active = active
        self.update()

    def set_count(self, n):
        self._count = n
        self.update()

    def apply_theme(self, t):
        self._theme = t
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.key)

    def paintEvent(self, e):
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 1, -8, -1)
        if self._active:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["accent_soft"]))
            p.drawRoundedRect(rect, 8, 8)
        elif self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["hover"]))
            p.drawRoundedRect(rect, 8, 8)

        # 图标
        icon_rect = QRect(rect.left() + 8, rect.top() + 4, 26, 26)
        color = QColor(self._color if self.key != "all" else t["accent"])
        bg = QColor(color)
        bg.setAlphaF(0.15)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(icon_rect, 6, 6)
        f = QFont("Microsoft YaHei UI")
        f.setPointSizeF(9)
        p.setFont(f)
        p.setPen(color)
        p.drawText(icon_rect, Qt.AlignCenter, self._icon)

        # 名称
        name_color = t["accent_soft_text"] if self._active else t["text"]
        f = QFont("Microsoft YaHei UI")
        f.setPointSizeF(11)
        if self._active:
            f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(name_color))
        p.drawText(QPoint(rect.left() + 44, rect.top() + 21), self._name)

        # 计数
        if self._count is not None:
            f = QFont("Microsoft YaHei UI")
            f.setPointSizeF(9.5)
            p.setFont(f)
            p.setPen(QColor(t["dimmer"]))
            text = f"{self._count:,}"
            w = p.fontMetrics().horizontalAdvance(text)
            p.drawText(QPoint(rect.right() - 8 - w, rect.top() + 21), text)


class DriveRow(QWidget):
    clicked = Signal(str)

    def __init__(self, drive):
        super().__init__()
        self.key = drive
        self._label = drive.rstrip("\\")
        self._sub = ""
        self._active = False
        self._hover = False
        self._theme = get_theme("light")
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)
        try:
            usage = shutil.disk_usage(drive)
            free_gb = usage.free / 1024**3
            total_gb = usage.total / 1024**3
            self._sub = f"{free_gb:.0f} GB 可用 / {total_gb:.0f} GB"
        except OSError:
            self._sub = "无法读取"

    def set_active(self, active):
        self._active = active
        self.update()

    def apply_theme(self, t):
        self._theme = t
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.key)

    def paintEvent(self, e):
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 2, -8, -2)
        if self._active:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["accent_soft"]))
            p.drawRoundedRect(rect, 8, 8)
        elif self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["hover"]))
            p.drawRoundedRect(rect, 8, 8)

        f = QFont("Microsoft YaHei UI")
        f.setPointSizeF(10)
        p.setFont(f)
        p.setPen(QColor(t["accent"] if self._active else t["dim"]))
        p.drawText(QPoint(rect.left() + 12, rect.top() + 17), "💽")

        f = QFont("Microsoft YaHei UI")
        f.setPointSizeF(10.5)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(t["accent_soft_text"] if self._active else t["text"]))
        p.drawText(QPoint(rect.left() + 40, rect.top() + 18), self._label)

        f = QFont("Microsoft YaHei UI")
        f.setPointSizeF(9)
        p.setFont(f)
        p.setPen(QColor(t["dimmer"]))
        p.drawText(QPoint(rect.left() + 40, rect.top() + 34), self._sub)


# ---------- 侧边栏 ----------
class Sidebar(QWidget):
    categorySelected = Signal(str)
    scopeChanged = Signal(str)
    settingsRequested = Signal()
    reindexRequested = Signal()
    themeToggled = Signal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部
        header = QWidget()
        header.setFixedHeight(72)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 12, 12, 8)
        h_layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(create_app_icon(36))
        h_layout.addWidget(logo)

        v = QVBoxLayout()
        v.setSpacing(1)
        title = QLabel("文件搜索")
        title_font = QFont("Microsoft YaHei UI")
        title_font.setPointSizeF(13)
        title_font.setWeight(QFont.Bold)
        title.setFont(title_font)
        v.addWidget(title)
        self.stats_label = QLabel("索引加载中...")
        stats_font = QFont("Microsoft YaHei UI")
        stats_font.setPointSizeF(8.5)
        self.stats_label.setFont(stats_font)
        v.addWidget(self.stats_label)
        h_layout.addLayout(v, 1)
        layout.addWidget(header)

        # 分类 + 位置（可滚动）
        inner = QWidget()
        inner.setObjectName("scrollInner")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(6, 4, 6, 8)
        inner_layout.setSpacing(0)

        def section_label(text):
            lab = QLabel(text)
            f = QFont("Microsoft YaHei UI")
            f.setPointSizeF(9)
            f.setWeight(QFont.DemiBold)
            lab.setFont(f)
            lab.setContentsMargins(10, 10, 0, 4)
            return lab

        inner_layout.addWidget(section_label("分类"))

        self.cat_rows = {}
        for key, name, icon, color in CATEGORY_META:
            row = CategoryRow(key, name, icon, color)
            row.clicked.connect(self._on_cat)
            row.apply_theme(theme)
            self.cat_rows[key] = row
            inner_layout.addWidget(row)

        inner_layout.addSpacing(10)
        inner_layout.addWidget(section_label("位置（点击筛选）"))

        self.drive_rows = {}
        for drive in get_drives():
            row = DriveRow(drive)
            row.clicked.connect(self._on_drive)
            row.apply_theme(theme)
            self.drive_rows[drive] = row
            inner_layout.addWidget(row)

        inner_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(scroll, 1)

        # 底部操作
        footer = QWidget()
        footer.setContentsMargins(8, 8, 8, 10)
        f_layout = QVBoxLayout(footer)
        f_layout.setContentsMargins(0, 0, 0, 0)
        f_layout.setSpacing(2)

        self.theme_btn = QPushButton("  🌙  切换暗色主题")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.themeToggled.emit)
        f_layout.addWidget(self.theme_btn)

        self.reindex_btn = QPushButton("  ⚡  重建索引")
        self.reindex_btn.setCursor(Qt.PointingHandCursor)
        self.reindex_btn.clicked.connect(self.reindexRequested.emit)
        f_layout.addWidget(self.reindex_btn)

        self.settings_btn = QPushButton("  ⚙️  设置")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settingsRequested.emit)
        f_layout.addWidget(self.settings_btn)

        layout.addWidget(footer)

        self.cat_rows["all"].set_active(True)
        self.apply_theme(theme)

    def _on_cat(self, key):
        for k, row in self.cat_rows.items():
            row.set_active(k == key)
        self.categorySelected.emit(key)

    def _on_drive(self, drive):
        for k, row in self.drive_rows.items():
            row.set_active(k == drive)
        self.scopeChanged.emit(drive)

    def clear_scope(self):
        for row in self.drive_rows.values():
            row.set_active(False)

    def set_index_stats(self, text):
        self.stats_label.setText(text)

    def set_category_counts(self, counts):
        if not counts:
            return
        total = sum(counts.values())
        for key, row in self.cat_rows.items():
            row.set_count(total if key == "all" else counts.get(key, 0))

    def set_indexing_state(self, indexing):
        self.reindex_btn.setText("  ⏹  停止索引" if indexing
                                 else "  ⚡  重建索引")

    def apply_theme(self, t):
        self.theme = t
        self.setStyleSheet(sidebar_qss(t))
        self.stats_label.setStyleSheet(f"color: {t['dimmer']};")
        for row in self.cat_rows.values():
            row.apply_theme(t)
        for row in self.drive_rows.values():
            row.apply_theme(t)
        for btn in (self.theme_btn, self.reindex_btn, self.settings_btn):
            btn.setStyleSheet(sidebar_button_qss(t))
        dark = t["name"] == "dark"
        self.theme_btn.setText("  ☀️  切换亮色主题" if dark
                               else "  🌙  切换暗色主题")


# ---------- 排序栏 ----------
class SortBar(QWidget):
    sortChanged = Signal(str, bool)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("sortBar")
        self.theme = theme
        self._key = "mtime"
        self._desc = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(2)

        self.buttons = {}
        for key, label in SORT_FIELDS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_sort(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch()
        self._refresh()
        self.apply_theme(theme)

    def _on_sort(self, key):
        if self._key == key:
            self._desc = not self._desc
        else:
            self._key = key
            self._desc = (key in ("mtime", "size"))
        self._refresh()
        self.sortChanged.emit(self._key, self._desc)

    def _refresh(self):
        for key, btn in self.buttons.items():
            active = key == self._key
            btn.setChecked(active)
            if active:
                arrow = "↓" if self._desc else "↑"
                btn.setText(f"{dict(SORT_FIELDS)[key]} {arrow}")
            else:
                btn.setText(dict(SORT_FIELDS)[key])

    def apply_theme(self, t):
        self.theme = t
        self.setStyleSheet(sortbar_qss(t))


# ---------- 搜索框 ----------
class SearchBox(QLineEdit):
    searchTriggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(
            "搜索文件名… 支持 *.pdf、ext:doc、size:>100MB、path:下载、!排除")
        self.setClearButtonEnabled(True)
        self._theme = get_theme("light")

        self.history_btn = QToolButton(self)
        self.history_btn.setText("▾")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.setFixedSize(22, 22)
        self.history_btn.clicked.connect(self.show_history)

        self.returnPressed.connect(
            lambda: self.searchTriggered.emit(self.text()))

    def apply_theme(self, t):
        self._theme = t
        self.setStyleSheet(searchbox_qss(t))
        self.history_btn.setStyleSheet(history_btn_qss(t))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.history_btn.move(self.width() - 52, (self.height() - 22) // 2)

    def show_history(self):
        settings = Settings()
        history = settings.load_history()
        if not history:
            return
        menu = QMenu(self)
        for kw in history[:15]:
            text = kw if len(kw) <= 42 else kw[:39] + "..."
            action = QAction(text, menu)
            action.triggered.connect(
                lambda checked, k=kw: self._pick(k))
            menu.addAction(action)
        menu.addSeparator()
        clear = QAction("清空搜索历史", menu)
        clear.triggered.connect(Settings().clear_history)
        menu.addAction(clear)
        menu.exec(self.history_btn.mapToGlobal(
            QPoint(0, self.history_btn.height() + 4)))

    def _pick(self, keyword):
        self.setText(keyword)
        self.searchTriggered.emit(keyword)


# ---------- 搜索完成信号中继 ----------
# 工作线程调用 QTimer.singleShot 无法在无事件循环的线程中触发，
# 用 Qt 信号封送到主线程（绑定 MainWindow 方法 → 自动 QueuedConnection）
class SearchRelay(QObject):
    searchDone = Signal(object, object, object)  # results, elapsed, error


# ---------- 主窗口 ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = Settings()
        self.theme = get_theme(self.settings.get("theme", "light"))
        self.index_engine = IndexEngine(self.settings)
        self.searcher = Searcher(self.index_engine)
        self.search_relay = SearchRelay()
        self.search_relay.searchDone.connect(self._search_done)

        # 状态
        self.current_category = "all"
        self.scope_drive = None
        self.sort_key = "mtime"
        self.sort_desc = True
        self._raw_results = []
        self._last_ms = 0
        self.is_searching = False
        self._was_indexing = False
        self._last_counts = None

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_search)

        self.app_icon = QIcon(create_app_icon(64))

        self._init_ui()
        self._build_context_menu()
        self._init_shortcuts()
        self._init_tray()
        self._init_poll_timer()
        self._load_window_state()
        self._apply_theme()

        self._load_index_cache()
        self._init_auto_refresh()

    # ================= UI 构建 =================
    def _init_ui(self):
        self.setWindowTitle("文件搜索")
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(960, 620)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧导航
        self.sidebar = Sidebar(self.theme)
        self.sidebar.categorySelected.connect(self._on_category)
        self.sidebar.scopeChanged.connect(self._on_scope)
        self.sidebar.settingsRequested.connect(self._open_settings)
        self.sidebar.reindexRequested.connect(self._start_index)
        self.sidebar.themeToggled.connect(self._toggle_theme)
        root.addWidget(self.sidebar)

        # 右侧主区
        right = QWidget()
        root.addWidget(right, 1)
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(0)

        # 顶部：搜索区
        topbar = QWidget()
        top_layout = QVBoxLayout(topbar)
        top_layout.setContentsMargins(20, 14, 20, 10)
        top_layout.setSpacing(10)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.search_box = SearchBox()
        self.search_box.searchTriggered.connect(
            lambda _: self._do_search_now())
        self.search_box.textChanged.connect(self._on_text_changed)
        row1.addWidget(self.search_box, 1)

        self.export_btn = QPushButton("⇩ 导出")
        self.export_btn.setFixedHeight(44)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setToolTip("导出当前结果为 CSV")
        self.export_btn.clicked.connect(self._export_csv)
        row1.addWidget(self.export_btn)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedHeight(44)
        self.settings_btn.setFixedWidth(44)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(self._open_settings)
        row1.addWidget(self.settings_btn)
        top_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.match_mode = QComboBox()
        self.match_mode.addItems(
            ["包含匹配", "精确匹配", "开头匹配", "结尾匹配", "通配符", "正则表达式"])
        self.match_mode.currentIndexChanged.connect(
            lambda _: self._do_search_now())
        row2.addWidget(self.match_mode)

        self.case_btn = QToolButton()
        self.case_btn.setText("Aa")
        self.case_btn.setCheckable(True)
        self.case_btn.setToolTip("区分大小写")
        self.case_btn.clicked.connect(lambda _: self._do_search_now())
        row2.addWidget(self.case_btn)

        row2.addStretch()

        self.result_pill = QLabel("0 个结果")
        row2.addWidget(self.result_pill)

        self.time_label = QLabel("")
        row2.addWidget(self.time_label)
        top_layout.addLayout(row2)

        self.topbar = topbar
        r_layout.addWidget(topbar)

        # 索引进度条（扫描时显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        r_layout.addWidget(self.progress_bar)

        # 排序栏
        self.sortbar = SortBar(self.theme)
        self.sortbar.sortChanged.connect(self._on_sort_changed)
        r_layout.addWidget(self.sortbar)

        # 结果列表 + 预览面板
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self.result_view = QTreeView()
        self.result_model = ResultListModel()
        self.result_view.setModel(self.result_model)
        self.result_delegate = ResultDelegate(self.result_view)
        self.result_view.setItemDelegate(self.result_delegate)
        self.result_view.setRootIsDecorated(False)
        self.result_view.setUniformRowHeights(True)
        self.result_view.setHeaderHidden(True)
        self.result_view.setIndentation(0)
        self.result_view.setSelectionBehavior(QTreeView.SelectRows)
        self.result_view.setSelectionMode(QTreeView.ExtendedSelection)
        self.result_view.setEditTriggers(QTreeView.NoEditTriggers)
        self.result_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.result_view.customContextMenuRequested.connect(
            self._show_context_menu)
        self.result_view.doubleClicked.connect(self._on_double_clicked)
        self.result_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        self.result_view.viewport().setAttribute(Qt.WA_Hover)
        splitter.addWidget(self.result_view)

        self.preview_panel = PreviewPanel(self.theme)
        self.preview_panel.setVisible(
            self.settings.get("show_preview", True))
        splitter.addWidget(self.preview_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([99999, 300])
        r_layout.addWidget(splitter, 1)

        # 空状态覆盖层
        self.empty_overlay = QLabel(self.result_view)
        self.empty_overlay.setAlignment(Qt.AlignCenter)
        self.empty_overlay.setTextFormat(Qt.RichText)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label, 1)

    def _build_context_menu(self):
        self.context_menu = QMenu(self)
        self.action_open = QAction("打开文件", self)
        self.action_open.setShortcut(QKeySequence(Qt.Key_Return))
        self.action_open.triggered.connect(self._open_selected)
        self.context_menu.addAction(self.action_open)

        self.action_open_folder = QAction("打开所在文件夹", self)
        self.action_open_folder.setShortcut(QKeySequence("Ctrl+E"))
        self.action_open_folder.triggered.connect(self._open_location)
        self.context_menu.addAction(self.action_open_folder)

        self.context_menu.addSeparator()

        self.action_copy_path = QAction("复制完整路径", self)
        self.action_copy_path.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.action_copy_path.triggered.connect(self._copy_path)
        self.context_menu.addAction(self.action_copy_path)

        self.action_copy_name = QAction("复制文件名", self)
        self.action_copy_name.triggered.connect(self._copy_name)
        self.context_menu.addAction(self.action_copy_name)

        self.context_menu.addSeparator()

        self.action_delete = QAction("删除文件", self)
        self.action_delete.setShortcut(QKeySequence(Qt.Key_Delete))
        self.action_delete.triggered.connect(self._delete_file)
        self.context_menu.addAction(self.action_delete)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self,
                  lambda: self.search_box.setFocus())
        QShortcut(QKeySequence("Ctrl+L"), self,
                  lambda: self.search_box.setFocus())
        QShortcut(QKeySequence("F5"), self, self._do_search_now)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)
        QShortcut(QKeySequence("Ctrl+Q"), self, self._quit_app)

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(create_app_icon(32)))
        self.tray_icon.setToolTip("文件搜索 · Ctrl+Shift+F 呼出")

        tray_menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._open_settings)
        tray_menu.addAction(settings_action)

        reindex_action = QAction("重建索引", self)
        reindex_action.triggered.connect(
            lambda: (self._show_window(), self._start_index()))
        tray_menu.addAction(reindex_action)

        tray_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _init_poll_timer(self):
        """统一 UI 轮询：索引进度、状态、分类统计"""
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(400)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start()

    def _init_auto_refresh(self):
        interval = self.settings.get("auto_refresh_interval", 300)
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()
        if interval and interval > 0:
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self._auto_refresh)
            self.refresh_timer.start(interval * 1000)

    def _auto_refresh(self):
        if not self.index_engine.is_indexing and not self.is_searching:
            self.index_engine.build_index()

    # ================= 主题 =================
    def _toggle_theme(self):
        name = "dark" if self.theme["name"] == "light" else "light"
        self.settings.set("theme", name)
        self.theme = get_theme(name)
        self._apply_theme()

    def _apply_theme(self):
        t = self.theme
        QApplication.instance().setStyleSheet(app_qss(t))
        self.setStyleSheet(f"QMainWindow {{ background: {t['app_bg']}; }}")
        self.topbar.setStyleSheet(
            f"QWidget {{ background: {t['panel']};"
            f" border-bottom: 1px solid {t['border']}; }}")
        self.search_box.apply_theme(t)
        self.match_mode.setStyleSheet(combo_qss(t))
        self.case_btn.setStyleSheet(toggle_qss(t))
        self.export_btn.setStyleSheet(ghost_button_qss(t))
        self.settings_btn.setStyleSheet(ghost_button_qss(t))
        self.result_pill.setStyleSheet(pill_qss(t))
        self.time_label.setStyleSheet(
            f"color: {t['dimmer']}; font-size: 11px;")
        self.progress_bar.setStyleSheet(progress_qss(t))
        self.result_view.setStyleSheet(list_qss(t))
        self.status_bar.setStyleSheet(statusbar_qss(t))
        self.status_label.setStyleSheet(f"color: {t['dim']};")
        self.sidebar.apply_theme(t)
        self.sortbar.apply_theme(t)
        self.result_delegate.apply_theme(t)
        self.preview_panel.apply_theme(t)
        self._update_empty_overlay_text()

    # ================= 窗口状态 =================
    def _load_window_state(self):
        self.resize(self.settings.get("window_width", 1100),
                    self.settings.get("window_height", 700))
        if self.settings.get("window_maximized", False):
            self.showMaximized()

    def _save_window_state(self):
        if not self.isMaximized():
            self.settings.set("window_width", self.width())
            self.settings.set("window_height", self.height())
        self.settings.set("window_maximized", self.isMaximized())

    # ================= 索引 =================
    def _load_index_cache(self):
        if self.index_engine.load_cache():
            self.sidebar.set_index_stats(
                f"{self.index_engine.file_count:,} 个文件")
        else:
            self.sidebar.set_index_stats("准备建立索引…")
            QTimer.singleShot(300, self._start_index)

    def _start_index(self):
        if self.index_engine.is_indexing:
            self.index_engine.stop()
            return
        self.progress_bar.show()
        self.sidebar.set_indexing_state(True)
        self.status_label.setText("正在建立索引…")
        self.index_engine.build_index()

    def _poll(self):
        engine = self.index_engine

        if engine.is_indexing:
            self._was_indexing = True
            self.progress_bar.show()
            self.status_label.setText(engine.status)
            self.sidebar.set_index_stats(f"{engine.file_count:,} 个文件 · 扫描中")
            return

        if self._was_indexing:
            self._was_indexing = False
            self.progress_bar.hide()
            self.sidebar.set_indexing_state(False)
            self.status_label.setText(engine.status)
            self.sidebar.set_index_stats(f"{engine.file_count:,} 个文件")
            # 索引更新后自动刷新当前视图
            if (self.search_box.text().strip()
                    or self.current_category != "all"):
                self._do_search()

        if engine.category_counts is not None \
                and engine.category_counts != self._last_counts:
            self._last_counts = engine.category_counts
            self.sidebar.set_category_counts(engine.category_counts)

    # ================= 搜索 =================
    def _on_text_changed(self, text):
        if self.settings.get("search_as_you_type", True):
            self.search_timer.start(self.settings.get("search_delay_ms", 150))

    def _do_search_now(self):
        self.search_timer.stop()
        self._do_search()

    def _clear_search(self):
        self.search_box.clear()
        self.search_box.setFocus()
        self._do_search()

    def _do_search(self):
        keyword = self.search_box.text().strip()
        match_mode = self._get_match_mode()
        case_sensitive = self.case_btn.isChecked()
        max_results = self.settings.get("max_search_results", 5000)

        if keyword:
            self.settings.add_history(keyword)

        # 更新高亮关键词
        try:
            query = self.searcher.parse_query(
                keyword, match_mode, case_sensitive)
            self.result_delegate.setKeywords(query.keywords)
        except Exception:
            self.result_delegate.setKeywords([keyword] if keyword else [])

        self.is_searching = True
        self.result_pill.setText("搜索中…")

        # 关键词非空：分类/位置在客户端过滤（切换即时）
        # 关键词为空：分类交给引擎按全库扫描
        category_filter = None
        if not keyword and self.current_category != "all":
            category_filter = self.current_category

        self.searcher.search(
            query_str=keyword,
            match_mode=match_mode,
            case_sensitive=case_sensitive,
            category_filter=category_filter,
            max_results=max_results,
            done_callback=self._emit_search_done,
        )

    def _emit_search_done(self, results, elapsed, error=None):
        """工作线程入口：经信号封送到主线程"""
        self.search_relay.searchDone.emit(results, elapsed, error)

    def _get_match_mode(self):
        modes = ["contains", "exact", "startswith", "endswith",
                 "wildcard", "regex"]
        idx = self.match_mode.currentIndex()
        return modes[idx] if idx < len(modes) else "contains"

    def _search_done(self, results, elapsed, error):
        self.is_searching = False
        if error:
            self.result_pill.setText("搜索出错")
            self.time_label.setText("")
            self.status_label.setText(f"搜索出错: {error}")
            self._update_empty_overlay_text()
            return
        self._raw_results = results
        self._last_ms = elapsed
        self._apply_filters()

    def _apply_filters(self):
        """客户端过滤（分类 + 位置）+ 排序 + 渲染"""
        results = self._raw_results
        if self.current_category != "all":
            results = [f for f in results
                       if f.category == self.current_category]
        if self.scope_drive:
            results = [f for f in results
                       if f.path.startswith(self.scope_drive)]

        results.sort(key=SORT_FNS[self.sort_key], reverse=self.sort_desc)

        self.result_model.set_results(results)
        self.result_pill.setText(f"{len(results):,} 个结果")
        self.time_label.setText(f"{self._last_ms * 1000:.0f} ms")

        if results:
            self.status_label.setText(
                f"找到 {len(results):,} 个结果"
                f"（{self._last_ms * 1000:.0f} ms）")
        elif self.index_engine.is_indexing:
            self.status_label.setText("正在建立索引，结果可能不完整…")
        else:
            self.status_label.setText("未找到匹配的文件")
        self._update_empty_overlay_text()

    def _update_empty_overlay_text(self):
        t = self.theme
        keyword = self.search_box.text().strip()
        if self.result_model.results:
            self.empty_overlay.hide()
            return
        if self.result_model.rowCount() > 0:
            return
        if self.is_searching:
            return
        if keyword:
            title = "未找到匹配的文件"
        elif self.index_engine.is_indexing:
            self.empty_overlay.hide()
            return
        else:
            title = "输入关键词开始搜索"
        self.empty_overlay.setText(
            f'<div style="color:{t["overlay_text"]}; font-size:15px;'
            f' font-weight:600; margin-bottom:14px;">{title}</div>'
            f'<div style="color:{t["overlay_text"]}; font-size:12px;'
            f' line-height:2;">'
            f'&nbsp;&nbsp;*.pdf&nbsp;&nbsp;&nbsp;&nbsp;按扩展名<br>'
            f'&nbsp;&nbsp;ext:doc,xls&nbsp;&nbsp;&nbsp;&nbsp;多扩展名<br>'
            f'&nbsp;&nbsp;size:&gt;100MB&nbsp;&nbsp;&nbsp;&nbsp;按大小<br>'
            f'&nbsp;&nbsp;path:下载&nbsp;&nbsp;&nbsp;&nbsp;按路径<br>'
            f'&nbsp;&nbsp;!临时&nbsp;&nbsp;&nbsp;&nbsp;排除关键词<br>'
            f'&nbsp;&nbsp;folder:&nbsp;&nbsp;&nbsp;&nbsp;只搜文件夹</div>')
        self._update_empty_overlay_geometry()
        self.empty_overlay.show()

    def _update_empty_overlay_geometry(self):
        self.empty_overlay.setGeometry(
            0, 0, self.result_view.width(), self.result_view.height())

    # ================= 过滤/排序交互 =================
    def _on_category(self, category):
        self.current_category = category
        if not self.search_box.text().strip() and category != "all":
            self._do_search()  # 空关键词时需引擎按分类扫描全库
        else:
            self._apply_filters()  # 有关键词时即时过滤

    def _on_scope(self, drive):
        if self.scope_drive == drive:
            self.scope_drive = None
            self.sidebar.clear_scope()
        else:
            self.scope_drive = drive
        self._apply_filters()

    def _on_sort_changed(self, key, desc):
        self.sort_key = key
        self.sort_desc = desc
        self._apply_filters()

    # ================= 选择与预览 =================
    def _get_all_selected_files(self):
        rows = {idx.row() for idx in self.result_view.selectedIndexes()}
        files = []
        for row in sorted(rows):
            f = self.result_model.get_file(row)
            if f:
                files.append(f)
        return files

    def _on_selection_changed(self):
        files = self._get_all_selected_files()
        if not files:
            self.status_label.setText("就绪")
            self.preview_panel.clear()
            return
        self.preview_panel.showFile(files[0])
        total = sum(f.size for f in files)
        text = f"已选中 {len(files)} 项"
        if len(files) > 1:
            text += f"，共 {format_size(total)}"
        self.status_label.setText(text)

    def _on_double_clicked(self, index):
        file = self.result_model.get_file(index.row())
        if file:
            open_file(file.path)

    def _show_context_menu(self, pos):
        self.context_menu.exec(self.result_view.viewport().mapToGlobal(pos))

    def _open_selected(self):
        for f in self._get_all_selected_files():
            open_file(f.path)

    def _open_location(self):
        for f in self._get_all_selected_files():
            open_in_explorer(f.path)
            break

    def _copy_path(self):
        files = self._get_all_selected_files()
        if files:
            QApplication.clipboard().setText(
                "\n".join(f.path for f in files))
            self.status_bar.showMessage(
                f"已复制 {len(files)} 条路径", 2000)

    def _copy_name(self):
        files = self._get_all_selected_files()
        if files:
            QApplication.clipboard().setText(
                "\n".join(f.name for f in files))
            self.status_bar.showMessage(
                f"已复制 {len(files)} 个文件名", 2000)

    def _delete_file(self):
        files = self._get_all_selected_files()
        if not files:
            return
        reply = QMessageBox.warning(
            self, "确认删除",
            f"确定要删除选中的 {len(files)} 个文件吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        errors = []
        for f in files:
            try:
                os.remove(f.path)
            except OSError as e:
                errors.append(f"{f.path}\n{e}")
        if errors:
            QMessageBox.warning(self, "部分删除失败", "\n\n".join(errors))
        self._do_search()

    # ================= 导出 =================
    def _export_csv(self):
        results = self.result_model.results
        if not results:
            QMessageBox.information(self, "导出 CSV", "当前没有可导出的结果")
            return
        from datetime import datetime
        default_name = f"搜索结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", default_name, "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            import csv
            with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
                writer = csv.writer(fp)
                writer.writerow(["文件名", "路径", "大小(字节)", "大小",
                                 "修改时间", "分类"])
                for file in results:
                    writer.writerow([
                        file.name, file.path, file.size,
                        format_size(file.size), format_time(file.mtime),
                        get_category_name(file.category)])
            self.status_bar.showMessage(
                f"已导出 {len(results):,} 条结果到 {path}", 5000)
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    # ================= 设置 =================
    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self.theme, self)
        dlg.settingsSaved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self, need_rebuild):
        self.preview_panel.setVisible(
            self.settings.get("show_preview", True))
        self._init_auto_refresh()
        if need_rebuild:
            self._start_index()

    # ================= 全局快捷键 =================
    HOTKEY_ID = 0xB0B

    def _register_hotkey(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            if (getattr(self, "_hotkey_hwnd", None) == hwnd
                    and getattr(self, "_hotkey_registered", False)):
                return
            self._unregister_hotkey()
            MOD_CTRL_SHIFT = 0x0002 | 0x0004
            VK_F = 0x46
            if ctypes.windll.user32.RegisterHotKey(
                    hwnd, self.HOTKEY_ID, MOD_CTRL_SHIFT, VK_F):
                self._hotkey_registered = True
                self._hotkey_hwnd = hwnd
        except Exception:
            pass

    def _unregister_hotkey(self):
        if getattr(self, "_hotkey_registered", False):
            try:
                import ctypes
                hwnd = getattr(self, "_hotkey_hwnd", 0)
                if hwnd:
                    ctypes.windll.user32.UnregisterHotKey(hwnd, self.HOTKEY_ID)
            except Exception:
                pass
        self._hotkey_registered = False
        self._hotkey_hwnd = None

    def _toggle_from_hotkey(self):
        if self.isVisible() and self.isActiveWindow():
            self.hide()
        else:
            self._show_window()

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32":
            try:
                from ctypes import wintypes
                et = (eventType.decode()
                      if isinstance(eventType, (bytes, bytearray))
                      else str(eventType))
                if "windows_generic_MSG" in et:
                    msg = wintypes.MSG.from_address(int(message))
                    if msg.message == 0x0312 and msg.wParam == self.HOTKEY_ID:
                        self._toggle_from_hotkey()
                        return True, 0
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    # ================= 托盘/窗口 =================
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()
        self.search_box.setFocus()

    def _quit_app(self):
        self._save_window_state()
        self._unregister_hotkey()
        self.tray_icon.hide()
        QApplication.quit()

    # ================= 事件 =================
    def showEvent(self, event):
        super().showEvent(event)
        self._register_hotkey()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.empty_overlay is not None and self.empty_overlay.isVisible():
            self._update_empty_overlay_geometry()

    def closeEvent(self, event):
        if self.settings.get("close_to_tray", True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "文件搜索", "程序已最小化到系统托盘（Ctrl+Shift+F 呼出）",
                QSystemTrayIcon.Information, 2000)
        else:
            self._save_window_state()
            self._unregister_hotkey()
            self.tray_icon.hide()
            event.accept()
