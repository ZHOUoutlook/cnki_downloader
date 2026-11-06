"""用真实 Qt 按钮、后台线程和事件循环验证作者链接刷新与验证恢复。"""
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
from PyQt6.QtCore import QSettings
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from cnki_downloader.core import enrichment
from cnki_downloader.gui import workers
from cnki_downloader.gui.main_window import MainWindow
from cnki_downloader.gui.workspace import Workspace
from cnki_downloader.models import Paper


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    win = MainWindow(QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat))
    yield win
    if win.job is not None:
        win.job.cancel()
        win.job.wait(3000)
        QTest.qWait(10)
    win.dirty = False
    win.close()


def response(text):
    return Mock(text=text, status_code=200, encoding='utf-8')


def run_button(window, button):
    button.click()
    deadline = time.monotonic() + 3
    while window.job is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.job is None


def load_rows(window, path, rows):
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    window.workspace = Workspace.load(path)
    window.apply_result_filter()
    window._set_busy(False)


def test_detail_button_updates_author_url_without_research(window, tmp_path, monkeypatch):
    path = tmp_path / 'details.json'
    load_rows(window, path, [{'标题': '论文', '详情链接': '/original-detail',
        '摘要': '摘要', '卷号': '2026', '期号': '1', '备注': '保留',
        '作者': [{'name': '作者', 'profile_url': '/old-author', 'au_code': ''}]}])
    session = Mock()
    session.get.return_value = response(
        '<div class="wx-tit"><h3 class="author"><span><a href="/fresh-author">作者</a></span></h3></div>')
    monkeypatch.setattr(workers, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    search = Mock()
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    run_button(window, window.detail_btn)
    search.assert_not_called()
    assert [c.args[0] for c in session.get.call_args_list] == ['https://kns.cnki.net/original-detail']
    saved = json.loads(path.read_text(encoding='utf-8'))[0]
    assert saved['详情链接'] == '/original-detail'
    assert saved['作者'][0]['profile_url'] == '/fresh-author'
    assert saved['备注'] == '保留'
    assert window.all_papers[0].authors[0].profile_url == '/fresh-author'
    assert not window.dirty
    session.close.assert_called_once()


@pytest.mark.parametrize('outcome', ['success', 'retry_blocked', 'detail_blocked', 'no_match'])
def test_author_button_recovers_or_stops_and_saves_partial_results(window, tmp_path, monkeypatch, outcome):
    path = tmp_path / 'authors.json'
    load_rows(window, path, [
        {'标题': '论文', '详情链接': '/old-detail', '来源': '管理世界', '发表时间': '2026-01-01',
         '备注': '保留', '作者': [{'name': '一', 'profile_url': '/a', '额外': '保留'},
             {'name': '二', 'profile_url': '/b'}, {'name': '三', 'profile_url': '/c'}]},
        {'标题': '后续论文', '详情链接': '/next-paper', '作者': [
            {'name': '后续作者', 'profile_url': '/next-author', 'au_code': '004' if outcome == 'success' else ''}]}])
    search = Mock(return_value=[] if outcome == 'no_match' else [
        Paper(1, '论文', '/fresh-detail', source='管理世界', publish_date='2026-01-01')])
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    session = Mock()
    fresh_detail = response('<div class="wx-tit"><h3 class="author">'
        '<span><a href="/fresh-b">二</a></span><span><a href="/fresh-c">三</a></span></h3></div>')
    session.get.side_effect = [response('<input id="au-code" value="001">'),
        response('<title>安全验证</title>'),
        response('<title>安全验证</title>') if outcome == 'detail_blocked' else fresh_detail,
        response('<title>安全验证</title>') if outcome == 'retry_blocked' else response('<input id="au-code" value="002">'),
        response('<input id="au-code" value="003">')]
    monkeypatch.setattr(workers, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    run_button(window, window.author_btn)
    search.assert_called_once_with('论文')
    urls = [c.args[0] for c in session.get.call_args_list]
    expected = ['https://kns.cnki.net/a', 'https://kns.cnki.net/b']
    if outcome != 'no_match':
        expected.append('https://kns.cnki.net/fresh-detail')
    if outcome in ('success', 'retry_blocked'):
        expected.append('https://kns.cnki.net/fresh-b')
    if outcome == 'success':
        expected.append('https://kns.cnki.net/fresh-c')
    assert urls == expected
    saved = json.loads(path.read_text(encoding='utf-8'))[0]
    assert saved['作者'][0]['au_code'] == '001'
    assert saved['作者'][0]['额外'] == '保留'
    assert saved['备注'] == '保留'
    refreshed = outcome in ('success', 'retry_blocked')
    assert saved['详情链接'] == ('https://kns.cnki.net/fresh-detail' if refreshed else '/old-detail')
    assert saved['作者'][1]['profile_url'] == ('/fresh-b' if refreshed else '/b')
    assert window.all_papers[0].authors[0].au_code == '001'
    if outcome == 'success':
        assert [a['au_code'] for a in saved['作者']] == ['001', '002', '003']
        assert '任务完成' in window.task_label.text()
    else:
        assert '任务失败' in window.task_label.text()
        assert not window.log_text.isHidden()
    assert not window.dirty
    session.close.assert_called_once()
