# -*- coding: utf-8 -*-
"""离屏自动化测试：验证搜索回调到达主线程并更新 UI"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from file_searcher.main_window import MainWindow
from file_searcher.indexer import FileIndex


def main():
    app = QApplication([])

    # 阻止测试中触发真实全盘索引
    MainWindow._start_index = lambda self: None

    w = MainWindow()

    # 注入假文件索引（绕过磁盘扫描）
    w.index_engine.files = [
        FileIndex("测试文档.pdf", r"C:\Users\test\docs\测试文档.pdf",
                  1024, 1700000000.0, ".pdf", "documents", False),
        FileIndex("照片.jpg", r"C:\Users\test\pics\照片.jpg",
                  2048, 1700000001.0, ".jpg", "images", False),
        FileIndex("报告.docx", r"C:\Users\test\docs\报告.docx",
                  4096, 1700000002.0, ".docx", "documents", False),
    ]
    w.index_engine._file_count = 3
    w.sidebar.set_index_stats(f"{3:,} 个文件")

    # --- 测试 1: 关键词搜索 ---
    w.search_box.setText("测试")
    w._do_search()

    deadline = time.time() + 3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if w.result_pill.text() != "搜索中…":
            break

    pill = w.result_pill.text()
    rows = w.result_model.rowCount()
    print(f"[T1] pill={pill!r}, rows={rows}")
    assert pill != "搜索中…", "BUG: 卡在搜索中（回调未到达主线程）"
    assert rows == 1, f"期望 1 行结果，实际 {rows}"
    assert w.result_model.get_file(0).name == "测试文档.pdf"

    # --- 测试 2: 清空关键词 → 全部 ---
    w.search_box.setText("")
    w._do_search()
    deadline = time.time() + 3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if w.result_pill.text() not in ("搜索中…", "3 个结果"):
            break
    print(f"[T2] pill={w.result_pill.text()!r}, rows={w.result_model.rowCount()}")
    assert w.result_model.rowCount() == 3

    # --- 测试 3: 分类过滤（空关键词时引擎按分类搜索）---
    w._on_category("documents")
    deadline = time.time() + 3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if w.result_pill.text() != "搜索中…" and w.result_pill.text() != "3 个结果":
            break
    print(f"[T3] pill={w.result_pill.text()!r}, rows={w.result_model.rowCount()}")
    assert w.result_model.rowCount() == 2

    # --- 测试 4: 高级语法 size:>2KB ---
    w._on_category("all")
    w.search_box.setText("size:>2KB")
    w._do_search()
    deadline = time.time() + 3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if w.result_pill.text() != "搜索中…":
            break
    print(f"[T4] pill={w.result_pill.text()!r}, rows={w.result_model.rowCount()}")
    assert w.result_model.rowCount() == 1
    assert w.result_model.get_file(0).name == "报告.docx"

    # --- 测试 5: 错误路径（非法正则）不再卡死 ---
    w.match_mode.setCurrentIndex(5)  # 正则表达式
    w.search_box.setText("[invalid")
    w._do_search()
    deadline = time.time() + 3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if w.result_pill.text() != "搜索中…":
            break
    print(f"[T5] pill={w.result_pill.text()!r}, status={w.status_label.text()!r}")
    assert w.result_pill.text() != "搜索中…", "BUG: 错误路径也卡在搜索中"

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
