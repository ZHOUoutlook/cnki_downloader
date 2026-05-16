"""GUI 后台任务。"""

from PyQt6.QtCore import QObject, pyqtSignal

from ..core.auth import CNKIAuth


class AuthCheckWorker(QObject):
    """在后台线程检测 CNKI IP 登录状态。"""

    succeeded = pyqtSignal(object, object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def run(self):
        """执行认证检测。"""
        try:
            auth = CNKIAuth()
            session = auth.ip_login()
            if session is None:
                self.failed.emit("未获取到可用会话，请连接校园网")
                return
            self.succeeded.emit(auth, session)
        except Exception as exc:
            self.failed.emit(str(exc) or "认证检测失败，请连接校园网")
        finally:
            self.finished.emit()
