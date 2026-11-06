"""用真实 Qt 事件循环验证工作台交互，网络使用替身。"""
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
pytest.importorskip('PyQt6')
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from cnki_downloader.gui.main_window import MainWindow
from cnki_downloader.gui.detail_dialog import DetailDialog
from cnki_downloader.gui.settings_dialog import SettingsDialog
from cnki_downloader.gui.workspace import Workspace
from cnki_downloader.gui import workers
from cnki_downloader.models import Paper, Author


@pytest.fixture(scope='module')
def app():
    instance = QApplication.instance() or QApplication([])
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
    return instance


@pytest.fixture
def window(app, tmp_path):
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    win = MainWindow(settings)
    yield win
    assert win.job is None
    win.close()


def test_startup_does_not_login_and_empty_state_is_visible(app, tmp_path, monkeypatch):
    auth = Mock()
    monkeypatch.setattr(workers, 'CNKIAuth', auth)
    window = MainWindow(QSettings(str(tmp_path / 'startup.ini'), QSettings.Format.IniFormat))
    assert window.job is None
    assert not window.empty_label.isHidden()
    assert not window.detail_btn.isEnabled()
    assert window.search_panel.search_btn.isEnabled()
    auth.assert_not_called()
    window.close()


def test_sort_all_pages_then_map_selected_identity(window):
    papers = [Paper(i, f'论文{i:02}', '/paper', citation_count=50-i) for i in range(1, 46)]
    window.workspace = Workspace(papers)
    window.apply_result_filter()
    window.table_view.sortByColumn(5, Qt.SortOrder.DescendingOrder)
    assert window.table_model.paper_at(0).seq == 1
    window.change_page(1)
    assert window.table_model.paper_at(0).seq == 21
    window.table_view.selectRow(0)
    window.scope.setCurrentIndex(1)
    assert window.target_indices() == [20]
    window.scope.setCurrentIndex(0)
    assert len(window.target_indices()) == 45


def test_filter_authors_and_encoding_status(window):
    window.workspace = Workspace([
        Paper(1, '金融论文', '/p', authors=[Author('张三', '/a')]),
        Paper(2, '金融论文二', '/p2', authors=[Author('李四', '/b', au_code='001')]),
    ])
    window.filter_input.setText('张三')
    assert len(window.filtered_papers) == 1
    window.filter_input.clear()
    window.view_group.button(4).click()
    assert [p.seq for p in window.filtered_papers] == [1]


def test_import_and_async_author_task_autosaves(window, monkeypatch, tmp_path, app):
    path = tmp_path / 'papers.json'
    path.write_text(json.dumps([{'序号': 1, '标题': '测试', '详情链接': '/paper', '备注': '保留',
        '作者': [{'name': '张三', 'profile_url': '/fresh'}]}]), encoding='utf-8')
    window.open_json(str(path))
    auth = Mock()
    auth.anonymous_login.return_value.get.return_value = Mock(
        text='<input id="au-code" value="001">', encoding='utf-8')
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    window.author_btn.click()
    assert window.job is not None
    assert not window.open_btn.isEnabled()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None
    assert window.author_btn.isEnabled()
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert saved[0]['作者'][0]['au_code'] == '001'
    assert saved[0]['备注'] == '保留'
    assert not window.dirty
    auth.ip_login.assert_not_called()


def test_dialog_escapes_page_text_and_shows_code(window):
    paper = Paper(1, '<script>bad</script>', '/p', authors=[Author('张三', '/author', au_code='001')])
    dialog = DetailDialog(paper, window)
    text = dialog.browser.toPlainText()
    assert '<script>bad</script>' in text
    assert '001' in text
    dialog.close()


def test_settings_dialog_returns_values(window):
    dialog = SettingsDialog({'result_page_size': 50, 'font_size': 11}, window)
    assert dialog.values() == {'result_page_size': 50, 'font_size': 11}
    dialog.close()


def test_search_title_passes_page_arguments(monkeypatch):
    from cnki_downloader.core.search import CNKISearcher
    searcher = CNKISearcher(Mock())
    searcher.turn_page = 'token'
    searcher.search = Mock(return_value=[])
    searcher.search_by_title('测试', page=3, page_size=50)
    payload = searcher.search.call_args.kwargs['query']
    assert payload['pageNum'] == '3'
    assert payload['pageSize'] == '50'
    assert payload['turnpage'] == 'token'


