"""主窗口 - CNKI 论文助手 GUI"""

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QFrame, QGroupBox, QGridLayout,
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QProgressBar,
    QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
    QStackedWidget, QStatusBar, QTableView, QTextEdit, QVBoxLayout, QWidget,
)

from ..config import OUTPUT_DIR
from .styles import get_stylesheet
from .workers import AuthCheckWorker


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNKI 论文助手")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(get_stylesheet())
        self.auth = None
        self.session = None
        self._auth_thread = None
        self._auth_worker = None

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self.refresh_network_status()

    # ── UI 初始化 ──────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 14, 16, 12)
        main_layout.setSpacing(12)

        main_layout.addWidget(self._create_header())

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setObjectName("workspaceSplitter")
        workspace.addWidget(self._create_sidebar())
        workspace.addWidget(self._create_result_area())
        workspace.setStretchFactor(0, 0)
        workspace.setStretchFactor(1, 1)
        workspace.setCollapsible(0, False)
        workspace.setCollapsible(1, False)
        workspace.setSizes([360, 900])

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(workspace)
        vertical_splitter.addWidget(self._create_bottom_panel())
        vertical_splitter.setStretchFactor(0, 5)
        vertical_splitter.setStretchFactor(1, 1)
        vertical_splitter.setSizes([640, 160])

        main_layout.addWidget(vertical_splitter, 1)

    def _create_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("topBar")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("CNKI 论文助手")
        title.setObjectName("appTitle")
        subtitle = QLabel("检索、筛选、批量下载与任务跟踪")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        self.network_status_label = QLabel("正在检测网络...")
        self.network_status_label.setObjectName("networkStatusLabel")
        self.network_status_label.setProperty("status", "checking")
        layout.addWidget(self.network_status_label)

        self.refresh_network_btn = QPushButton("刷新状态")
        self.refresh_network_btn.setObjectName("ghostButton")
        self.refresh_network_btn.clicked.connect(self.refresh_network_status)
        layout.addWidget(self.refresh_network_btn)

        layout.addStretch()

        self.header_settings_btn = QPushButton("设置")
        self.header_settings_btn.setObjectName("ghostButton")
        layout.addWidget(self.header_settings_btn)
        return header

    # ── 侧边栏 ───────────────────────────────────────────────

    def _create_sidebar(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("sideScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(340)
        scroll.setMaximumWidth(420)
        scroll.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        sidebar = QWidget()
        sidebar.setObjectName("sidePanel")
        sidebar.setMinimumWidth(320)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 0, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._create_action_panel())
        layout.addStretch()
        scroll.setWidget(sidebar)
        return scroll

    def _create_action_panel(self) -> QWidget:
        panel = QGroupBox("操作面板")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 22, 12, 12)
        layout.setSpacing(12)

        switcher = QFrame()
        switcher.setObjectName("panelSwitcher")
        switcher_layout = QHBoxLayout(switcher)
        switcher_layout.setContentsMargins(4, 4, 4, 4)
        switcher_layout.setSpacing(4)

        self.search_panel_btn = QPushButton("搜索")
        self.search_panel_btn.setObjectName("switchButton")
        self.search_panel_btn.setCheckable(True)
        self.search_panel_btn.setChecked(True)
        self.download_panel_btn = QPushButton("下载")
        self.download_panel_btn.setObjectName("switchButton")
        self.download_panel_btn.setCheckable(True)

        self.panel_button_group = QButtonGroup(self)
        self.panel_button_group.setExclusive(True)
        self.panel_button_group.addButton(self.search_panel_btn, 0)
        self.panel_button_group.addButton(self.download_panel_btn, 1)

        switcher_layout.addWidget(self.search_panel_btn)
        switcher_layout.addWidget(self.download_panel_btn)
        layout.addWidget(switcher)

        self.action_stack = QStackedWidget()
        self.action_stack.addWidget(self._create_search_panel())
        self.action_stack.addWidget(self._create_download_panel())
        self.panel_button_group.idClicked.connect(self.action_stack.setCurrentIndex)
        layout.addWidget(self.action_stack)
        return panel

    def _create_search_panel(self) -> QWidget:
        panel = QWidget()
        search_layout = QGridLayout(panel)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setHorizontalSpacing(10)
        search_layout.setVerticalSpacing(10)
        search_layout.setColumnMinimumWidth(0, 64)
        search_layout.setColumnStretch(0, 0)
        search_layout.setColumnStretch(1, 1)

        self.journal_radio = QRadioButton("期刊名")
        self.journal_radio.setChecked(True)
        self.title_radio = QRadioButton("论文标题")

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.journal_radio)
        radio_layout.addWidget(self.title_radio)
        radio_layout.addStretch()
        search_layout.addLayout(radio_layout, 0, 0, 1, 2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入期刊名称或论文标题")
        self.search_input.setMinimumWidth(180)
        search_layout.addWidget(self.search_input, 1, 0, 1, 2)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100"])
        search_layout.addWidget(QLabel("每页"), 2, 0)
        search_layout.addWidget(self.page_size_combo, 2, 1)

        self.page_count_spin = QSpinBox()
        self.page_count_spin.setRange(1, 50)
        self.page_count_spin.setValue(1)
        search_layout.addWidget(QLabel("页数"), 3, 0)
        search_layout.addWidget(self.page_count_spin, 3, 1)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setObjectName("primaryButton")
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("secondaryButton")
        self.export_btn = QPushButton("导出 JSON")
        self.export_btn.setObjectName("secondaryButton")
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addWidget(self.search_btn)
        btn_layout.addWidget(self.clear_btn)
        search_layout.addLayout(btn_layout, 4, 0, 1, 2)
        search_layout.addWidget(self.export_btn, 5, 0, 1, 2)

        return panel

    def _create_download_panel(self) -> QWidget:
        panel = QWidget()
        dl_layout = QGridLayout(panel)
        dl_layout.setContentsMargins(0, 0, 0, 0)
        dl_layout.setHorizontalSpacing(10)
        dl_layout.setVerticalSpacing(10)
        dl_layout.setColumnMinimumWidth(0, 64)
        dl_layout.setColumnMinimumWidth(2, 54)
        dl_layout.setColumnStretch(0, 0)
        dl_layout.setColumnStretch(1, 1)
        dl_layout.setColumnStretch(2, 0)

        dl_layout.addWidget(QLabel("保存到"), 0, 0)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(OUTPUT_DIR)
        self.output_dir_input.setMinimumWidth(150)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setObjectName("secondaryButton")
        self.browse_btn.setFixedWidth(58)
        dl_layout.addWidget(self.output_dir_input, 0, 1)
        dl_layout.addWidget(self.browse_btn, 0, 2)

        dl_layout.addWidget(QLabel("请求间隔"), 1, 0)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 120)
        self.delay_spin.setSingleStep(1)
        self.delay_spin.setValue(10)
        self.delay_spin.setSuffix(" 秒")
        dl_layout.addWidget(self.delay_spin, 1, 1, 1, 2)

        dl_layout.addWidget(QLabel("重试次数"), 2, 0)
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        dl_layout.addWidget(self.retry_spin, 2, 1, 1, 2)

        dl_layout.addWidget(QLabel("JSON"), 3, 0)
        self.json_input = QLineEdit()
        self.json_input.setPlaceholderText("选择论文 JSON 文件")
        self.json_input.setMinimumWidth(150)
        self.json_browse_btn = QPushButton("选择")
        self.json_browse_btn.setObjectName("secondaryButton")
        self.json_browse_btn.setFixedWidth(58)
        dl_layout.addWidget(self.json_input, 3, 1)
        dl_layout.addWidget(self.json_browse_btn, 3, 2)

        self.import_btn = QPushButton("导入 JSON")
        self.import_btn.setObjectName("secondaryButton")
        self.start_dl_btn = QPushButton("开始下载")
        self.start_dl_btn.setObjectName("primaryButton")
        self.stop_dl_btn = QPushButton("停止")
        self.stop_dl_btn.setObjectName("dangerButton")
        self.stop_dl_btn.setEnabled(False)
        dl_layout.addWidget(self.import_btn, 4, 0, 1, 3)
        dl_layout.addWidget(self.start_dl_btn, 5, 0, 1, 2)
        dl_layout.addWidget(self.stop_dl_btn, 5, 2)

        self.dl_progress = QProgressBar()
        self.dl_progress.setValue(0)
        dl_layout.addWidget(self.dl_progress, 6, 0, 1, 3)

        self.dl_status_label = QLabel("就绪")
        self.dl_status_label.setObjectName("mutedLabel")
        dl_layout.addWidget(self.dl_status_label, 7, 0, 1, 3)

        return panel

    # ── 结果区 ───────────────────────────────────────────────

    def _create_result_area(self) -> QWidget:
        area = QWidget()
        area.setObjectName("contentPanel")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("resultToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 10, 14, 10)
        toolbar_layout.setSpacing(10)

        self.search_count_label = QLabel("搜索结果：0 篇")
        self.search_count_label.setObjectName("sectionTitle")
        toolbar_layout.addWidget(self.search_count_label)
        toolbar_layout.addStretch()

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("筛选标题、作者、来源")
        toolbar_layout.addWidget(self.filter_input)

        self.download_selected_btn = QPushButton("下载选中")
        self.download_selected_btn.setObjectName("secondaryButton")
        toolbar_layout.addWidget(self.download_selected_btn)

        layout.addWidget(toolbar)
        layout.addWidget(self._create_result_table(), 1)
        return area

    def _create_result_table(self) -> QWidget:
        """创建结果表格组件"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 表格
        self.table_view = QTableView()
        self.table_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSortingEnabled(True)
        header = self.table_view.horizontalHeader()
        header.setMinimumSectionSize(56)
        header.setStretchLastSection(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(34)

        # 表头
        self.table_columns = ["序号", "标题", "作者", "来源", "时间", "被引", "下载"]
        from .result_model import PaperTableModel
        self.table_model = PaperTableModel(self.table_view, self.table_columns)
        self.table_view.setModel(self.table_model)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table_view.setColumnWidth(0, 64)
        self.table_view.setColumnWidth(4, 112)
        self.table_view.setColumnWidth(5, 72)
        self.table_view.setColumnWidth(6, 72)

        layout.addWidget(self.table_view)

        # 分页控件
        pager_layout = QHBoxLayout()
        pager_layout.setContentsMargins(12, 0, 12, 8)
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.setObjectName("secondaryButton")
        self.prev_btn.setEnabled(False)
        self.next_btn = QPushButton("下一页")
        self.next_btn.setObjectName("secondaryButton")
        self.next_btn.setEnabled(False)
        self.page_label = QLabel("第 0 页 / 共 0 页")
        self.page_label.setObjectName("mutedLabel")

        pager_layout.addStretch()
        pager_layout.addWidget(self.prev_btn)
        pager_layout.addWidget(self.page_label)
        pager_layout.addWidget(self.next_btn)

        layout.addLayout(pager_layout)
        return container

    # ── 底部面板 ───────────────────────────────────────────────

    def _create_bottom_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("bottomPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        stats_layout = QHBoxLayout()
        self.dl_stats_label = QLabel("已下载：0/0 | 成功：0 | 失败：0")
        self.dl_stats_label.setObjectName("mutedLabel")
        stats_layout.addWidget(self.dl_stats_label)
        stats_layout.addStretch()
        self.runtime_label = QLabel("任务日志")
        self.runtime_label.setObjectName("mutedLabel")
        stats_layout.addWidget(self.runtime_label)
        layout.addLayout(stats_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("搜索、下载和错误信息会显示在这里")
        layout.addWidget(self.log_text)

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

    def closeEvent(self, event):
        """关闭窗口时清理后台认证线程。"""
        if self._auth_thread and self._auth_thread.isRunning():
            self.append_log("正在检测网络状态，请稍后关闭窗口。")
            event.ignore()
            return
        super().closeEvent(event)

    def set_status(self, message: str):
        """更新状态栏"""
        self.status_label.setText(message)

    def refresh_network_status(self):
        """刷新校园网认证状态。"""
        if self._auth_thread and self._auth_thread.isRunning():
            return

        self._set_network_status("checking", "正在检测网络...")
        self.append_log("正在检测校园网连接状态...")

        self._auth_thread = QThread(self)
        self._auth_worker = AuthCheckWorker()
        self._auth_worker.moveToThread(self._auth_thread)
        self._auth_thread.started.connect(self._auth_worker.run)
        self._auth_worker.succeeded.connect(self._on_auth_succeeded)
        self._auth_worker.failed.connect(self._on_auth_failed)
        self._auth_worker.finished.connect(self._auth_thread.quit)
        self._auth_worker.finished.connect(self._auth_worker.deleteLater)
        self._auth_thread.finished.connect(self._auth_thread.deleteLater)
        self._auth_thread.finished.connect(self._clear_auth_worker)
        self._auth_thread.start()

    def _on_auth_succeeded(self, auth, session):
        """认证成功。"""
        self.auth = auth
        self.session = session
        self._set_network_status("connected", "校园网已连接")
        self.set_status("校园网已连接")
        self.append_log("校园网认证成功，可以开始搜索和下载。")

    def _on_auth_failed(self, message: str):
        """认证失败。"""
        self.auth = None
        self.session = None
        self._set_network_status("disconnected", "断开 · 请连接校园网")
        self.set_status("断开，请连接校园网")
        self.append_log(f"校园网认证失败：{message}")

    def _clear_auth_worker(self):
        self._auth_thread = None
        self._auth_worker = None

    def _set_network_status(self, status: str, text: str):
        self.network_status_label.setText(text)
        self.network_status_label.setProperty("status", status)
        self.network_status_label.style().unpolish(self.network_status_label)
        self.network_status_label.style().polish(self.network_status_label)

        is_connected = status == "connected"
        is_checking = status == "checking"
        enabled = is_connected and not is_checking
        for button in (
            self.search_btn,
            self.export_btn,
            self.download_selected_btn,
            self.import_btn,
            self.start_dl_btn,
        ):
            button.setEnabled(enabled)
        self.refresh_network_btn.setEnabled(not is_checking)

    def append_log(self, message: str):
        """追加日志"""
        self.log_text.append(message)

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
