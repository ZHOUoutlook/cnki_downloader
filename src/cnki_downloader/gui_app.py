#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CNKI 论文助手 - GUI 入口

使用方法:
    python gui_app.py
"""

import sys

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    print("GUI 需要 PyQt6，请执行：pip install cnki-downloader[gui]")
    sys.exit(1)

from .gui import MainWindow


def main():
    """GUI 主入口"""
    app = QApplication(sys.argv)
    app.setFont(app.font())
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
