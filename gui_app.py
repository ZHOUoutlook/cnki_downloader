#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CNKI 论文助手 - GUI 入口

使用方法:
    python gui_app.py
"""

import sys
from pathlib import Path

# 支持从项目目录直接运行
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PyQt6.QtWidgets import QApplication

from cnki_downloader.gui import MainWindow


def main():
    """GUI 主入口"""
    app = QApplication(sys.argv)
    app.setFont(app.font())
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
