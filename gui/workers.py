"""GUI 后台任务。"""

from PyQt6.QtCore import QObject, pyqtSignal

from ..core.auth import CNKIAuth
from ..core.search import CNKISearcher


GLOBAL_AUTH = None


def set_global_auth(auth):
    """保存全局认证对象。"""
    global GLOBAL_AUTH
    GLOBAL_AUTH = auth


def clear_global_auth():
    """清空全局认证对象。"""
    global GLOBAL_AUTH
    GLOBAL_AUTH = None


class AuthCheckWorker(QObject):
    """在后台线程检测 CNKI IP 登录状态。"""

    succeeded = pyqtSignal(object, object)
    anonymous_succeeded = pyqtSignal(object, object, str)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def run(self):
        """执行认证检测。"""
        try:
            auth = CNKIAuth()
            try:
                session = auth.ip_login()
            except Exception as ip_exc:
                session = auth.anonymous_login()
                if session is None:
                    clear_global_auth()
                    self.failed.emit("未获取到可用匿名会话")
                    return
                set_global_auth(auth)
                self.anonymous_succeeded.emit(auth, session, str(ip_exc))
                return

            if session is None:
                clear_global_auth()
                self.failed.emit("未获取到可用会话，请连接校园网")
                return
            set_global_auth(auth)
            self.succeeded.emit(auth, session)
        except Exception as exc:
            clear_global_auth()
            self.failed.emit(str(exc) or "认证检测失败，请连接校园网")
        finally:
            self.finished.emit()


class SearchWorker(QObject):
    """在后台线程执行论文搜索。"""

    page_loaded = pyqtSignal(int, int, int)
    succeeded = pyqtSignal(list)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, search_type: str, keyword: str, page_count: int, page_size: int):
        super().__init__()
        self.search_type = search_type
        self.keyword = keyword
        self.page_count = page_count
        self.page_size = page_size

    def run(self):
        """执行搜索任务。"""
        try:
            session = GLOBAL_AUTH.get_session() if GLOBAL_AUTH else None
            searcher = CNKISearcher(session)
            all_papers = []
            for page in range(1, self.page_count + 1):
                if self.search_type == "title":
                    papers = searcher.search_by_title(self.keyword, page=page, page_size=self.page_size)
                else:
                    papers = searcher.search_by_journal(self.keyword, page=page, page_size=self.page_size)

                if not papers:
                    self.page_loaded.emit(page, 0, len(all_papers))
                    break

                all_papers.extend(papers)
                self.page_loaded.emit(page, len(papers), len(all_papers))

            self.succeeded.emit(all_papers)
        except Exception as exc:
            self.failed.emit(str(exc) or "搜索失败")
        finally:
            self.finished.emit()
