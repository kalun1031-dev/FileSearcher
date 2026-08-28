# -*- coding: utf-8 -*-
"""生成应用图标 icon.ico（仅打包时使用，运行时不需要）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage

from file_searcher.main_window import create_app_icon

SIZES = [16, 24, 32, 48, 64, 128, 256]


def qimage_to_pil(qimg):
    from PIL import Image
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.bits()
    try:
        ptr.setsize(qimg.sizeInBytes())
    except AttributeError:
        pass
    buf = bytes(ptr)
    return Image.frombytes("RGBA", (w, h), buf)


def main():
    app = QApplication(sys.argv)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    images = [create_app_icon(s).toImage() for s in SIZES]

    try:
        base = qimage_to_pil(images[-1])
        base.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
        print("icon.ico generated (Pillow, multi-size)")
    except Exception as e:
        print("Pillow failed:", e)
        ok = images[-1].save(out, "ICO")
        print("icon.ico via Qt:", ok)

    if os.path.exists(out):
        print("size:", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
