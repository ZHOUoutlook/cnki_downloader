"""文献工作台：文件、结果视图与后台任务的协调。"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QFrame, QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox,
                            QScrollArea, QSplitter, QPlainTextEdit, QProgressBar,
                            QFileDialog, QMessageBox, QDialog, QStackedWidget, QButtonGroup, QSizePolicy)

from .. import __version__
from ..utils import sanitize_filename
from .search_panel import SearchPanel
from .download_panel import DownloadPanel
from .detail_dialog import DetailDialog
from .settings_dialog import SettingsDialog
from .result_table import ResultTable
from .result_model import PaperTableModel
from .workspace import Workspace
from .workers import AuthCheckWorker, SearchWorker, PaperTaskWorker
from .styles import get_stylesheet
from .icons import icon


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings('CNKIDownloader', 'Desktop')
        self.workspace = Workspace()
        self.filtered_papers = []
        self.job = None
        self.task_indices = []
        self.current_page = 1
        self.dirty = False
        self._save_failed = False
        self._close_when_idle = False
        self._paused = False
        self.result_page_size = int(self.settings.value('result_page_size', 20))
        self.font_size = int(self.settings.value('font_size', 10))
        self.setWindowTitle('CNKI 论文助手 · 文献工作台')
        self.resize(1440, 900)
        self.setMinimumSize(1100, 760)
        self._init_ui()
        self._init_menu()
        self._restore_settings()
        self._apply_style()
        self._refresh_results()
        self._set_busy(False)

    @property
    def all_papers(self):
        return self.workspace.papers

    def _init_ui(self):
        root = QWidget()
        root.setObjectName('appRoot')
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame()
        header.setObjectName('appHeader')
        header.setFixedHeight(72)
        bar = QHBoxLayout(header)
        bar.setContentsMargins(24, 0, 24, 0)
        bar.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(icon('book', '#FFFFFF', 22).pixmap(22))
        mark.setFixedSize(40, 40)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet('background: #5B5FEF; border-radius: 10px;')
        bar.addWidget(mark)
        brand = QLabel('CNKI 论文助手')
        brand.setObjectName('brandTitle')
        bar.addWidget(brand)
        caption = QLabel('  /  研究工作台')
        caption.setObjectName('headerCaption')
        bar.addWidget(caption)
        bar.addStretch()
        self.network_label = QLabel('匿名模式')
        self.network_label.setObjectName('mutedLabel')
        connection = QLabel()
        connection.setPixmap(icon('wifi', '#8A93A6', 16).pixmap(16))
        bar.addWidget(connection)
        bar.addWidget(self.network_label)
        self.network_btn = QPushButton('检查连接')
        self.network_btn.setObjectName('ghostButton')
        self.network_btn.clicked.connect(self.check_network)
        bar.addWidget(self.network_btn)
        self.settings_btn = QPushButton('设置')
        self.settings_btn.setIcon(icon('settings'))
        self.settings_btn.setObjectName('ghostButton')
        self.settings_btn.clicked.connect(self.show_settings)
        bar.addWidget(self.settings_btn)
        layout.addWidget(header)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._create_sidebar())
        workspace = QWidget()
        workspace.setObjectName('workspace')
        content = QVBoxLayout(workspace)
        content.setContentsMargins(28, 24, 28, 20)
        content.setSpacing(16)
        content.addWidget(self._create_results(), 1)
        content.addWidget(self._create_task_panel())
        body.addWidget(workspace, 1)
        layout.addLayout(body, 1)
        self.statusBar().hide()

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(280)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 20, 20, 20)
        side.setSpacing(6)
        label = QLabel('工作流程')
        label.setObjectName('eyebrow')
        side.addWidget(label)
        side.addSpacing(6)
        self.flow_buttons = []
        self.flow_group = QButtonGroup(self)
        self.flow_group.setExclusive(True)
        for index, (text, glyph) in enumerate([('检索文献', 'search'), ('补全文献信息', 'layers'), ('下载文件', 'download')]):
            button = QPushButton(text)
            button.setObjectName('navButton')
            button.setIcon(icon(glyph, '#858D9F'))
            button.setCheckable(True)
            self.flow_group.addButton(button, index)
            side.addWidget(button)
            self.flow_buttons.append(button)
        self.flow_buttons[0].setChecked(True)
        side.addSpacing(12)
        separator = QFrame()
        separator.setObjectName('separator')
        separator.setFixedHeight(1)
        side.addWidget(separator)
        side.addSpacing(12)
        self.flow_stack = QStackedWidget()
        self.search_panel = SearchPanel()
        self.search_panel.search_btn.setIcon(icon('search', '#FFFFFF', 18))
        self.search_panel.search_btn.clicked.connect(self.start_search)
        self.search_panel.keyword.returnPressed.connect(self.start_search)
        self.flow_stack.addWidget(self.search_panel)
        self.process_group = QWidget()
        self.process_group.setObjectName('flowPanel')
        form = QVBoxLayout(self.process_group)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(16)
        title = QLabel('整理文献信息')
        title.setObjectName('panelTitle')
        form.addWidget(title)
        hint = QLabel('先补齐文献详情，再获取作者编码。')
        hint.setObjectName('mutedLabel')
        hint.setWordWrap(True)
        form.addWidget(hint)
        form.addSpacing(8)
        self.detail_btn = QPushButton('补全详情与作者链接')
        self.detail_btn.setIcon(icon('file'))
        self.detail_btn.clicked.connect(lambda: self.start_paper_task('detail'))
        form.addWidget(self.detail_btn)
        detail_hint = QLabel('更新摘要、关键词、卷期等信息；缺少作者编码时刷新主页链接。')
        detail_hint.setObjectName('mutedLabel')
        detail_hint.setWordWrap(True)
        form.addWidget(detail_hint)
        form.addSpacing(12)
        self.author_btn = QPushButton('获取作者编码')
        self.author_btn.setObjectName('primaryButton')
        self.author_btn.setIcon(icon('layers', '#FFFFFF', 18))
        self.author_btn.clicked.connect(lambda: self.start_paper_task('author'))
        form.addWidget(self.author_btn)
        author_hint = QLabel('使用最新的作者主页链接补齐 au-code，已有编码自动跳过。')
        author_hint.setObjectName('mutedLabel')
        author_hint.setWordWrap(True)
        form.addWidget(author_hint)
        form.addStretch()
        footnote = QLabel('处理范围在右侧列表底部选择。')
        footnote.setObjectName('mutedLabel')
        form.addWidget(footnote)
        self.flow_stack.addWidget(self.process_group)
        self.download_panel = DownloadPanel()
        self.download_panel.download_btn.setIcon(icon('download', '#FFFFFF', 18))
        self.download_panel.browse_btn.setIcon(icon('folder', size=16))
        self.download_panel.browse_btn.setText('')
        self.download_panel.download_btn.clicked.connect(lambda: self.start_paper_task('download'))
        self.flow_stack.addWidget(self.download_panel)
        side.addWidget(self.flow_stack, 1)
        side.addSpacing(16)
        note = QLabel('检索与信息补全无需校园网')
        note.setObjectName('mutedLabel')
        side.addWidget(note)
        self.flow_group.idClicked.connect(self._select_workflow)
        return sidebar

    def _select_workflow(self, index):
        self.flow_stack.setCurrentIndex(index)
        for i, button in enumerate(self.flow_buttons):
            button.setChecked(i == index)
            button.setIcon(icon(['search', 'layers', 'download'][i], '#5B5FEF' if i == index else '#858D9F'))

    def _create_results(self):
        area = QWidget()
        area.setObjectName('workspace')
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel('文献库')
        title.setObjectName('pageTitle')
        title_row.addWidget(title)
        self.count_label = QLabel('0 篇')
        self.count_label.setObjectName('countBadge')
        title_row.addWidget(self.count_label)
        title_row.addStretch()
        self.open_btn = QPushButton('导入文献')
        self.open_btn.setIcon(icon('folder', size=18))
        self.open_btn.clicked.connect(self.open_json)
        self.save_btn = QPushButton('保存文献库')
        self.save_btn.setObjectName('secondaryButton')
        self.save_btn.setIcon(icon('save', size=18))
        self.save_btn.clicked.connect(self.save_workspace)
        title_row.addWidget(self.open_btn)
        title_row.addWidget(self.save_btn)
        layout.addLayout(title_row)
        self.file_label = QLabel('未打开文件 · 开始检索，或导入已有文献')
        self.file_label.setObjectName('fileBreadcrumb')
        self.file_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.file_label)
        card = QFrame()
        card.setObjectName('contentPanel')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 8, 16, 12)
        card_layout.setSpacing(0)
        tabs = QHBoxLayout()
        tabs.setSpacing(20)
        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)
        self.view_buttons = []
        for i, text in enumerate(['全部文献', '编码待补全', '已下载']):
            button = QPushButton(text)
            button.setObjectName('viewTab')
            button.setCheckable(True)
            self.view_group.addButton(button, i)
            self.view_buttons.append(button)
            tabs.addWidget(button)
        self.view_buttons[0].setChecked(True)
        self.view_group.idClicked.connect(lambda i: self.status_filter.setCurrentIndex([0, 4, 2][i]))
        tabs.addStretch()
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['默认排序', '最新发表', '被引最多', '按标题排序'])
        self.sort_combo.setAccessibleName('排序方式')
        self.sort_combo.setMaximumWidth(140)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_choice)
        tabs.addWidget(self.sort_combo)
        card_layout.addLayout(tabs)
        card_layout.addSpacing(12)
        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.filter_input = QLineEdit()
        self.filter_input.setObjectName('libraryFilter')
        self.filter_input.setPlaceholderText('搜索文献标题、作者或来源')
        self.filter_input.setAccessibleName('筛选文献')
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.addAction(icon('search', '#A1A8B8', 18), QLineEdit.ActionPosition.LeadingPosition)
        self.filter_input.textChanged.connect(self.apply_result_filter)
        self.status_filter = QComboBox()
        self.status_filter.addItems(['全部状态', '待下载', '已下载', '下载失败', '编码待补全'])
        self.status_filter.currentIndexChanged.connect(self.apply_result_filter)
        self.status_filter.setMaximumWidth(134)
        filters.addWidget(self.filter_input, 1)
        filters.addWidget(self.status_filter)
        card_layout.addLayout(filters)
        card_layout.addSpacing(12)
        self.scope = QComboBox()
        self.scope.addItems(['当前筛选结果（全部页）', '仅选中的文献'])
        self.scope.setFixedWidth(205)
        self.scope.setAccessibleName('操作范围')
        self.scope.setToolTip('补全详情、作者编码和下载任务的处理范围')
        self.selection_label = QLabel('已选 0 篇')
        self.selection_label.setObjectName('mutedLabel')
        self.select_all_btn = QPushButton('选择本页')
        self.select_all_btn.setObjectName('ghostButton')
        self.empty_state = QWidget()
        empty = QVBoxLayout(self.empty_state)
        empty.setSpacing(16)
        empty.addStretch()
        empty_icon = QLabel()
        empty_icon.setPixmap(icon('book', '#C5CAE1', 54).pixmap(54))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(empty_icon)
        self.empty_label = QLabel('还没有文献')
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setObjectName('panelTitle')
        empty.addWidget(self.empty_label)
        self.empty_hint = QLabel('在左侧开始检索，或导入已有的 JSON 文件')
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setObjectName('mutedLabel')
        empty.addWidget(self.empty_hint)
        empty.addStretch()
        card_layout.addWidget(self.empty_state, 1)
        self.table_model = PaperTableModel(self)
        self.table_view = ResultTable()
        self.table_view.setModel(self.table_model)
        self.table_view.configure_columns()
        self.table_view.details_requested.connect(self.show_details)
        self.table_view.horizontalHeader().sortIndicatorChanged.connect(self.apply_result_filter)
        self.table_view.selectionModel().selectionChanged.connect(self._selection_changed)
        self.select_all_btn.clicked.connect(self.table_view.selectAll)
        card_layout.addWidget(self.table_view, 1)
        card_layout.addSpacing(8)
        pager = QHBoxLayout()
        self.table_view.setToolTip('双击文献或按 Enter 查看完整详情')
        pager.addWidget(self.scope)
        pager.addWidget(self.selection_label)
        pager.addWidget(self.select_all_btn)
        pager.addStretch()
        self.prev_btn = QPushButton('上一页')
        self.next_btn = QPushButton('下一页')
        self.prev_btn.setObjectName('ghostButton')
        self.next_btn.setObjectName('ghostButton')
        self.prev_btn.clicked.connect(lambda: self.change_page(-1))
        self.next_btn.clicked.connect(lambda: self.change_page(1))
        self.page_label = QLabel('0 / 0')
        self.page_label.setObjectName('mutedLabel')
        pager.addWidget(self.prev_btn)
        pager.addWidget(self.page_label)
        pager.addWidget(self.next_btn)
        card_layout.addLayout(pager)
        layout.addWidget(card, 1)
        return area

    def _on_sort_choice(self, index):
        column, order = [(0, Qt.SortOrder.AscendingOrder), (4, Qt.SortOrder.DescendingOrder),
                         (5, Qt.SortOrder.DescendingOrder), (1, Qt.SortOrder.AscendingOrder)][index]
        self.table_view.sortByColumn(column, order)

    def _create_task_panel(self):
        panel = QFrame()
        panel.setObjectName('taskPanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        row = QHBoxLayout()
        glyph = QLabel()
        glyph.setPixmap(icon('clock', '#969EB1', 18).pixmap(18))
        row.addWidget(glyph)
        self.task_label = QLabel('就绪')
        self.task_label.setObjectName('sectionTitle')
        self.task_label.setMinimumWidth(0)
        self.task_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(self.task_label, 1)
        self.stats_label = QLabel('后台执行 · 自动保存')
        self.stats_label.setObjectName('mutedLabel')
        row.addWidget(self.stats_label)
        self.log_toggle = QPushButton('查看日志')
        self.log_toggle.setObjectName('ghostButton')
        self.log_toggle.setCheckable(True)
        self.log_toggle.toggled.connect(self._set_log_visible)
        row.addWidget(self.log_toggle)
        self.pause_btn = QPushButton('暂停')
        self.pause_btn.setIcon(icon('pause', size=14))
        self.pause_btn.setObjectName('ghostButton')
        self.stop_btn = QPushButton('停止')
        self.stop_btn.setObjectName('dangerButton')
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn.clicked.connect(self.stop_task)
        row.addWidget(self.pause_btn)
        row.addWidget(self.stop_btn)
        layout.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(2000)
        self.log_text.setFixedHeight(130)
        self.log_text.setPlaceholderText('任务进度和处理记录会显示在这里。')
        self.log_text.hide()
        layout.addWidget(self.log_text)
        return panel

    def _set_log_visible(self, visible):
        self.log_text.setVisible(visible)
        self.log_toggle.setChecked(visible)
        self.log_toggle.setText('收起日志' if visible else '查看日志')

    def _init_menu(self):
        files = self.menuBar().addMenu('文件')
        self.open_action = self._action(files, '打开 JSON…', self.open_json, QKeySequence.StandardKey.Open)
        self.save_action = self._action(files, '保存', self.save_workspace, QKeySequence.StandardKey.Save)
        self.save_as_action = self._action(files, '另存全部文献…', self.save_as, QKeySequence.StandardKey.SaveAs)
        self.recent_menu = files.addMenu('最近文件')
        self._update_recent_menu()
        files.addSeparator()
        self._action(files, '退出', self.close, QKeySequence.StandardKey.Quit)
        tools = self.menuBar().addMenu('工具')
        self._action(tools, '设置…', self.show_settings)
        self._action(tools, '清空日志', self.log_text.clear)
        help_menu = self.menuBar().addMenu('帮助')
        self._action(help_menu, '关于', lambda: QMessageBox.information(
            self, '关于', f'CNKI 论文助手 v{__version__}\n搜索、详情和作者编码：匿名会话\nPDF / CAJ 下载：知网授权 IP'))

    def _action(self, menu, title, callback, shortcut=None):
        action = QAction(title, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def append_log(self, message):
        self.log_text.appendPlainText(f'{datetime.now():%H:%M:%S}  {message}')
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def _update_recent_menu(self):
        self.recent_menu.clear()
        paths = self.settings.value('recent_files', [], type=list)
        for path in paths[:10]:
            action = self.recent_menu.addAction(str(path))
            action.triggered.connect(lambda checked=False, p=path: self.open_json(p))
        self.recent_menu.setEnabled(bool(paths) and self.job is None)

    def _remember_file(self):
        path = str(self.workspace.path)
        paths = self.settings.value('recent_files', [], type=list)
        self.settings.setValue('recent_files', [path] + [p for p in paths if p != path][:9])
        self._update_recent_menu()
        self.file_label.setText(self.workspace.path.name)
        self.file_label.setToolTip(path)

    def open_json(self, path=None):
        if self.job or not self._ensure_saved():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, '导入论文 JSON', 'output', 'JSON 文件 (*.json)')
        if not path:
            return
        try:
            workspace = Workspace.load(path)
        except Exception as exc:
            QMessageBox.warning(self, '导入失败', str(exc))
            return
        self.workspace = workspace
        self.dirty = False
        self.filter_input.clear()
        self.status_filter.setCurrentIndex(0)
        self.apply_result_filter()
        self._remember_file()
        self.append_log(f'已导入 {len(self.all_papers)} 篇：{workspace.path}')
        self._set_busy(False)

    def save_workspace(self):
        if not self.workspace.path:
            return self.save_as()
        try:
            self.workspace.save()
            self.dirty = False
            self.file_label.setText(self.workspace.path.name)
            return True
        except Exception as exc:
            self.dirty = True
            self.append_log(f'保存失败：{exc}。数据仍在界面中，请另存文件。')
            self.file_label.setText('有未保存进度 · 请另存 JSON')
            if self.job:
                self._save_failed = True
                self.job.cancel()
            else:
                QMessageBox.warning(self, '保存失败', str(exc))
            return False

    def save_as(self):
        filename, _ = QFileDialog.getSaveFileName(self, '保存全部文献',
            str(self.workspace.path or Path('output/文献库.json').resolve()), 'JSON 文件 (*.json)')
        if not filename:
            return False
        try:
            self.workspace.save(filename)
            self.dirty = False
            self._remember_file()
            self.append_log(f'已保存 {len(self.all_papers)} 篇文献')
            return True
        except Exception as exc:
            QMessageBox.warning(self, '保存失败', str(exc))
            return False

    def _ensure_saved(self):
        if not self.dirty:
            return True
        return bool(self.save_workspace())

    def start_search(self):
        if self.job:
            return
        sp = self.search_panel
        keyword = sp.keyword.text().strip()
        if not keyword:
            sp.keyword.setFocus()
            self.task_label.setText('请先输入期刊名称或论文标题')
            return
        if not self._ensure_saved():
            return
        filename, _ = QFileDialog.getSaveFileName(self, '选择搜索结果文件（已有文件会增量合并）',
            str(Path('output') / (sanitize_filename(keyword) + '.json')), 'JSON 文件 (*.json)')
        if not filename:
            return
        try:
            self.workspace = Workspace.load(filename) if Path(filename).exists() else Workspace(path=filename)
        except Exception as exc:
            QMessageBox.warning(self, '无法读取已有文件', str(exc))
            return
        self.filter_input.clear()
        self.status_filter.setCurrentIndex(0)
        self.apply_result_filter()
        self._remember_file()
        worker = SearchWorker(sp.mode.currentData(), keyword, sp.page_count.value(),
                              int(sp.page_size.currentText()), sp.start_page.value(), self)
        worker.papers_loaded.connect(self._search_page_loaded)
        self._start_job(worker, '正在搜索文献')

    def _search_page_loaded(self, papers):
        added = self.workspace.merge(papers)
        self.dirty = True
        self.append_log(f'本页获取 {len(papers)} 篇，新增 {added} 篇')
        self._autosave()
        self._refresh_results()

    def target_indices(self):
        if self.scope.currentIndex() == 1:
            papers = [self.table_model.paper_at(i.row()) for i in self.table_view.selectionModel().selectedRows()]
        else:
            papers = self.filtered_papers
        lookup = {id(p): i for i, p in enumerate(self.all_papers)}
        return [lookup[id(p)] for p in papers]

    def start_paper_task(self, operation):
        if self.job:
            return
        indices = self.target_indices()
        if not indices:
            self.task_label.setText('请导入文献，或选择需要处理的文献')
            return
        dp = self.download_panel
        if operation == 'download':
            if not dp.output_dir.text().strip():
                self.task_label.setText('请先选择下载保存目录')
                dp.output_dir.setFocus()
                return
            if dp.limit_spin.value():
                indices = indices[:dp.limit_spin.value()]
        if not self.workspace.path and not self.save_as():
            return
        if not self._ensure_saved():
            return
        self.task_indices = indices
        worker = PaperTaskWorker(operation, [self.all_papers[i] for i in indices],
            output_dir=dp.output_dir.text().strip(),
            delay=dp.delay_min_spin.value() if operation == 'download' else 0,
            delay_max=dp.delay_max_spin.value() if operation == 'download' else 0,
            retries=dp.retries_spin.value(), parent=self)
        worker.paper_updated.connect(self._paper_updated)
        label = {'detail': '补全详情 / 刷新作者链接', 'author': '获取作者编码', 'download': '下载文献'}[operation]
        self._start_job(worker, f'{label} · {len(indices)} 篇')

    def _paper_updated(self, index, paper):
        self.workspace.papers[self.task_indices[index]] = paper
        self.dirty = True
        self._autosave()
        self._refresh_results()

    def _autosave(self):
        if not self._save_failed:
            self.save_workspace()

    def _start_job(self, worker, label):
        self.job = worker
        self._paused = False
        self._save_failed = False
        self.pause_btn.setText('暂停')
        self.pause_btn.setIcon(icon('pause', size=14))
        self.progress.setRange(0, 0)
        self.progress.show()
        self.stats_label.setText('正在建立连接…')
        self.task_label.setText(label)
        self.append_log(label)
        self._store_settings()
        worker.log.connect(self.append_log)
        worker.failed.connect(self._task_failed)
        worker.completed.connect(self._task_completed)
        worker.progress.connect(self._task_progress)
        worker.finished.connect(self._job_finished)
        self._set_busy(True)
        worker.start()

    def _task_progress(self, done, total, success, failed, skipped):
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.stats_label.setText(f'{done}/{total} · 成功 {success} · 失败 {failed} · 跳过 {skipped}')
        if failed:
            self._set_log_visible(True)

    def _task_completed(self, message):
        self.task_label.setText(message)
        self.append_log(message)

    def _task_failed(self, message):
        self.task_label.setText('任务失败 · 请查看下方日志')
        self.append_log(f'任务失败：{message}')
        self._set_log_visible(True)

    def _job_finished(self):
        job = self.job
        self.job = None
        if job:
            job.deleteLater()
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
        if self._save_failed:
            self.task_label.setText('文件保存失败 · 任务已停止，请另存 JSON')
            self._set_log_visible(True)
        self.progress.hide()
        self._set_busy(False)
        if self._close_when_idle:
            QTimer.singleShot(0, self.close)

    def _set_busy(self, busy):
        for widget in (self.search_panel, self.process_group, self.download_panel, self.open_btn,
                       self.save_btn, self.network_btn, self.settings_btn, self.scope):
            widget.setEnabled(not busy)
        for action in (self.open_action, self.save_action, self.save_as_action):
            action.setEnabled(not busy)
        self.recent_menu.setEnabled(not busy and bool(self.settings.value('recent_files', [], type=list)))
        self.pause_btn.setEnabled(busy)
        self.stop_btn.setEnabled(busy)
        has_data = bool(self.all_papers)
        self.process_group.setEnabled(not busy and has_data)
        self.download_panel.download_btn.setEnabled(not busy and has_data)
        self.save_btn.setEnabled(not busy and has_data)

    def toggle_pause(self):
        if self.job:
            self._paused = not self._paused
            self.job.set_paused(self._paused)
            self.pause_btn.setText('继续' if self._paused else '暂停')
            self.append_log('已请求暂停，当前文献处理结束后暂停' if self._paused else '任务继续')
            self.pause_btn.setIcon(icon('play' if self._paused else 'pause', size=14))

    def stop_task(self):
        if self.job:
            self.job.cancel()
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.task_label.setText('正在停止 · 等待当前文献处理结束')

    def check_network(self):
        if self.job:
            return
        worker = AuthCheckWorker(self)
        worker.succeeded.connect(lambda: self.network_label.setText('匿名连接正常'))
        worker.succeeded.connect(lambda: self._task_completed('匿名连接正常；下载时单独进行 IP 登录'))
        worker.failed.connect(lambda message: self.network_label.setText('连接失败 · 可重试'))
        self._start_job(worker, '正在检查匿名连接')

    def apply_result_filter(self, *args):
        self.current_page = 1
        self._refresh_results()

    def _refresh_results(self):
        keyword = self.filter_input.text().strip().casefold()
        status = self.status_filter.currentIndex()
        def matches(p):
            text = ' '.join([p.title, p.source, ' '.join(a.name for a in p.authors)]).casefold()
            return (not keyword or keyword in text) and (
                status == 0 or (status == 1 and p.download_status == 'pending')
                or (status == 2 and p.download_status == 'completed')
                or (status == 3 and p.download_status == 'failed')
                or (status == 4 and (not p.authors or any(not a.au_code for a in p.authors))))
        header = self.table_view.horizontalHeader()
        self.filtered_papers = sorted([p for p in self.all_papers if matches(p)],
            key=lambda p: PaperTableModel.sort_key(p, header.sortIndicatorSection()),
            reverse=header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder)
        count = len(self.filtered_papers)
        pages = (count + self.result_page_size - 1) // self.result_page_size
        self.current_page = max(1, min(self.current_page, pages)) if pages else 0
        start = max(0, self.current_page - 1) * self.result_page_size
        self.table_model.set_papers(self.filtered_papers[start:start + self.result_page_size])
        self.count_label.setText(f'{count} / {len(self.all_papers)} 篇' if count != len(self.all_papers) else f'{count} 篇')
        self.view_group.setExclusive(False)
        for button, status_index in zip(self.view_buttons, [0, 4, 2]):
            button.setChecked(status == status_index)
        self.view_group.setExclusive(True)
        self.empty_label.setVisible(count == 0)
        self.empty_state.setVisible(count == 0)
        self.empty_label.setText('没有符合条件的文献' if self.all_papers else '还没有文献')
        self.empty_hint.setText('试试清除关键词或切换状态筛选' if self.all_papers else '在左侧开始检索，或导入已有的 JSON 文件')
        self.table_view.setVisible(count > 0)
        self.page_label.setText(f'{self.current_page} / {pages} 页')
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < pages)
        self._selection_changed()

    def change_page(self, offset):
        self.current_page += offset
        self._refresh_results()

    def _selection_changed(self, *args):
        self.selection_label.setText(f'已选 {len(self.table_view.selectionModel().selectedRows())} 篇')

    def show_details(self, paper):
        if paper is not None:
            DetailDialog(paper, self).exec()

    def show_settings(self):
        if self.job:
            return
        dialog = SettingsDialog({'result_page_size': self.result_page_size, 'font_size': self.font_size}, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()
            self.result_page_size, self.font_size = values['result_page_size'], values['font_size']
            self._apply_style()
            self.apply_result_filter()
            self._store_settings()

    def _apply_style(self):
        self.setStyleSheet(get_stylesheet() + f'\nQWidget {{ font-size: {self.font_size}pt; }}')

    def _restore_settings(self):
        sp, dp = self.search_panel, self.download_panel
        sp.keyword.setText(self.settings.value('keyword', ''))
        sp.mode.setCurrentIndex(int(self.settings.value('search_mode', 0)))
        sp.start_page.setValue(int(self.settings.value('start_page', 1)))
        sp.page_count.setValue(int(self.settings.value('page_count', 1)))
        sp.page_size.setCurrentText(str(self.settings.value('search_page_size', '20')))
        dp.output_dir.setText(self.settings.value('output_dir', str(Path('output/pdfs').resolve())))
        legacy_delay = self.settings.value('delay')
        dp.delay_min_spin.setValue(float(self.settings.value('delay_min', legacy_delay if legacy_delay is not None else 9)))
        dp.delay_max_spin.setValue(float(self.settings.value('delay_max', legacy_delay if legacy_delay is not None else 11)))
        dp.retries_spin.setValue(int(self.settings.value('retries', 3)))
        dp.limit_spin.setValue(int(self.settings.value('limit', 0)))
        self._select_workflow(max(0, min(2, int(self.settings.value('workflow', 0)))))
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def _store_settings(self):
        sp, dp = self.search_panel, self.download_panel
        values = {'keyword': sp.keyword.text(), 'search_mode': sp.mode.currentIndex(),
                  'start_page': sp.start_page.value(), 'page_count': sp.page_count.value(),
                  'search_page_size': sp.page_size.currentText(), 'output_dir': dp.output_dir.text(),
                  'delay_min': dp.delay_min_spin.value(), 'delay_max': dp.delay_max_spin.value(),
                  'retries': dp.retries_spin.value(),
                  'limit': dp.limit_spin.value(), 'result_page_size': self.result_page_size,
                  'font_size': self.font_size, 'geometry': self.saveGeometry(), 'workflow': self.flow_stack.currentIndex()}
        for key, value in values.items():
            self.settings.setValue(key, value)

    def closeEvent(self, event):
        if self.job:
            answer = QMessageBox.question(self, '停止任务后关闭',
                '当前任务仍在运行。是否停止任务，保存已完成的进度后关闭？')
            if answer == QMessageBox.StandardButton.Yes:
                self._close_when_idle = True
                self.stop_task()
            event.ignore()
            return
        if not self._ensure_saved():
            self._close_when_idle = False
            event.ignore()
            return
        self._store_settings()
        event.accept()
