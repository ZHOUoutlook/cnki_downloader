import os
import sys
from pathlib import Path
from threading import Thread, Event
from unittest.mock import Mock

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
pytest.importorskip('PyQt6')
from PyQt6.QtWidgets import QApplication
from cnki_downloader.gui import workers
from cnki_downloader.models import Paper, Author


@pytest.fixture(scope='module', autouse=True)
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


def test_stop_wakes_paused_checkpoint():
    worker = workers.TaskWorker()
    worker.set_paused(True)
    entered, stopped = Event(), Event()
    def run():
        entered.set()
        try:
            worker.checkpoint()
        except workers.TaskStopped:
            stopped.set()
    thread = Thread(target=run)
    thread.start()
    assert entered.wait(1)
    assert not stopped.wait(0.05)
    worker.cancel()
    thread.join(1)
    assert stopped.is_set()


def test_search_preserves_first_page_when_stopped(monkeypatch):
    auth = Mock()
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    searcher = Mock(server_error=False)
    searcher.search_by_journal.return_value = [Paper(1, '测试', '/paper', source='期刊')]
    monkeypatch.setattr(workers, 'CNKISearcher', lambda session: searcher)
    worker = workers.SearchWorker('journal', '期刊', 3, 20)
    results = []
    worker.papers_loaded.connect(lambda papers: (results.extend(papers), worker.cancel()))
    worker.run()
    assert len(results) == 1
    assert searcher.search_by_journal.call_count == 1
    auth.anonymous_login.assert_called_once()
    auth.ip_login.assert_not_called()


def test_author_task_uses_anonymous_and_does_not_mutate_input(monkeypatch):
    auth = Mock()
    auth.anonymous_login.return_value.get.return_value = Mock(
        text='<input id="au-code" value="001">', encoding='utf-8')
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    paper = Paper(1, '测试', '/paper', authors=[Author('作者', '/author')])
    worker = workers.PaperTaskWorker('author', [paper], delay=0)
    updates = []
    worker.paper_updated.connect(lambda i, p: updates.append(p))
    worker.run()
    assert updates[0].authors[0].au_code == '001'
    assert paper.authors[0].au_code == ''
    auth.ip_login.assert_not_called()


@pytest.mark.parametrize('first_result', [None, TimeoutError('请求超时')])
def test_download_retries_then_saves_success(monkeypatch, tmp_path, first_result):
    auth = Mock()
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    downloader = Mock()
    path = str(tmp_path / 'paper.pdf')
    downloader.download.side_effect = [first_result, path]
    monkeypatch.setattr(workers, 'PDFDownloader', lambda *args, **kwargs: downloader)
    worker = workers.PaperTaskWorker('download', [Paper(1, '测试', '/paper')], delay=0, retries=1)
    updates, progress = [], []
    worker.paper_updated.connect(lambda i, p: updates.append(p))
    worker.progress.connect(lambda *args: progress.append(args))
    worker.run()
    auth.ip_login.assert_called_once()
    auth.anonymous_login.assert_not_called()
    assert downloader.download.call_count == 2
    assert updates[0].local_pdf_path == path
    assert updates[0].download_status == 'completed'
    assert progress[-1] == (1, 1, 1, 0, 0)


def test_download_rejected_login_closes_returned_session(monkeypatch):
    auth = Mock()
    auth.is_authenticated.return_value = False
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    worker = workers.PaperTaskWorker('download', [Paper(1, '论文', '/paper')])
    failures = []
    worker.failed.connect(failures.append)
    worker.run()
    assert failures
    auth.ip_login.return_value.close.assert_called_once()


def test_download_samples_new_random_delay_for_retry_and_each_paper(monkeypatch, tmp_path):
    auth = Mock()
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    downloader = Mock()
    downloader.download.side_effect = [None, str(tmp_path/'1.pdf'), str(tmp_path/'2.pdf'), str(tmp_path/'3.pdf')]
    monkeypatch.setattr(workers, 'PDFDownloader', lambda *args, **kwargs: downloader)
    uniform = Mock(side_effect=[10.25, 9.75, 11.5])
    monkeypatch.setattr(workers.random, 'uniform', uniform)
    worker = workers.PaperTaskWorker('download', [Paper(i, str(i), '/p') for i in range(3)],
                                    delay=9, delay_max=12, retries=1)
    worker.delay = Mock()
    worker.run()
    assert [c.args for c in uniform.call_args_list] == [(9, 12)] * 3
    assert [c.args[0] for c in worker.delay.call_args_list] == [10.25, 9.75, 11.5]
    assert downloader.download.call_count == 4


