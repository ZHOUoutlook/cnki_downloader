#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CNKI 论文助手 - GUI 入口

使用方法:
    cnki-gui
    python -m cnki_downloader.gui_app
"""

import sys

def main():
    """GUI 主入口"""
    try:
        from PyQt6.QtWidgets import QApplication
        from .gui import MainWindow
    except ImportError as exc:
        print(f'GUI 无法启动：{exc}\n请安装或检查 GUI 依赖：pip install "cnki-downloader[gui]"')
        return 1
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setOrganizationName('CNKIDownloader')
    app.setApplicationName('CNKI 论文助手')
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
