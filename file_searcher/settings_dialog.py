# -*- coding: utf-8 -*-
"""
设置对话框
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
    QCheckBox, QSpinBox, QTextEdit, QPushButton, QLabel, QGroupBox,
    QMessageBox,
)
from PySide6.QtCore import Signal

from .theme import get_theme
from .utils import get_drives

# 修改后需要重建索引的设置键
INDEX_KEYS = ("index_drives", "exclude_dirs", "exclude_hidden",
              "exclude_system", "index_files_only")


class SettingsDialog(QDialog):
    """应用设置对话框"""

    settingsSaved = Signal(bool)  # True 表示索引设置变化，需要重建索引

    def __init__(self, settings, theme=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.theme = theme or get_theme(settings.get("theme", "light"))
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(500)

        self._build_ui()
        self._load()

    def _build_ui(self):
        t = self.theme
        self.setStyleSheet(f"""
            QDialog {{ background: {t['panel']}; color: {t['text']}; font-size: 13px; }}
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 10px;
                background: {t['panel']};
            }}
            QTabBar::tab {{
                padding: 8px 22px;
                margin-right: 4px;
                border: 1px solid {t['border']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                background: {t['sidebar']};
                color: {t['dim']};
            }}
            QTabBar::tab:selected {{
                background: {t['panel']};
                color: {t['accent']};
                font-weight: 600;
            }}
            QGroupBox {{
                border: 1px solid {t['border']};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
                font-size: 12px;
                color: {t['dim']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QCheckBox {{ spacing: 8px; color: {t['text']}; }}
            QSpinBox {{
                padding: 5px 8px;
                border: 1px solid {t['border']};
                border-radius: 6px;
                background: {t['input_bg']};
                color: {t['text']};
            }}
            QTextEdit {{
                border: 1px solid {t['border']};
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
                background: {t['input_bg']};
                color: {t['text']};
            }}
            QLabel {{ color: {t['dim']}; }}
            QPushButton {{
                padding: 7px 20px;
                border: 1px solid {t['border']};
                border-radius: 6px;
                background: {t['panel']};
                color: {t['dim']};
            }}
            QPushButton:hover {{ background: {t['hover']}; color: {t['text']}; }}
            QPushButton:default {{
                background: {t['accent']};
                color: {t['accent_text']};
                border-color: {t['accent']};
                font-weight: 500;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_index_tab(), "索 引")
        tabs.addTab(self._build_search_tab(), "搜 索")
        tabs.addTab(self._build_interface_tab(), "界 面")
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # ---------- 索引页 ----------
    def _build_index_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.all_drives_cb = QCheckBox("索引所有硬盘驱动器")
        self.all_drives_cb.toggled.connect(self._toggle_drive_group)
        form.addRow(self.all_drives_cb)

        group = QGroupBox("自定义驱动器（取消上方勾选后可选）")
        g_layout = QHBoxLayout(group)
        g_layout.setContentsMargins(10, 4, 10, 4)
        self.drive_cbs = {}
        for d in get_drives():
            cb = QCheckBox(d)
            self.drive_cbs[d] = cb
            g_layout.addWidget(cb)
        g_layout.addStretch()
        self.drive_group = group
        form.addRow(group)

        self.exclude_edit = QTextEdit()
        self.exclude_edit.setPlaceholderText("每行一个要跳过的目录名，如：Windows")
        self.exclude_edit.setFixedHeight(96)
        form.addRow("排除目录:", self.exclude_edit)

        self.exclude_hidden_cb = QCheckBox("跳过隐藏文件和目录")
        form.addRow(self.exclude_hidden_cb)

        self.exclude_system_cb = QCheckBox("跳过系统目录")
        form.addRow(self.exclude_system_cb)

        self.index_dirs_cb = QCheckBox("同时索引文件夹（默认只索引文件）")
        form.addRow(self.index_dirs_cb)

        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(0, 720)
        self.refresh_spin.setSuffix(" 分钟")
        self.refresh_spin.setSpecialValueText("关闭")
        form.addRow("自动刷新索引:", self.refresh_spin)

        return w

    # ---------- 搜索页 ----------
    def _build_search_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.live_search_cb = QCheckBox("边输入边搜索（回车立即搜索）")
        form.addRow(self.live_search_cb)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(50, 1000)
        self.delay_spin.setSingleStep(50)
        self.delay_spin.setSuffix(" 毫秒")
        form.addRow("输入防抖延迟:", self.delay_spin)

        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(500, 100000)
        self.max_results_spin.setSingleStep(500)
        self.max_results_spin.setSuffix(" 条")
        form.addRow("最大结果数:", self.max_results_spin)

        return w

    # ---------- 界面页 ----------
    def _build_interface_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.tray_cb = QCheckBox("关闭窗口时最小化到系统托盘（取消勾选则直接退出）")
        form.addRow(self.tray_cb)

        self.preview_cb = QCheckBox("显示文件预览面板")
        form.addRow(self.preview_cb)

        hotkey_label = QLabel("全局呼出 / 隐藏窗口：Ctrl + Shift + F")
        hotkey_label.setStyleSheet("color:#64748b;")
        form.addRow("全局快捷键:", hotkey_label)

        return w

    # ---------- 数据加载/保存 ----------
    def _load(self):
        s = self.settings

        drives = s.get("index_drives", [])
        self.all_drives_cb.setChecked(not drives)
        for d, cb in self.drive_cbs.items():
            cb.setChecked(d in drives)
        self._toggle_drive_group(not drives)

        self.exclude_edit.setPlainText("\n".join(s.get("exclude_dirs", [])))
        self.exclude_hidden_cb.setChecked(s.get("exclude_hidden", True))
        self.exclude_system_cb.setChecked(s.get("exclude_system", True))
        self.index_dirs_cb.setChecked(not s.get("index_files_only", True))
        self.refresh_spin.setValue(s.get("auto_refresh_interval", 300) // 60)

        self.live_search_cb.setChecked(s.get("search_as_you_type", True))
        self.delay_spin.setValue(s.get("search_delay_ms", 150))
        self.max_results_spin.setValue(s.get("max_search_results", 5000))

        self.tray_cb.setChecked(s.get("close_to_tray", True))
        self.preview_cb.setChecked(s.get("show_preview", True))

    def _reset_defaults(self):
        self.all_drives_cb.setChecked(True)
        for cb in self.drive_cbs.values():
            cb.setChecked(False)

        defaults = self.settings.defaults
        self.exclude_edit.setPlainText("\n".join(defaults["exclude_dirs"]))
        self.exclude_hidden_cb.setChecked(True)
        self.exclude_system_cb.setChecked(True)
        self.index_dirs_cb.setChecked(False)
        self.refresh_spin.setValue(5)

        self.live_search_cb.setChecked(True)
        self.delay_spin.setValue(150)
        self.max_results_spin.setValue(5000)

        self.tray_cb.setChecked(True)
        self.preview_cb.setChecked(True)

    def _save(self):
        old = dict(self.settings.data)

        if self.all_drives_cb.isChecked():
            new_drives = []
        else:
            new_drives = [d for d, cb in self.drive_cbs.items() if cb.isChecked()]
            if not new_drives:
                QMessageBox.information(
                    self, "提示", "未勾选任何驱动器，将索引所有驱动器。")

        exclude = [line.strip() for line
                   in self.exclude_edit.toPlainText().splitlines()
                   if line.strip()]

        self.settings.update({
            "index_drives": new_drives,
            "exclude_dirs": exclude,
            "exclude_hidden": self.exclude_hidden_cb.isChecked(),
            "exclude_system": self.exclude_system_cb.isChecked(),
            "index_files_only": not self.index_dirs_cb.isChecked(),
            "auto_refresh_interval": self.refresh_spin.value() * 60,
            "search_as_you_type": self.live_search_cb.isChecked(),
            "search_delay_ms": self.delay_spin.value(),
            "max_search_results": self.max_results_spin.value(),
            "close_to_tray": self.tray_cb.isChecked(),
            "show_preview": self.preview_cb.isChecked(),
        })

        need_rebuild = any(self.settings.data.get(k) != old.get(k)
                           for k in INDEX_KEYS)
        self.settingsSaved.emit(need_rebuild)
        self.accept()

    def _toggle_drive_group(self, all_checked):
        self.drive_group.setEnabled(not all_checked)