def test_random_download_interval_defaults_and_persists(window, app):
    dp = window.download_panel
    assert (dp.delay_min_spin.value(), dp.delay_max_spin.value()) == (9, 11)
    dp.delay_max_spin.setValue(3)
    assert dp.delay_max_spin.value() == 9
    dp.delay_max_spin.setValue(20)
    dp.delay_min_spin.setValue(12)
    window._store_settings()
    restored = MainWindow(window.settings)
    assert restored.download_panel.delay_min_spin.value() == 12
    assert restored.download_panel.delay_max_spin.value() == 20
    restored.close()


def test_legacy_single_delay_migrates_to_equal_bounds(app, tmp_path):
    settings = QSettings(str(tmp_path/'legacy.ini'), QSettings.Format.IniFormat)
    settings.setValue('delay', 15)
    restored = MainWindow(settings)
    assert restored.download_panel.delay_min_spin.value() == 15
    assert restored.download_panel.delay_max_spin.value() == 15
    restored.close()


def test_workflow_switch_keeps_selection_and_download_action_visible(window, app):
    window.workspace = Workspace([Paper(1, '文献', '/paper')])
    window.apply_result_filter()
    window.table_view.selectRow(0)
    window.scope.setCurrentIndex(1)
    window.show()
    window.resize(1100, 760)
    window.flow_buttons[2].click()
    app.processEvents()
    assert window.download_panel.isVisible()
    assert not window.search_panel.isVisible()
    assert window.target_indices() == [0]
    button = window.download_panel.download_btn
    position = button.mapTo(window.download_panel, button.rect().bottomRight())
    assert window.download_panel.rect().contains(position)


def test_library_tabs_match_filters_and_errors_expand_log(window):
    window.workspace = Workspace([
        Paper(1, '未完成', '/p', authors=[Author('作者', '/a')]),
        Paper(2, '已下载', '/p2', authors=[Author('作者', '/b', au_code='001')], download_status='completed'),
    ])
    window.apply_result_filter()
    window.view_buttons[1].click()
    assert [p.seq for p in window.filtered_papers] == [1]
    window.view_buttons[2].click()
    assert [p.seq for p in window.filtered_papers] == [2]
    assert window.log_text.isHidden()
    window._task_failed('测试连接失败')
    assert not window.log_text.isHidden()
    assert '测试连接失败' in window.log_text.toPlainText()


def test_author_autosave_runs_outside_gui_thread(window, monkeypatch, tmp_path):
    from threading import get_ident
    path = tmp_path / 'background-save.json'
    window.workspace = Workspace([Paper(1, '论文', '/p', authors=[Author('作者', '/a')])], path=path)
    window.apply_result_filter()
    window._set_busy(False)
    auth = Mock()
    auth.anonymous_login.return_value.get.return_value = Mock(
        text='<input id="au-code" value="001">', encoding='utf-8')
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    save_threads = []
    gui_thread = get_ident()
    original_save = Workspace.save
    def save(store, *args, **kwargs):
        save_threads.append(get_ident())
        return original_save(store, *args, **kwargs)
    monkeypatch.setattr(Workspace, 'save', save)
    window.author_btn.click()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None
    assert save_threads and all(thread != gui_thread for thread in save_threads)
    assert json.loads(path.read_text(encoding='utf-8'))[0]['作者'][0]['au_code'] == '001'
    assert not window.dirty


def test_skipped_author_batch_does_not_save_or_rebuild_table(window, monkeypatch, tmp_path):
    window.workspace = Workspace([Paper(i, str(i), '/p', authors=[Author('作者', '/a', au_code='001')])
                                  for i in range(300)], path=tmp_path / 'known.json')
    window.apply_result_filter()
    window._set_busy(False)
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())
    save = Mock()
    monkeypatch.setattr(Workspace, 'save', save)
    refresh = Mock(wraps=window._refresh_results)
    monkeypatch.setattr(window, '_refresh_results', refresh)
    window.author_btn.click()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None
    save.assert_not_called()
    assert refresh.call_count <= 1


