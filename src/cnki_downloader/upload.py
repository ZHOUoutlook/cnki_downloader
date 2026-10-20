"""CNKI 文献上传模块（占位）

实际上传实现位于仓库根目录 `output/upload.py`，属于内部工具，
依赖本地 API 服务，不随 PyPI 包分发。

如需在库中使用上传功能，请自行将 `output/upload.py` 复制为
`cnki_downloader/upload.py` 并调整 API 地址与凭据。
"""

from typing import Any, Dict, List, Optional

import requests


class Uploader:
    """文献上传器（占位实现）。

    实际调用需要本地文献管理 API 服务（默认 http://localhost:8000）。
    当前占位实现不会发起网络请求，仅抛出明确异常提示用户配置。
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._access_token: Optional[str] = None
        self._session: Optional[requests.Session] = None

    def _ensure_configured(self) -> None:
        raise RuntimeError(
            "上传功能依赖内部 API 服务，未随包分发。"
            "请将 output/upload.py 复制为 cnki_downloader/upload.py 并配置 base_url 与凭据。"
        )

    def login(self) -> str:
        self._ensure_configured()
        raise RuntimeError("未实现")

    def check(self, dois: List[str], titles: List[str]) -> List[Any]:
        self._ensure_configured()
        raise RuntimeError("未实现")

    def upload(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        self._ensure_configured()
        raise RuntimeError("未实现")

    def upload_with_login(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        self._ensure_configured()
        raise RuntimeError("未实现")