@pytest.mark.parametrize('minimum, maximum', [(-1, 3), (12, 9)])
def test_invalid_random_delay_range_is_rejected(minimum, maximum):
    with pytest.raises(ValueError):
        workers.PaperTaskWorker('download', [], delay=minimum, delay_max=maximum)


def test_completed_authors_do_not_emit_redundant_updates(monkeypatch):
    auth = Mock()
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    papers = [Paper(i, str(i), '/p', authors=[Author('作者', '/a', au_code='001')]) for i in range(300)]
    worker = workers.PaperTaskWorker('author', papers, delay=0)
    updates = []
    worker.paper_updated.connect(lambda *args: updates.append(args))
    worker.run()
    assert updates == []
    auth.anonymous_login.return_value.get.assert_not_called()


def test_download_filters_existing_files_before_limit_and_logs_steps(monkeypatch, tmp_path):
    import json
    from cnki_downloader.gui.workspace import Workspace
    existing = tmp_path / '已有_.pdf'
    existing.write_bytes(b'existing')
    (tmp_path / '已有CAJ_.caj').write_bytes(b'existing')
    papers = [Paper(1, '已有', '/p'), Paper(2, '无链接', ''),
              Paper(3, '视频', '/p', db_type='视频'), Paper(4, '已有CAJ', '/p'),
              Paper(2939, '待下载', '/p'), Paper(2940, '下一个', '/p')]
    store = Workspace(papers, path=tmp_path / 'library.json')
    store.save()
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())

    class Downloader:
        def __init__(self, session, output_dir, auth=None, log=None):
            self.log = log

        def download(self, paper):
            assert paper.seq == 2939
            self.log('   获取详情页...')
            self.log('   解析下载链接...')
            return str(tmp_path / 'new.pdf')

    monkeypatch.setattr(workers, 'PDFDownloader', Downloader)
    worker = workers.PaperTaskWorker('download', papers, output_dir=str(tmp_path),
                                    workspace=store, delay=0, limit=1)
    logs, updates = [], []
    worker.log.connect(logs.append)
    worker.paper_updated.connect(lambda i, p: updates.append((i, p)))
    worker.wait_interval = Mock()
    worker.run()
    assert '📄 共 6 篇论文，2 篇有详情链接且还没下载' in logs
    assert '[1/1] 📥 [2939] 待下载' in logs
    assert '   获取详情页...' not in logs
    assert '   解析下载链接...' not in logs
    worker.wait_interval.assert_not_called()
    saved = json.loads(store.path.read_text(encoding='utf-8'))
    assert saved[0]['下载状态'] == saved[3]['下载状态'] == saved[4]['下载状态'] == 'completed'
    assert saved[1]['下载状态'] == saved[2]['下载状态'] == saved[5]['下载状态'] == 'pending'
    assert [i for i, _ in updates] == [0, 3, 4]