@pytest.mark.parametrize('operation', ['author', 'detail'])
def test_gui_remains_responsive_while_background_save_is_slow(window, monkeypatch, tmp_path, operation):
    from threading import Event
    from PyQt6.QtCore import QTimer
    entered, release = Event(), Event()
    window.workspace = Workspace([Paper(1, '论文', '/p', authors=[Author('作者', '/a')])],
                                 path=tmp_path / 'slow.json')
    window.apply_result_filter()
    window._set_busy(False)
    auth = Mock()
    auth.anonymous_login.return_value.get.return_value = Mock(
        text='<input id="au-code" value="001">', encoding='utf-8')
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    if operation == 'detail':
        def fetch_detail(session, paper):
            paper.abstract = '补全后的摘要'
        monkeypatch.setattr(workers, 'fetch_detail', fetch_detail)
    original_save = Workspace.save
    def slow_save(store, *args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original_save(store, *args, **kwargs)
    monkeypatch.setattr(Workspace, 'save', slow_save)
    (window.author_btn if operation == 'author' else window.detail_btn).click()
    try:
        deadline = time.monotonic() + 2
        while not entered.is_set() and time.monotonic() < deadline:
            QTest.qWait(10)
        assert entered.is_set()
        ticks = []
        QTimer.singleShot(0, lambda: ticks.append(True))
        QTest.qWait(20)
        assert ticks and window.job is not None
        window.stop_btn.click()
        assert window.job._stop.is_set()
    finally:
        release.set()
        deadline = time.monotonic() + 3
        while window.job is not None and time.monotonic() < deadline:
            QTest.qWait(10)
    assert window.job is None
    assert not window.dirty


def test_background_save_failure_preserves_memory_and_stops_requests(window, monkeypatch, tmp_path):
    path = tmp_path / 'failure.json'
    window.workspace = Workspace([Paper(i, str(i), '/p', authors=[Author(str(i), f'/a{i}')])
                                  for i in range(2)], path=path)
    window.workspace.save()
    original_file = path.read_bytes()
    window.apply_result_filter()
    window._set_busy(False)
    auth = Mock()
    auth.anonymous_login.return_value.get.return_value = Mock(
        text='<input id="au-code" value="001">', encoding='utf-8')
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    original_save = Workspace.save
    monkeypatch.setattr(Workspace, 'save', Mock(side_effect=PermissionError('文件被占用')))
    window.author_btn.click()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None
    assert window._save_failed and window.dirty
    assert window.workspace.papers[0].authors[0].au_code == '001'
    assert window.workspace.papers[1].authors[0].au_code == ''
    auth.anonymous_login.return_value.get.assert_called_once()
    assert path.read_bytes() == original_file
    monkeypatch.setattr(Workspace, 'save', original_save)
    assert window.save_workspace()
    assert not window.dirty


@pytest.mark.parametrize('already_open', [True, False])
def test_search_reuses_open_file_or_selects_initial_output(window, monkeypatch, tmp_path, already_open):
    from cnki_downloader.gui import main_window
    path = tmp_path / 'library.json'
    if already_open:
        path.write_text(json.dumps([{'标题': '已有论文', '发表时间': '2026-01-01',
            '摘要': '保留摘要', '备注': '保留', '来源': '管理世界',
            '作者': [{'name': '作者', 'au_code': '001'}]}]), encoding='utf-8')
        window.open_json(str(path))
    dialog = Mock(return_value=(str(tmp_path / 'wrong.json') if already_open else str(path), 'JSON'))
    monkeypatch.setattr(main_window.QFileDialog, 'getSaveFileName', dialog)
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())
    searcher = Mock(server_error=False)
    searcher.search_by_journal.return_value = [
        Paper(1, '已有论文', '/fresh', source='管理世界', publish_date='2026-01-01'),
        Paper(2, '新增论文', '/new', source='管理世界', publish_date='2026-01-02')]
    monkeypatch.setattr(workers, 'CNKISearcher', Mock(return_value=searcher))
    window.search_panel.keyword.setText('管理世界')
    window.search_panel.page_count.setValue(1)
    window.search_panel.search_btn.click()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None
    if already_open:
        dialog.assert_not_called()
    else:
        dialog.assert_called_once()
    assert window.workspace.path == path.resolve()
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert len(saved) == 2
    if already_open:
        old = next(row for row in saved if row['标题'] == '已有论文')
        assert old['摘要'] == '保留摘要'
        assert old['作者'][0]['au_code'] == '001'
        assert old['备注'] == '保留'
        assert old['详情链接'] == '/fresh'
    assert not (tmp_path / 'wrong.json').exists()


