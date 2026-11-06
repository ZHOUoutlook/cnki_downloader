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