def test_download_reconciles_json_with_output_files_before_login(monkeypatch, tmp_path):
    import json
    from cnki_downloader.gui.workspace import Workspace
    output = tmp_path / 'downloads'
    output.mkdir()
    (output / '已有PDF_20261106.pdf').write_bytes(b'pdf')
    (output / '已有CAJ_.caj').write_bytes(b'caj')
    old_file = tmp_path / 'old-location.pdf'
    old_file.write_bytes(b'old')
    store = Workspace([
        Paper(1, '已有PDF', '/p', publish_date='2026-11-06', download_status='failed'),
        Paper(2, '已有CAJ', '/p'),
        Paper(3, '旧目录文件', '/p', local_pdf_path=str(old_file), download_status='completed'),
        Paper(4, '无详情', '', local_pdf_path=str(tmp_path / 'missing.pdf'), download_status='completed'),
        Paper(5, '文件已删除', '/p', local_pdf_path=str(tmp_path / 'deleted.pdf'), download_status='completed'),
        Paper(6, '未下载', '/p'),
    ], path=tmp_path / 'library.json')
    store.save()
    store = Workspace.load(store.path)
    auth = Mock()
    auth.is_authenticated.return_value = False

    def login():
        # 即使随后登录失败，校验结果也必须先完整保存到 JSON。
        rows = json.loads(store.path.read_text(encoding='utf-8'))
        assert rows[0]['下载状态'] == rows[1]['下载状态'] == 'completed'
        assert rows[0]['本地PDF路径'] == str(output / '已有PDF_20261106.pdf')
        assert rows[1]['本地PDF路径'] == str(output / '已有CAJ_.caj')
        for row in rows[2:]:
            assert row['下载状态'] == 'pending'
            assert not row.get('本地PDF路径')
        return Mock()

    auth.ip_login.side_effect = login
    monkeypatch.setattr(workers, 'CNKIAuth', lambda: auth)
    worker = workers.PaperTaskWorker('download', store.papers, workspace=store,
                                    output_dir=str(output), delay=0, limit=1)
    logs, failures = [], []
    worker.log.connect(logs.append)
    worker.failed.connect(failures.append)
    worker.run()
    assert '📄 共 6 篇论文，3 篇有详情链接且还没下载' in logs
    auth.ip_login.assert_called_once()
    assert failures == ['下载需要知网授权 IP，请检查校园网连接']


def test_real_downloader_gui_log_contains_only_progress_and_result(monkeypatch, tmp_path):
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())
    monkeypatch.setattr(workers.PDFDownloader, '_get_detail_page', Mock(return_value='<html>详情</html>'))
    monkeypatch.setattr(workers.PDFDownloader, '_extract_pdf_url', Mock(return_value='https://example.com/p.pdf'))
    monkeypatch.setattr(workers.PDFDownloader, '_download_file', Mock(return_value=True))
    paper = Paper(2939, '论文', '/paper')
    worker = workers.PaperTaskWorker('download', [paper], output_dir=str(tmp_path), delay=0)
    logs, updates = [], []
    worker.log.connect(logs.append)
    worker.paper_updated.connect(lambda i, p: updates.append(p))
    worker.run()
    assert '📄 共 1 篇论文，1 篇有详情链接且还没下载' in logs
    assert '[1/1] 📥 [2939] 论文' in logs
    assert len(logs) == 3  # 统计、单篇进度、下载结果。
    assert any('下载成功' in line for line in logs)
    assert updates[0].download_status == 'completed'


def test_download_wait_is_silent_and_warnings_remain_visible():
    worker = workers.PaperTaskWorker('download', [], delay=9, delay_max=11)
    worker.delay = Mock()
    logs = []
    worker.log.connect(logs.append)
    worker.wait_interval()
    assert logs == []
    seconds = worker.delay.call_args.args[0]
    assert 9 <= seconds <= 11
    worker._download_log('   ❌ 未找到下载链接')
    worker._download_log('   ⚠️ 下载时需要重新登录')
    assert logs == ['   ❌ 未找到下载链接', '   ⚠️ 下载时需要重新登录']


def test_empty_download_queue_does_not_login_or_wait(monkeypatch, tmp_path):
    auth = Mock()
    monkeypatch.setattr(workers, 'CNKIAuth', auth)
    worker = workers.PaperTaskWorker('download', [Paper(1, '无链接', '')],
                                    output_dir=str(tmp_path), delay=10)
    worker.wait_interval = Mock()
    messages = []
    worker.completed.connect(messages.append)
    worker.run()
    auth.assert_not_called()
    worker.wait_interval.assert_not_called()
    assert messages and '没有需要下载' in messages[0]


