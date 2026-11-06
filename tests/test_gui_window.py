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
    window.status_filter.setCurrentIndex(4)
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
