# -*- coding: utf-8 -*-
"""
轻量文件搜索工具 - 桌面版
启动入口
"""
import sys
import os

# 确保导入路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """检查依赖，缺失时用系统弹窗提示（不依赖 PySide6）"""
    try:
        import PySide6  # noqa: F401
        return True
    except ImportError:
        title = "缺少依赖组件"
        message = (
            "未检测到 PySide6 组件，程序无法启动。\n\n"
            "请打开命令行（CMD）执行以下命令安装：\n\n"
            "    pip install PySide6\n\n"
            "安装完成后重新运行本程序。"
        )
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, message, title, 0x10)  # MB_ICONERROR
        except Exception:
            print(message)
        return False


if not check_dependencies():
    sys.exit(1)

from file_searcher import __version__


def main():
    """主函数"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont, QIcon
    from file_searcher.main_window import MainWindow, create_app_icon

    app = QApplication(sys.argv)
    app.setApplicationName("轻量文件搜索")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("FileSearcher")

    # Windows 任务栏图标分组
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "FileSearcher.1.0")
    except Exception:
        pass

    # 全局应用图标
    app.setWindowIcon(QIcon(create_app_icon(64)))

    # 设置默认字体（全局样式由主题系统在 MainWindow 中应用）
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