@pytest.mark.parametrize('failure', [False, True])
def test_search_stages_pages_until_success(window, monkeypatch, tmp_path, failure):
    from threading import Event
    path = tmp_path / 'transaction.json'
    path.write_text(json.dumps([{'标题': '原论文', '发表时间': '2026-01-01',
        '来源': '期刊', '备注': '保留', '作者': []}]), encoding='utf-8')
    original = path.read_bytes()
    window.open_json(str(path))
    window.search_panel.keyword.setText('期刊')
    window.search_panel.page_count.setValue(2)
    entered, release = Event(), Event()
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())
    searcher = Mock(server_error=False)
    def page(keyword, page, page_size):
        if page == 1:
            return [Paper(1, '新论文', '/new', source='期刊', publish_date='2026-01-02')]
        entered.set()
        assert release.wait(3)
        if failure:
            raise TimeoutError('模拟检索中断')
        return []
    searcher.search_by_journal.side_effect = page
    monkeypatch.setattr(workers, 'CNKISearcher', Mock(return_value=searcher))
    window.search_panel.search_btn.click()
    try:
        deadline = time.monotonic() + 2
        while not entered.is_set() and time.monotonic() < deadline:
            QTest.qWait(10)
        assert entered.is_set()
        QTest.qWait(20)
        assert path.read_bytes() == original
        staged = list(tmp_path.glob('transaction.json.*.search.json'))
        assert len(staged) == 1
        assert len(json.loads(staged[0].read_text(encoding='utf-8'))) == 2
    finally:
        release.set()
        deadline = time.monotonic() + 3
        while window.job is not None and time.monotonic() < deadline:
            QTest.qWait(10)
    assert window.job is None
    if failure:
        assert path.read_bytes() == original
        assert staged[0].exists()
        assert window.dirty
        # 测试结束前显式另存恢复，避免关闭窗口触发保存原文件。
        window.workspace.save(tmp_path / 'recovered.json')
        window.dirty = False
    else:
        assert len(json.loads(path.read_text(encoding='utf-8'))) == 2
        assert not staged[0].exists()
        assert not window.dirty


@pytest.mark.parametrize(('label', 'status_index', 'expected'), [
    ('全部文献', 0, [1, 2, 3]),
    ('编码待补全', 4, [1]),
    ('已下载', 2, [2]),
    ('待下载', 1, [1]),
    ('下载失败', 3, [3]),
])
def test_all_status_shortcuts_filter_results(window, label, status_index, expected):
    window.workspace = Workspace([
        Paper(1, '待处理', '/p', authors=[Author('作者', '/a')]),
        Paper(2, '已完成', '/p2', authors=[Author('作者', '/b', au_code='001')],
              download_status='completed'),
        Paper(3, '失败', '/p3', authors=[Author('作者', '/c', au_code='002')],
              download_status='failed'),
    ])
    window.apply_result_filter()
    button = next(b for b in window.view_buttons if b.text() == label)
    button.click()
    assert window.view_group.checkedId() == status_index
    assert [p.seq for p in window.filtered_papers] == expected
    window.view_group.button((status_index + 1) % 5).click()
    button.click()
    assert button.isChecked()
    assert sum(b.isChecked() for b in window.view_buttons) == 1
    window.filter_input.setText('不存在')
    assert not window.filtered_papers
    window.filter_input.clear()
    assert [p.seq for p in window.filtered_papers] == expected


