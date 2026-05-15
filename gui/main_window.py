"""主窗口 - CNKI 论文助手 GUI"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog,
    QGroupBox, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QProgressBar, QPushButton, QRadioButton, QSpinBox, QSplitter, QStatusBar,
    QTabWidget, QTableView, QVBoxLayout, QWidget,
)

from ..config import OUTPUT_DIR
from .styles import get_stylesheet


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNKI 论文助手")
        self.resize(1200, 800)

        self._init_ui()
        self._init_menu()
        self._init_statusbar()

    # ── UI 初始化 ──────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 使用分割器：上部为搜索/下载面板 + 结果表格，下部为状态信息
        splitter = QSplitter(Qt.Orientation.Vertical)

        # --- 上部：标签页（搜索 / 下载） ---
        self.tabs = QTabWidget()
        self.search_tab = self._create_search_tab()
        self.download_tab = self._create_download_tab()
        self.tabs.addTab(self.search_tab, "搜索")
        self.tabs.addTab(self.download_tab, "下载")
        splitter.addWidget(self.tabs)

        # --- 下部：状态面板 ---
        self.bottom_panel = self._create_bottom_panel()
        splitter.addWidget(self.bottom_panel)

        # 比例：上部占 70%，下部占 30%
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    # ── 搜索面板 ───────────────────────────────────────────────

    def _create_search_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # 搜索条件组
        search_group = QGroupBox("搜索条件")
        search_layout = QGridLayout()

        self.journal_radio = QRadioButton("期刊名")
        self.journal_radio.setChecked(True)
        self.title_radio = QRadioButton("论文标题")

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.journal_radio)
        radio_layout.addWidget(self.title_radio)
        search_layout.addLayout(radio_layout, 0, 0, 1, 2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入期刊名称或论文标题")
        search_layout.addWidget(self.search_input, 1, 0)

        self.page_count_spin = QSpinBox()
        self.page_count_spin.setRange(1, 50)
        self.page_count_spin.setValue(1)
        self.page_count_spin.setFixedWidth(80)
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("页数："))
        page_layout.addWidget(self.page_count_spin)
        search_layout.addLayout(page_layout, 1, 1)

        self.search_btn = QPushButton("搜索")
        self.clear_btn = QPushButton("清空")
        self.export_btn = QPushButton("导出 JSON")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.search_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        search_layout.addLayout(btn_layout, 2, 0, 1, 2)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # 结果表格
        self.table_widget = self._create_result_table()
        layout.addWidget(self.table_widget)

        return tab

    def _create_result_table(self) -> QWidget:
        """创建结果表格组件"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 表格
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(28)

        # 表头
        self.table_columns = ["序号", "标题", "作者", "来源", "时间", "被引", "下载"]
        from .result_model import PaperTableModel
        self.table_model = PaperTableModel(self.table_view, self.table_columns)
        self.table_view.setModel(self.table_model)

        layout.addWidget(self.table_view)

        # 分页控件
        pager_layout = QGridLayout()
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.setEnabled(False)
        self.next_btn = QPushButton("下一页")
        self.next_btn.setEnabled(False)
        self.page_label = QLabel("第 0 页 / 共 0 页")

        pager_layout.addWidget(self.prev_btn, 0, 0)
        pager_layout.addWidget(self.page_label, 0, 1, Qt.AlignmentFlag.AlignCenter)
        pager_layout.addWidget(self.next_btn, 0, 2)
        pager_layout.setColumnStretch(1, 1)

        layout.addLayout(pager_layout)
        return container

    # ── 下载面板 ───────────────────────────────────────────────

    def _create_download_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # 下载设置组
        dl_group = QGroupBox("下载设置")
        dl_layout = QGridLayout()

        dl_layout.addWidget(QLabel("下载目录："), 0, 0)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(OUTPUT_DIR)
        self.browse_btn = QPushButton("浏览...")
        dl_layout.addWidget(self.output_dir_input, 0, 1)
        dl_layout.addWidget(self.browse_btn, 0, 2)

        dl_layout.addWidget(QLabel("请求间隔（秒）："), 1, 0)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 120)
        self.delay_spin.setSingleStep(1)
        self.delay_spin.setValue(3)
        dl_layout.addWidget(self.delay_spin, 1, 1)

        dl_layout.addWidget(QLabel("最大重试次数："), 2, 0)
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        dl_layout.addWidget(self.retry_spin, 2, 1)

        # 导入 JSON
        dl_layout.addWidget(QLabel("JSON 文件："), 3, 0)
        self.json_input = QLineEdit()
        self.json_input.setPlaceholderText("选择论文 JSON 文件")
        self.json_browse_btn = QPushButton("浏览...")
        dl_layout.addWidget(self.json_input, 3, 1)
        dl_layout.addWidget(self.json_browse_btn, 3, 2)

        dl_group.setLayout(dl_layout)
        layout.addWidget(dl_group)

        # 下载操作按钮
        btn_layout = QGridLayout()
        self.import_btn = QPushButton("导入 JSON")
        self.start_dl_btn = QPushButton("开始下载")
        self.stop_dl_btn = QPushButton("停止")
        self.stop_dl_btn.setEnabled(False)

        btn_layout.addWidget(self.import_btn, 0, 0)
        btn_layout.addWidget(self.start_dl_btn, 0, 1)
        btn_layout.addWidget(self.stop_dl_btn, 0, 2)
        btn_layout.setColumnStretch(0, 1)
        layout.addLayout(btn_layout)

        # 下载进度
        progress_group = QGroupBox("下载进度")
        progress_layout = QVBoxLayout(progress_group)

        self.dl_progress = QProgressBar()
        self.dl_progress.setValue(0)
        progress_layout.addWidget(self.dl_progress)

        self.dl_status_label = QLabel("就绪")
        progress_layout.addWidget(self.dl_status_label)

        layout.addWidget(progress_group)
        layout.addStretch()

        return tab

    # ── 底部面板 ───────────────────────────────────────────────

    def _create_bottom_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 搜索统计
        self.search_count_label = QLabel("搜索结果：0 篇")
        layout.addWidget(self.search_count_label)

        # 下载统计
        self.dl_stats_label = QLabel("已下载：0/0 | 成功：0 | 失败：0")
        layout.addWidget(self.dl_stats_label)

        # 日志区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QLabel("")
        self.log_text.setWordWrap(True)
        self.log_text.setStyleSheet("background-color: #f8f9fa; padding: 5px; border-radius: 3px;")
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        return panel

    # ── 菜单 ───────────────────────────────────────────────────

    def _init_menu(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("&文件")

        exit_action = QAction("退&出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu("&工具")

        settings_action = QAction("&设置", self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        tools_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu("&帮助")

        about_action = QAction("&关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ── 状态栏 ─────────────────────────────────────────────────

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        self.status_spacer = QLabel()
        self.status_spacer.setMinimumWidth(200)
        self.status_bar.addPermanentWidget(self.status_spacer)

        self.version_label = QLabel("v1.0.0")
        self.status_bar.addPermanentWidget(self.version_label)

    # ── 辅助方法 ───────────────────────────────────────────────

    def _show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "关于 CNKI 论文助手",
            "CNKI 论文助手 v1.0.0\n\n"
            "一款知网论文搜索和下载的桌面应用。\n\n"
            "基于 PyQt6 构建。"
        )

    def set_status(self, message: str):
        """更新状态栏"""
        self.status_label.setText(message)

    def append_log(self, message: str):
        """追加日志"""
        current = self.log_text.text()
        new_log = f"{current}\n{message}" if current else message
        self.log_text.setText(new_log)
        # 自动滚动到底部
        scrollbar = self.log_text.parent()  # 简化处理，实际应使用 QScrollArea
        if scrollbar:
            pass  # 日志区域较小时不需要滚动

    def update_search_count(self, count: int):
        """更新搜索结果计数"""
        self.search_count_label.setText(f"搜索结果：{count} 篇")

    def update_dl_stats(self, downloaded: int, total: int, success: int, failed: int):
        """更新下载统计"""
        self.dl_stats_label.setText(f"已下载：{downloaded}/{total} | 成功：{success} | 失败：{failed}")

    def update_dl_progress(self, value: int):
        """更新下载进度条"""
        self.dl_progress.setValue(value)

    def set_dl_status(self, message: str):
        """更新下载状态"""
        self.dl_status_label.setText(message)
