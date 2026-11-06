"""可协作停止的后台任务；任务独占会话并处理文献副本。"""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from threading import Event
import time
import random

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.auth import CNKIAuth
from ..core.search import CNKISearcher
from ..core.pagination import build_warmup_pages
from ..core.enrichment import needs_detail, fetch_detail, fetch_codes
from ..downloaders import PDFDownloader


class TaskStopped(Exception):
    pass


class TaskWorker(QThread):
    log = pyqtSignal(str)
    failed = pyqtSignal(str)
    completed = pyqtSignal(str)
    progress = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = Event()
        self._resume = Event()
        self._resume.set()

    def cancel(self):
        self._stop.set()
        self._resume.set()

    def set_paused(self, paused):
        self._resume.clear() if paused else self._resume.set()

    def checkpoint(self):
        while not self._resume.wait(0.1):
            if self._stop.is_set():
                raise TaskStopped()
        if self._stop.is_set():
            raise TaskStopped()

    def delay(self, seconds):
        remaining = seconds
        while remaining > 0:
            self.checkpoint()
            step = min(remaining, 0.1)
            start = time.monotonic()
            if self._stop.wait(step):
                raise TaskStopped()
            remaining -= time.monotonic() - start

    def login(self, download=False):
        self.checkpoint()
        auth = CNKIAuth()
        # 核心认证输出包含 cookies，不显示在 GUI 日志中。
        with redirect_stdout(StringIO()):
            session = auth.ip_login() if download else auth.anonymous_login()
        if session is None or (download and not auth.is_authenticated()):
            if session is not None:
                session.close()
            raise ConnectionError('下载需要知网授权 IP，请检查校园网连接' if download else '匿名会话初始化失败')
        return auth, session


class AuthCheckWorker(TaskWorker):
    succeeded = pyqtSignal()

    def run(self):
        session = None
        try:
            _, session = self.login()
            self.succeeded.emit()
        except TaskStopped:
            pass
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if session is not None:
                session.close()


class SearchWorker(TaskWorker):
    papers_loaded = pyqtSignal(list)

    def __init__(self, search_type, keyword, page_count, page_size, start_page=1, parent=None):
        super().__init__(parent)
        self.search_type, self.keyword = search_type, keyword
        self.page_count, self.page_size, self.start_page = page_count, page_size, start_page

    def run(self):
        session = None
        count = 0
        try:
            _, session = self.login()
            searcher = CNKISearcher(session)
            if self.start_page > 1:
                for page in build_warmup_pages(self.start_page):
                    self.checkpoint()
                    self.log.emit(f'正在准备第 {page} 页的翻页信息…')
                    with redirect_stdout(StringIO()):
                        search = searcher.search_by_title if self.search_type == 'title' else searcher.search_by_journal
                        papers = search(self.keyword, page=page, page_size=self.page_size)
                    if not papers or searcher.server_error:
                        raise RuntimeError(f'第 {page} 页预热失败，请重试或减小起始页')
            for offset in range(self.page_count):
                self.checkpoint()
                page = self.start_page + offset
                self.log.emit(f'正在搜索第 {page} 页…')
                with redirect_stdout(StringIO()):
                    if self.search_type == 'title':
                        papers = searcher.search_by_title(self.keyword, page=page, page_size=self.page_size)
                    else:
                        papers = searcher.search_by_journal(self.keyword, page=page, page_size=self.page_size)
                if searcher.server_error:
                    raise RuntimeError(f'第 {page} 页服务异常，已获取结果已保留，请稍后重试')
                if not papers:
                    break
                if self.search_type == 'journal':
                    papers = [p for p in papers if p.source == self.keyword]
                count += len(papers)
                self.papers_loaded.emit(papers)
                self.progress.emit(offset + 1, self.page_count, count, 0, 0)
            self.completed.emit(f'搜索完成，获取 {count} 篇文献')
        except TaskStopped:
            self.completed.emit(f'搜索已停止，保留已获取的 {count} 篇文献')
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if session is not None:
                session.close()


class PaperTaskWorker(TaskWorker):
    paper_updated = pyqtSignal(int, object)

    def __init__(self, operation, papers, output_dir='', delay=10, retries=3, parent=None, delay_max=None):
        super().__init__(parent)
        self.operation = operation
        self.papers = deepcopy(papers)
        self.output_dir, self.retries = output_dir, retries
        self.interval_min = float(delay)
        self.interval_max = float(delay if delay_max is None else delay_max)
        if not 0 <= self.interval_min <= self.interval_max:
            raise ValueError('随机请求间隔必须满足 0 ≤ 最短间隔 ≤ 最长间隔')

    def wait_interval(self):
        seconds = random.uniform(self.interval_min, self.interval_max)
        if seconds > 0:
            self.log.emit(f'随机等待 {seconds:.1f} 秒后继续…')
        self.delay(seconds)

    def run(self):
        session = None
        success = failed = skipped = done = 0
        total = len(self.papers)
        try:
            auth, session = self.login(download=self.operation == 'download')
            downloader = PDFDownloader(session, self.output_dir, auth=auth) if self.operation == 'download' else None
            cache = {}
            for index, paper in enumerate(self.papers):
                self.checkpoint()
                self.log.emit(f'[{index + 1}/{total}] {paper.title}')
                try:
                    if self.operation == 'detail':
                        if not needs_detail(paper):
                            skipped += 1
                            self.log.emit('摘要以 <正> 开头、详情和作者编码已完整，或没有详情链接，跳过')
                        else:
                            fetch_detail(session, paper)
                            success += 1
                    elif self.operation == 'author':
                        if paper.authors and all(a.au_code for a in paper.authors):
                            skipped += 1
                        elif not paper.authors:
                            raise ValueError('没有作者信息，请先补全详情')
                        elif fetch_codes(session, paper, cache, self.log.emit, self.checkpoint):
                            failed += 1
                        else:
                            success += 1
                    else:
                        if paper.local_pdf_path and Path(paper.local_pdf_path).is_file():
                            paper.download_status = 'completed'
                            skipped += 1
                        elif paper.db_type == '视频':
                            skipped += 1
                        else:
                            for attempt in range(self.retries + 1):
                                self.checkpoint()
                                try:
                                    with redirect_stdout(StringIO()):
                                        path = downloader.download(paper)
                                except Exception as exc:
                                    path = None
                                    self.log.emit(f'下载请求失败：{exc}')
                                if path:
                                    break
                                if attempt < self.retries:
                                    self.log.emit(f'下载失败，准备第 {attempt + 1} 次重试')
                                    self.wait_interval()
                            if not path:
                                raise RuntimeError('下载失败，详情链接可能已过期或需要安全验证')
                            paper.local_pdf_path = str(path)
                            paper.download_status = 'completed'
                            success += 1
                except TaskStopped:
                    self.paper_updated.emit(index, deepcopy(paper))
                    raise
                except Exception as exc:
                    failed += 1
                    if self.operation == 'download':
                        paper.download_status = 'failed'
                    self.log.emit(f'处理失败：{exc}')
                self.paper_updated.emit(index, deepcopy(paper))
                done += 1
                self.progress.emit(done, total, success, failed, skipped)
                if index + 1 < total:
                    self.wait_interval()
            self.completed.emit(f'任务完成：成功 {success}，失败 {failed}，跳过 {skipped}')
        except TaskStopped:
            self.completed.emit(f'任务已停止，已处理 {done}/{total} 篇，进度已保留')
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if session is not None:
                session.close()