@pytest.mark.parametrize('width', [1100, 1440])
def test_library_header_and_search_layout(window, app, width):
    from PyQt6.QtWidgets import QLabel
    window.file_label.setText('文献库文件名较长的示例.json')
    window.show()
    window.resize(width, 900)
    app.processEvents()
    title = next(label for label in window.findChildren(QLabel)
                 if label.objectName() == 'pageTitle')
    title_rect = title.geometry()
    file_rect = window.file_label.geometry()
    assert file_rect.left() > title_rect.right()
    assert title_rect.top() <= file_rect.center().y() <= title_rect.bottom()
    search_rect = window.filter_input.geometry()
    sort_rect = window.sort_combo.geometry()
    assert search_rect.right() < sort_rect.left()
    assert search_rect.top() <= sort_rect.center().y() <= search_rect.bottom()
    for button in window.view_buttons:
        assert button.isVisible()
        assert button.width() >= button.sizeHint().width()
        if window.results_area.width() >= 760:
            assert button.geometry().top() <= sort_rect.center().y() <= button.geometry().bottom()
            assert button.geometry().right() < search_rect.left()
        else:
            assert button.geometry().bottom() < search_rect.top()
    from PyQt6.QtWidgets import QComboBox
    assert all(combo.findText('全部状态') == -1 for combo in window.findChildren(QComboBox))


@pytest.mark.parametrize('size', [(860, 540), (1100, 760), (1600, 1000)])
def test_resizable_regions_and_responsive_controls(window, app, size):
    window.show()
    window.resize(*size)
    window._set_log_visible(True)
    app.processEvents()
    assert window.size().width() == size[0]
    assert window.size().height() == size[1]
    for index in range(3):
        window.flow_buttons[index].click()
        app.processEvents()
        assert window.sidebar_scroll.verticalScrollBar().maximum() >= 0
    for widget in [window.filter_input, window.sort_combo, window.scope,
                   window.next_btn, window.stop_btn, *window.view_buttons]:
        assert widget.isVisible()
        point = widget.mapTo(window.centralWidget(), widget.rect().bottomRight())
        assert window.centralWidget().rect().contains(point)
    previous = window.body_splitter.sizes()[0]
    window.body_splitter.setSizes([previous + 70, window.width() - previous - 70])
    app.processEvents()
    assert window.body_splitter.sizes()[0] > previous
    window.content_splitter.setSizes([350, 300])
    app.processEvents()
    assert window.log_text.height() >= 70
    if size[1] >= 760:
        assert window.log_text.height() > 70
    window.sidebar_scroll.ensureWidgetVisible(window.download_panel.download_btn)
    app.processEvents()
    point = window.download_panel.download_btn.mapTo(window.sidebar_scroll.viewport(),
        window.download_panel.download_btn.rect().center())
    assert window.sidebar_scroll.viewport().rect().contains(point)


def test_splitter_sizes_are_restored(window, app):
    window.show()
    window.resize(1440, 900)
    window._set_log_visible(True)
    window.body_splitter.setSizes([350, 1080])
    window.content_splitter.setSizes([450, 300])
    app.processEvents()
    window._store_settings()
    restored = MainWindow(window.settings)
    restored.show()
    app.processEvents()
    assert abs(restored.body_splitter.sizes()[0] - window.body_splitter.sizes()[0]) < 15
    assert restored.log_toggle.isChecked()
    available = sum(restored.content_splitter.sizes()) - restored.results_area.minimumSizeHint().height()
    expected = min(window.content_splitter.sizes()[1], available)
    assert abs(restored.content_splitter.sizes()[1] - expected) < 15
    restored.close()


def test_log_splitter_can_only_be_dragged_when_log_is_open(window, app):
    from PyQt6.QtCore import QPoint
    window.show()
    window.resize(1440, 900)
    app.processEvents()
    handle = window.content_splitter.handle(1)
    assert not handle.isEnabled()
    before = window.content_splitter.sizes()
    center = handle.rect().center()
    QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(handle, center - QPoint(0, 100))
    QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=center - QPoint(0, 100))
    app.processEvents()
    assert window.content_splitter.sizes() == before
    window.log_toggle.click()
    app.processEvents()
    assert handle.isEnabled()
    window.content_splitter.setSizes([450, 260])
    app.processEvents()
    expanded_height = window.content_splitter.sizes()[1]
    window.log_toggle.click()
    app.processEvents()
    assert not handle.isEnabled()
    assert window.content_splitter.sizes()[1] < expanded_height
    window.log_toggle.click()
    app.processEvents()
    assert handle.isEnabled()
    assert abs(window.content_splitter.sizes()[1] - expanded_height) < 5