@pytest.mark.parametrize('operation', ['detail', 'author'])
def test_task_snapshot_is_copied_in_worker_thread(monkeypatch, tmp_path, operation):
    from threading import get_ident
    from cnki_downloader.gui.workspace import Workspace
    gui_thread = get_ident()
    threads = []
    original = workers.deepcopy

    def copy_in_background(value):
        threads.append(get_ident())
        return original(value)

    monkeypatch.setattr(workers, 'deepcopy', copy_in_background)
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())
    paper = Paper(1, '论文', '', authors=[Author('作者', '/a', au_code='001')])
    store = Workspace([paper], path=tmp_path / 'papers.json')
    worker = workers.PaperTaskWorker(operation, [paper], workspace=store, delay=0)
    worker.start()
    assert worker.wait(3000)
    assert threads and all(thread != gui_thread for thread in threads)
    assert store.papers[0] is paper



def test_stopped_search_keeps_original_and_staging_result(monkeypatch, tmp_path):
    import json
    from cnki_downloader.gui.workspace import Workspace
    path = tmp_path / 'stopped.json'
    path.write_text('[{"标题": "旧论文"}]', encoding='utf-8')
    original = path.read_bytes()
    monkeypatch.setattr(workers, 'CNKIAuth', Mock())
    searcher = Mock(server_error=False)
    searcher.search_by_journal.return_value = [Paper(1, '新论文', '/p', source='期刊')]
    monkeypatch.setattr(workers, 'CNKISearcher', lambda session: searcher)
    worker = workers.SearchWorker('journal', '期刊', 3, 20, workspace=Workspace.load(path))
    ready = []
    worker.workspace_ready.connect(lambda store, committed: ready.append((store, committed)))
    worker.papers_loaded.connect(lambda papers: worker.cancel())
    worker.run()
    assert path.read_bytes() == original
    staged = list(tmp_path.glob('stopped.json.*.search.json'))
    assert len(staged) == 1
    assert len(json.loads(staged[0].read_text(encoding='utf-8'))) == 2
    assert len(ready) == 1 and not ready[0][1]
    assert ready[0][0].path == path


@pytest.mark.parametrize(('anonymous_ok', 'ip_ok'), [(True, True), (True, False), (False, True), (False, False)])
def test_connection_check_reports_both_modes(monkeypatch, anonymous_ok, ip_ok):
    anonymous, campus = Mock(), Mock()
    if not anonymous_ok:
        anonymous.anonymous_login.side_effect = ConnectionError('匿名网络异常')
    if not ip_ok:
        campus.ip_login.side_effect = ConnectionError('当前 IP 无授权')
    monkeypatch.setattr(workers, 'CNKIAuth', Mock(side_effect=[anonymous, campus]))
    worker = workers.AuthCheckWorker()
    results, completed, failures = [], [], []
    worker.checked.connect(lambda *args: results.append(args))
    worker.completed.connect(completed.append)
    worker.failed.connect(failures.append)
    worker.run()
    assert [(mode, ok) for mode, ok, detail in results] == [(False, anonymous_ok), (True, ip_ok)]
    assert completed and not failures
    if anonymous_ok:
        anonymous.anonymous_login.return_value.close.assert_called_once()
    if ip_ok:
        campus.ip_login.return_value.close.assert_called_once()
    else:
        assert '当前 IP 无授权' in results[1][2]


def test_connection_check_rejects_unauthenticated_ip_session(monkeypatch):
    anonymous, campus = Mock(), Mock()
    campus.is_authenticated.return_value = False
    monkeypatch.setattr(workers, 'CNKIAuth', Mock(side_effect=[anonymous, campus]))
    worker = workers.AuthCheckWorker()
    results = []
    worker.checked.connect(lambda *args: results.append(args))
    worker.run()
    assert results[1][0:2] == (True, False)
    campus.ip_login.return_value.close.assert_called_once()


def test_connection_check_can_stop_before_ip_login(monkeypatch):
    auth = Mock()
    factory = Mock(return_value=auth)
    monkeypatch.setattr(workers, 'CNKIAuth', factory)
    worker = workers.AuthCheckWorker()
    results, completed = [], []
    worker.checked.connect(lambda *args: (results.append(args), worker.cancel()))
    worker.completed.connect(completed.append)
    worker.run()
    assert len(results) == 1
    auth.ip_login.assert_not_called()
    auth.anonymous_login.return_value.close.assert_called_once()
    assert completed == ['连接检查已停止']
