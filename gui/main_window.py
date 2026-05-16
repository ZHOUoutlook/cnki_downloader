"""主窗口 - CNKI 论文助手 GUI"""

from pathlib import Path

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QFrame, QGroupBox, QGridLayout,
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QProgressBar,
    QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
    QStackedWidget, QStatusBar, QTableView, QTextEdit, QVBoxLayout, QWidget,
    QFileDialog, QMessageBox,
)

from ..config import OUTPUT_DIR
from ..utils.file_utils import save_json, sanitize_filename
from .styles import get_stylesheet
from .workers import AuthCheckWorker, SearchWorker


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
        self._search_thread = None
        self._search_worker = None
        self.all_papers = []
        self.filtered_papers = []
        self.current_page = 1
        self.result_page_size = 20

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()
        self._refresh_result_page()
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

    def _connect_signals(self):
        """连接搜索相关交互。"""
        self.search_btn.clicked.connect(self.start_search)
        self.search_input.returnPressed.connect(self.start_search)
        self.clear_btn.clicked.connect(self.clear_search_results)
        self.export_btn.clicked.connect(self.export_search_results)
        self.filter_input.textChanged.connect(self.apply_result_filter)
        self.prev_btn.clicked.connect(self.show_prev_page)
        self.next_btn.clicked.connect(self.show_next_page)

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
        if self._search_thread and self._search_thread.isRunning():
            self.append_log("正在搜索论文，请稍后关闭窗口。")
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
        self._auth_worker.anonymous_succeeded.connect(self._on_anonymous_auth_succeeded)
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

    def _on_anonymous_auth_succeeded(self, auth, session, reason: str):
        """校园网认证失败后，匿名会话初始化成功。"""
        self.auth = auth
        self.session = session
        self._set_network_status("disconnected", "断开 · 请连接校园网")
        self.set_status("已启用匿名检索，下载需连接校园网")
        self.append_log(f"校园网认证失败：{reason}")
        self.append_log("已启用知网匿名会话，搜索可用，下载需连接校园网。")

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

    def start_search(self):
        """启动论文搜索。"""
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "请输入关键词", "请先输入期刊名称或论文标题。")
            self.search_input.setFocus()
            return
        if self._search_thread and self._search_thread.isRunning():
            return

        search_type = "title" if self.title_radio.isChecked() else "journal"
        page_count = self.page_count_spin.value()
        page_size = int(self.page_size_combo.currentText())
        self.result_page_size = page_size
        self.current_page = 1
        self.all_papers = []
        self.filtered_papers = []
        self.table_model.clear()
        self.update_search_count(0)
        self._update_pager()

        label = "论文标题" if search_type == "title" else "期刊名"
        self.append_log(f"开始按{label}搜索：{keyword}，页数 {page_count}，每页 {page_size}。")
        self.set_status("正在搜索...")
        self._set_searching_state(True)

        self._search_thread = QThread(self)
        self._search_worker = SearchWorker(search_type, keyword, page_count, page_size)
        self._search_worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(self._search_worker.run)
        self._search_worker.page_loaded.connect(self._on_search_page_loaded)
        self._search_worker.succeeded.connect(self._on_search_succeeded)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.finished.connect(self._search_thread.quit)
        self._search_worker.finished.connect(self._search_worker.deleteLater)
        self._search_thread.finished.connect(self._search_thread.deleteLater)
        self._search_thread.finished.connect(self._clear_search_worker)
        self._search_thread.start()

    def _on_search_page_loaded(self, page: int, count: int, total: int):
        if count:
            self.append_log(f"第 {page} 页获取 {count} 篇，累计 {total} 篇。")
        else:
            self.append_log(f"第 {page} 页没有更多结果。")
        self.set_status(f"正在搜索：已获取 {total} 篇")

    def _on_search_succeeded(self, papers: list):
        self.all_papers = papers
        self.apply_result_filter()
        self.set_status("搜索完成")
        self.append_log(f"搜索完成，共获取 {len(papers)} 篇论文。" if papers else "搜索完成，没有搜索到结果。")
        self._set_searching_state(False)

    def _on_search_failed(self, message: str):
        self.set_status("搜索失败")
        self.append_log(f"搜索失败：{message}")
        QMessageBox.warning(self, "搜索失败", message)
        self._set_searching_state(False)

    def _clear_search_worker(self):
        self._search_thread = None
        self._search_worker = None

    def _set_searching_state(self, searching: bool):
        self.search_btn.setEnabled(not searching)
        self.clear_btn.setEnabled(not searching)
        self.export_btn.setEnabled(not searching and bool(self.all_papers))
        self.search_input.setEnabled(not searching)
        self.journal_radio.setEnabled(not searching)
        self.title_radio.setEnabled(not searching)
        self.page_size_combo.setEnabled(not searching)
        self.page_count_spin.setEnabled(not searching)

    def _set_network_status(self, status: str, text: str):
        self.network_status_label.setText(text)
        self.network_status_label.setProperty("status", status)
        self.network_status_label.style().unpolish(self.network_status_label)
        self.network_status_label.style().polish(self.network_status_label)

        is_checking = status == "checking"
        can_download = status == "connected" and not is_checking

        # 搜索、筛选、导出和 JSON 导入不依赖校园网授权。
        self.search_btn.setEnabled(not (getattr(self, "_search_thread", None) and self._search_thread.isRunning()))
        self.export_btn.setEnabled(bool(getattr(self, "all_papers", [])))
        self.import_btn.setEnabled(True)

        # 只有真正需要校园网授权的下载动作随网络状态启停。
        self.download_selected_btn.setEnabled(can_download)
        self.start_dl_btn.setEnabled(can_download)
        self.refresh_network_btn.setEnabled(not is_checking)

    def append_log(self, message: str):
        """追加日志"""
        self.log_text.append(message)

    def apply_result_filter(self):
        """按标题、作者、来源筛选已加载结果。"""
        keyword = self.filter_input.text().strip().lower()
        if not keyword:
            self.filtered_papers = list(self.all_papers)
        else:
            self.filtered_papers = [
                paper for paper in self.all_papers
                if keyword in self._paper_filter_text(paper).lower()
            ]
        self.current_page = 1
        self.update_search_count(len(self.filtered_papers))
        self._refresh_result_page()

    def _paper_filter_text(self, paper) -> str:
        authors = " ".join(author.name for author in getattr(paper, "authors", []))
        return " ".join([getattr(paper, "title", ""), authors, getattr(paper, "source", "")])

    def _refresh_result_page(self):
        """刷新当前页结果。"""
        total = len(self.filtered_papers)
        total_pages = self._total_result_pages()
        if total_pages == 0:
            self.current_page = 0
            page_papers = []
        else:
            self.current_page = max(1, min(self.current_page, total_pages))
            start = (self.current_page - 1) * self.result_page_size
            page_papers = self.filtered_papers[start:start + self.result_page_size]
        self.table_model.set_papers(page_papers)
        self._update_pager(total, total_pages)

    def _total_result_pages(self) -> int:
        if not self.filtered_papers:
            return 0
        return (len(self.filtered_papers) + self.result_page_size - 1) // self.result_page_size

    def _update_pager(self, total: int = None, total_pages: int = None):
        if total is None:
            total = len(self.filtered_papers)
        if total_pages is None:
            total_pages = self._total_result_pages()
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {total_pages} 页 · {total} 篇")
        self.prev_btn.setEnabled(total_pages > 0 and self.current_page > 1)
        self.next_btn.setEnabled(total_pages > 0 and self.current_page < total_pages)

    def show_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_result_page()

    def show_next_page(self):
        total_pages = self._total_result_pages()
        if self.current_page < total_pages:
            self.current_page += 1
            self._refresh_result_page()

    def clear_search_results(self):
        """清空搜索输入和结果。"""
        self.search_input.clear()
        self.filter_input.clear()
        self.all_papers = []
        self.filtered_papers = []
        self.current_page = 1
        self.table_model.clear()
        self.update_search_count(0)
        self._refresh_result_page()
        self.export_btn.setEnabled(False)
        self.set_status("已清空")
        self.append_log("已清空搜索条件和结果。")

    def export_search_results(self):
        """导出当前搜索结果为 JSON。"""
        if not self.all_papers:
            QMessageBox.information(self, "没有可导出的结果", "当前没有搜索结果可导出。")
            return
        default_name = sanitize_filename(self.search_input.text().strip() or "搜索结果") + ".json"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出搜索结果",
            str(Path(OUTPUT_DIR) / default_name),
            "JSON 文件 (*.json)",
        )
        if not filename:
            return
        saved_path = save_json(self.all_papers, filename)
        self.append_log(f"搜索结果已导出：{saved_path}")
        self.set_status("导出完成")

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
