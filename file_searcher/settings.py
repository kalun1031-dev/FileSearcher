# -*- coding: utf-8 -*-
"""
设置管理模块
"""
import os
import json
from pathlib import Path


class Settings:
    """应用设置管理"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _get_config_dir(self):
        """获取配置目录"""
        if os.name == "nt":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        else:
            base = os.path.expanduser("~/.config")
        config_dir = os.path.join(base, "FileSearcher")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def _get_config_file(self):
        return os.path.join(self._get_config_dir(), "settings.json")

    def _get_index_file(self):
        return os.path.join(self._get_config_dir(), "file_index.db")

    def _get_history_file(self):
        return os.path.join(self._get_config_dir(), "history.json")

    def _load(self):
        """加载设置"""
        self.config_file = self._get_config_file()
        self.index_file = self._get_index_file()
        self.history_file = self._get_history_file()

        # 默认设置
        self.defaults = {
            "index_drives": [],  # 要索引的驱动器，空表示全部
            "exclude_dirs": [
                "$Recycle.Bin",
                "System Volume Information",
                "Windows",
                "ProgramData",
                "AppData/Local/Temp",
            ],
            "exclude_hidden": True,
            "exclude_system": True,
            "index_files_only": True,  # 只索引文件，不索引目录
            "auto_index_on_startup": True,
            "auto_refresh_interval": 300,  # 自动刷新间隔（秒），0表示不自动刷新
            "max_search_results": 5000,
            "search_as_you_type": True,
            "search_delay_ms": 150,
            "theme": "light",  # light / dark / auto
            "language": "zh_CN",
            "window_width": 1100,
            "window_height": 700,
            "window_maximized": False,
            "show_preview": True,
            "show_sidebar": True,
            "show_statusbar": True,
            "default_match_mode": "contains",  # contains / exact / startswith / regex / wildcard
            "case_sensitive": False,
            "search_history_limit": 100,
            "hotkey_show": "Ctrl+Shift+F",
            "minimize_to_tray": True,
            "close_to_tray": True,
        }

        self.data = dict(self.defaults)

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        """保存设置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else self.defaults.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def update(self, data):
        self.data.update(data)
        self.save()

    # 历史记录
    def load_history(self):
        """加载搜索历史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_history(self, history):
        """保存搜索历史"""
        try:
            limit = self.get("search_history_limit", 100)
            history = history[:limit]
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_history(self, keyword):
        """添加搜索历史"""
        if not keyword or not keyword.strip():
            return
        keyword = keyword.strip()
        history = self.load_history()
        if keyword in history:
            history.remove(keyword)
        history.insert(0, keyword)
        self.save_history(history)

    def clear_history(self):
        """清空搜索历史"""
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
        except Exception:
            pass
