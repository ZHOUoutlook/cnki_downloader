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
from ..core.access import AccessBlocked
from ..downloaders import PDFDownloader
from ..utils import sanitize_filename
from ..config import DOWNLOAD_RELOGIN_INTERVAL
from .workspace import Workspace, SearchTransaction


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
    checked = pyqtSignal(bool, bool, str)

    def run(self):
        results = []
        for download, label in [(False, '匿名访问'), (True, 'IP（校园网）')]:
            session = None
            try:
                self.checkpoint()
                self.log.emit(f'正在检查{label}…')
                _, session = self.login(download=download)
                available = True
                detail = '授权登录成功' if download else '匿名会话建立成功'
            except TaskStopped:
                self.completed.emit('连接检查已停止')
                return
            except Exception as exc:
                available = False
                detail = str(exc)
            finally:
                if session is not None:
                    session.close()
            self.checked.emit(download, available, detail)
            result = f'{label}：' + ('正常' if available else '不可用')
            results.append(result)
            self.log.emit(f'{result} · {detail}')
        self.completed.emit('连接检查完成 · ' + '；'.join(results))


class SearchWorker(TaskWorker):
    papers_loaded = pyqtSignal(list)
    workspace_ready = pyqtSignal(object, bool)

    def __init__(self, search_type, keyword, page_count, page_size, start_page=1, parent=None, workspace=None):
        super().__init__(parent)
        self.workspace = (Workspace(deepcopy(workspace.papers), workspace.path, workspace.raw)
                          if workspace is not None else None)
        self.search_type, self.keyword = search_type, keyword
        self.page_count, self.page_size, self.start_page = page_count, page_size, start_page

    def run(self):
        session = None
        count = 0
        transaction = None
        committed = False
        try:
            if self.workspace is not None:
                transaction = SearchTransaction(self.workspace)
                transaction.begin()
                self.log.emit(f'检索临时文件：{transaction.temporary}')
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
                self.checkpoint()
                if transaction is not None:
                    stats = transaction.merge(papers)
                    self.log.emit(f"本页新增 {stats['added']} 篇，清理历史重复 {stats['deduplicated']} 条")
                count += len(papers)
                self.papers_loaded.emit(papers)
                self.progress.emit(offset + 1, self.page_count, count, 0, 0)
            self.checkpoint()
            if transaction is not None:
                transaction.commit()
                committed = True
                self.log.emit(f'检索结束，已替换正式文件：{transaction.target}')
            self.completed.emit(f'搜索完成，获取 {count} 篇文献')
        except TaskStopped:
            self.completed.emit(f'搜索已停止，保留已获取的 {count} 篇文献')
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if transaction is not None:
                transaction.workspace.path = transaction.target
                if not committed and transaction.temporary is not None:
                    self.log.emit(f'正式文件未改动，恢复文件保留在：{transaction.temporary}')
                self.workspace_ready.emit(transaction.workspace, committed)
            if session is not None:
                session.close()