@pytest.mark.parametrize('entry', ['button', 'menu'])
def test_export_log_preserves_chinese_and_timestamps(window, monkeypatch, tmp_path, entry):
    from cnki_downloader.gui import main_window
    window.append_log('📄 共 3098 篇论文')
    window.append_log('   ✅ 下载成功：论文.pdf')
    expected = window.log_text.toPlainText() + '\n'
    path = tmp_path / '日志.txt'
    monkeypatch.setattr(main_window.QFileDialog, 'getSaveFileName', Mock(return_value=(str(path), '')))
    if entry == 'button':
        window.export_log_btn.click()
    else:
        window.export_log_action.trigger()
    assert path.read_text(encoding='utf-8-sig') == expected
    assert '日志已导出' in window.log_text.toPlainText()


def test_export_log_cancel_and_failure_preserve_logs(window, monkeypatch, tmp_path):
    from cnki_downloader.gui import main_window
    window.append_log('原始日志')
    expected = window.log_text.toPlainText()
    dialog = Mock(return_value=('', ''))
    monkeypatch.setattr(main_window.QFileDialog, 'getSaveFileName', dialog)
    assert not window.export_log()
    dialog.return_value = (str(tmp_path / 'missing' / 'log.txt'), '')
    warning = Mock()
    monkeypatch.setattr(main_window.QMessageBox, 'warning', warning)
    assert not window.export_log()
    warning.assert_called_once()
    assert window.log_text.toPlainText() == expected


def test_empty_log_export_explains_empty_state(window, monkeypatch):
    from cnki_downloader.gui import main_window
    info = Mock()
    dialog = Mock()
    monkeypatch.setattr(main_window.QMessageBox, 'information', info)
    monkeypatch.setattr(main_window.QFileDialog, 'getSaveFileName', dialog)
    assert not window.export_log()
    info.assert_called_once()
    dialog.assert_not_called()


def test_github_icon_opens_project(window, monkeypatch):
    from cnki_downloader.gui import main_window
    open_url = Mock()
    monkeypatch.setattr(main_window, 'open_web_url', open_url)
    assert not window.github_btn.icon().isNull()
    window.github_btn.click()
    open_url.assert_called_once_with('https://github.com/ZHOUoutlook/cnki_downloader')


def test_open_download_directory_uses_current_folder(window, monkeypatch, tmp_path):
    from cnki_downloader.gui import download_panel
    open_url = Mock(return_value=True)
    monkeypatch.setattr(download_panel.QDesktopServices, 'openUrl', open_url)
    window.download_panel.output_dir.setText(str(tmp_path))
    window.download_panel.open_dir_btn.click()
    url = open_url.call_args.args[0]
    assert Path(url.toLocalFile()) == tmp_path.resolve()


@pytest.mark.parametrize('value', ['', 'missing-folder'])
def test_open_missing_download_directory_explains_state(window, monkeypatch, tmp_path, value):
    from cnki_downloader.gui import download_panel
    open_url = Mock()
    info = Mock()
    monkeypatch.setattr(download_panel.QDesktopServices, 'openUrl', open_url)
    monkeypatch.setattr(download_panel.QMessageBox, 'information', info)
    window.download_panel.output_dir.setText(str(tmp_path / value) if value else '')
    window.download_panel.open_dir_btn.click()
    open_url.assert_not_called()
    info.assert_called_once()


@pytest.mark.parametrize('ip_ok', [True, False])
def test_check_network_displays_anonymous_and_ip_results(window, app, monkeypatch, ip_ok):
    anonymous, campus = Mock(), Mock()
    if not ip_ok:
        campus.ip_login.side_effect = ConnectionError('当前 IP 无授权')
    monkeypatch.setattr(workers, 'CNKIAuth', Mock(side_effect=[anonymous, campus]))
    window.network_btn.click()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None
    assert '匿名正常' in window.network_label.text()
    assert ('IP已授权' if ip_ok else 'IP不可用') in window.network_label.text()
    assert window.network_btn.isEnabled()
    assert 'IP（校园网）' in window.log_text.toPlainText()
    if not ip_ok:
        assert '当前 IP 无授权' in window.log_text.toPlainText()
        assert not window.log_text.isHidden()
