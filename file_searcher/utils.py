# -*- coding: utf-8 -*-
"""
工具函数模块
"""
import os
import sys
import subprocess
from datetime import datetime


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    if size >= 100:
        return f"{size:.0f} {units[i]}"
    elif size >= 10:
        return f"{size:.1f} {units[i]}"
    else:
        return f"{size:.2f} {units[i]}"


def format_time(timestamp):
    """格式化时间戳"""
    if timestamp == 0:
        return "—"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError):
        return "—"


def format_date(timestamp):
    """格式化日期"""
    if timestamp == 0:
        return "—"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except (OSError, ValueError):
        return "—"


def open_file(path):
    """打开文件（使用系统默认程序）"""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False


def open_in_explorer(path):
    """在资源管理器中打开并选中文件"""
    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", path], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        else:
            folder = os.path.dirname(path)
            subprocess.run(["xdg-open", folder], check=False)
        return True
    except Exception:
        return False


def open_properties(path):
    """打开文件属性窗口"""
    try:
        if sys.platform == "win32":
            subprocess.run(["powershell", "-Command",
                          f"(New-Object -ComObject Shell.Application).NameSpace((Split-Path '{path}')).ParseName((Split-Path '{path}' -Leaf)).InvokeVerb('Properties')"],
                         check=False)
        return True
    except Exception:
        return False


def get_drives():
    """获取可用驱动器列表"""
    drives = []
    if sys.platform == "win32":
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
    else:
        drives.append("/")
    return drives


def get_file_extension(filename):
    """获取文件扩展名（小写，带点）"""
    return os.path.splitext(filename)[1].lower()


def is_hidden(path, name):
    """判断文件/目录是否隐藏"""
    if name.startswith('.'):
        return True
    try:
        if sys.platform == "win32":
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
            if attrs != -1:
                # FILE_ATTRIBUTE_HIDDEN = 2, FILE_ATTRIBUTE_SYSTEM = 4
                if attrs & 2 or attrs & 4:
                    return True
    except Exception:
        pass
    return False


# 文件类型分类
FILE_TYPE_CATEGORIES = {
    "documents": {".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx",
                  ".ppt", ".pptx", ".md", ".rtf", ".odt", ".csv",
                  ".json", ".xml", ".html", ".htm", ".log", ".wps",
                  ".et", ".dps", ".epub", ".mobi", ".azw"},
    "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
               ".svg", ".ico", ".tiff", ".tif", ".raw", ".heic",
               ".psd", ".ai", ".eps", ".xcf", ".dwg", ".cdr"},
    "videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
               ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".rmvb",
               ".rm", ".ts", ".m2ts", ".vob", ".dat"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma",
              ".m4a", ".ape", ".opus", ".aiff", ".au", ".mid",
              ".midi", ".dsf", ".dff"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
                 ".xz", ".iso", ".cab", ".z", ".tgz", ".tbz2",
                 ".lz", ".zst", ".arj", ".lzh"},
    "programs": {".exe", ".msi", ".bat", ".cmd", ".sh", ".py",
                 ".js", ".ts", ".java", ".c", ".cpp", ".h",
                 ".cs", ".go", ".rs", ".rb", ".php", ".swift",
                 ".kt", ".dart", ".lua", ".pl", ".r", ".m",
                 ".mm", ".vb", ".vbs", ".ps1", ".dll", ".sys",
                 ".drv", ".com", ".scr", ".pif"},
    "design": {".psd", ".ai", ".sketch", ".fig", ".xd", ".eps",
               ".indd", ".cdr", ".svg", ".blend", ".3ds", ".max",
               ".obj", ".fbx", ".stl"},
    "fonts": {".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon",
              ".ttc"},
}


def get_file_category(ext):
    """根据扩展名获取文件分类"""
    ext = ext.lower()
    for cat, exts in FILE_TYPE_CATEGORIES.items():
        if ext in exts:
            return cat
    return "others"


def get_category_icon(cat):
    """获取分类图标名称"""
    icons = {
        "documents": "📄",
        "images": "🖼️",
        "videos": "🎬",
        "audio": "🎵",
        "archives": "📦",
        "programs": "⚙️",
        "design": "🎨",
        "fonts": "🔤",
        "folders": "📁",
        "others": "📎",
    }
    return icons.get(cat, "📎")


def get_category_name(cat):
    """获取分类中文名"""
    names = {
        "documents": "文档",
        "images": "图片",
        "videos": "视频",
        "audio": "音频",
        "archives": "压缩包",
        "programs": "程序",
        "design": "设计",
        "fonts": "字体",
        "folders": "文件夹",
        "others": "其他",
    }
    return names.get(cat, "其他")


def parse_size(size_str):
    """解析大小字符串为字节数，如 '5MB' -> 5*1024*1024"""
    if not size_str:
        return None
    size_str = size_str.strip().upper().replace(" ", "")
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3,
             "TB": 1024**4, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    
    num_str = ""
    unit_str = ""
    for ch in size_str:
        if ch.isdigit() or ch == '.':
            num_str += ch
        else:
            unit_str += ch
    
    if not num_str:
        return None
    
    try:
        num = float(num_str)
    except ValueError:
        return None
    
    if not unit_str:
        return int(num)
    
    multiplier = units.get(unit_str, 1)
    return int(num * multiplier)