class PaperTaskWorker(TaskWorker):
    paper_updated = pyqtSignal(int, object)
    paper_saved = pyqtSignal()
    save_failed = pyqtSignal(str)

    def __init__(self, operation, papers, output_dir='', delay=10, retries=3, parent=None, delay_max=None,
                 workspace=None, indices=None, limit=0):
        super().__init__(parent)
        self.operation = operation
        # 构造函数在界面线程执行，只复制列表；深拷贝留到 run 中。
        # 任务期间界面禁止编辑/保存/切换工作文件，因此原始字段可安全延后复制。
        self.papers = list(papers)
        self.workspace = None
        self._workspace_source = ((list(workspace.papers), workspace.path, workspace.raw)
                                  if workspace is not None else None)
        self.indices = list(indices) if indices is not None else list(range(len(papers)))
        self.output_dir, self.retries = output_dir, retries
        self.limit = limit
        self.interval_min = float(delay)
        self.interval_max = float(delay if delay_max is None else delay_max)
        if not 0 <= self.interval_min <= self.interval_max:
            raise ValueError('随机请求间隔必须满足 0 ≤ 最短间隔 ≤ 最长间隔')

    def _persist_update(self, index, paper):
        self._persist_updates([(index, paper)])

    def _persist_updates(self, updates):
        if self.workspace is not None:
            for index, paper in updates:
                self.workspace.papers[self.indices[index]] = paper
            try:
                self.workspace.save()
            except Exception as exc:
                # 写入失败也回传内存结果，供用户另存；立即结束后续请求。
                for index, paper in updates:
                    self.paper_updated.emit(index, deepcopy(paper))
                self.save_failed.emit(str(exc))
                raise TaskStopped() from exc
        for index, paper in updates:
            self.paper_updated.emit(index, deepcopy(paper))
        if self.workspace is not None:
            self.paper_saved.emit()

    def wait_interval(self):
        seconds = random.uniform(self.interval_min, self.interval_max)
        self.delay(seconds)

    def _download_log(self, message):
        text = message.strip()
        if text.startswith('📥 ') or text in ('获取详情页...', '解析下载链接...', '下载文件...'):
            return
        self.log.emit(message)

    def _download_tasks(self):
        tasks = []
        status_updates = []
        for index, paper in enumerate(self.papers):
            self.checkpoint()
            date = paper.publish_date.replace('-', '') if paper.publish_date else ''
            name = sanitize_filename(f'{paper.title}_{date}')
            # 与命令行下载一致，重新核验当前输出目录，不依赖 JSON 的旧状态或旧路径。
            paths = [Path(self.output_dir) / f'{name}.pdf', Path(self.output_dir) / f'{name}.caj']
            existing = next((path for path in paths if path.is_file()), None)
            if existing is not None:
                if paper.local_pdf_path != str(existing) or paper.download_status != 'completed':
                    paper.local_pdf_path = str(existing)
                    paper.download_status = 'completed'
                    status_updates.append((index, paper))
            else:
                if paper.local_pdf_path or paper.download_status != 'pending':
                    paper.local_pdf_path = None
                    paper.download_status = 'pending'
                    status_updates.append((index, paper))
                if paper.detail_url and paper.db_type != '视频':
                    tasks.append((index, paper))
        if status_updates:
            self._persist_updates(status_updates)
        self.log.emit(f'📄 共 {len(self.papers)} 篇论文，{len(tasks)} 篇有详情链接且还没下载')
        if self.limit:
            tasks = tasks[:self.limit]
            self.log.emit(f'🔢 本次最多下载 {self.limit} 篇，实际待下载 {len(tasks)} 篇')
        random.shuffle(tasks)
        return tasks

    def _refresh_download_session(self, downloader, done):
        self.checkpoint()
        self.log.emit(f'🧹 已处理 {done} 篇，清理会话并重新登录…')
        downloader.session.cookies.clear()
        # 认证输出可能包含 cookies，仍只显示下载器的结构化日志。
        with redirect_stdout(StringIO()):
            renewed = downloader._relogin()
        if not renewed:
            raise ConnectionError('定期重新登录失败，下载已停止，已完成进度已保存')
        self.checkpoint()
        self.wait_interval()

    def run(self):
        session = None
        success = failed = skipped = done = 0
        downloader = None
        total = len(self.papers)
        try:
            self.checkpoint()
            self.papers = deepcopy(self.papers)
            if self._workspace_source is not None:
                self.workspace = Workspace(*self._workspace_source)
                self._workspace_source = None
            self.checkpoint()
            tasks = (self._download_tasks() if self.operation == 'download'
                     else list(enumerate(self.papers)))
            total = len(tasks)
            if not tasks and self.operation == 'download':
                self.progress.emit(0, 0, 0, 0, 0)
                self.completed.emit('没有需要下载的论文：已有文件，或缺少详情链接，或为视频')
                return
            auth, session = self.login(download=self.operation == 'download')
            downloader = (PDFDownloader(session, self.output_dir, auth=auth, log=self._download_log)
                          if self.operation == 'download' else None)
            cache = {}
            for position, (index, paper) in enumerate(tasks):
                before = deepcopy(paper)
                self.checkpoint()
                if self.operation == 'download':
                    self.log.emit(f'[{position + 1}/{total}] 📥 [{paper.seq}] {paper.title}')
                else:
                    self.log.emit(f'[{position + 1}/{total}] {paper.title}')
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
                except AccessBlocked:
                    # 保存当前论文已取得的编码及刷新后的 URL，然后停止整批请求。
                    if paper != before:
                        self._persist_update(index, paper)
                    raise
                except TaskStopped:
                    if paper != before:
                        self._persist_update(index, paper)
                    raise
                except Exception as exc:
                    failed += 1
                    if self.operation == 'download':
                        paper.download_status = 'failed'
                    self.log.emit(f'处理失败：{exc}')
                if paper != before:
                    self._persist_update(index, paper)
                done += 1
                self.progress.emit(done, total, success, failed, skipped)
                if position + 1 < total:
                    self.wait_interval()
                    if self.operation == 'download' and done % DOWNLOAD_RELOGIN_INTERVAL == 0:
                        self._refresh_download_session(downloader, done)
            self.completed.emit(f'任务完成：成功 {success}，失败 {failed}，跳过 {skipped}')
        except TaskStopped:
            self.completed.emit(f'任务已停止，已处理 {done}/{total} 篇，进度已保留')
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            active_session = getattr(downloader, 'session', session) if downloader is not None else session
            if active_session is not None:
                active_session.close()
