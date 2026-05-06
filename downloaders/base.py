"""下载器基类（预留）"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

from ..models import Paper


class BaseDownloader(ABC):
    """下载器基类"""

    def __init__(self, output_dir: str = "output"):
        """
        初始化下载器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def download(self, paper: Paper, filename: Optional[str] = None) -> Optional[str]:
        """
        下载单个论文

        Args:
            paper: 论文对象
            filename: 自定义文件名

        Returns:
            Optional[str]: 下载后的文件路径，失败返回 None
        """
        pass

    @abstractmethod
    def download_batch(
        self,
        papers: List[Paper],
        max_workers: int = 3,
        skip_existing: bool = True
    ) -> dict:
        """
        批量下载论文

        Args:
            papers: 论文列表
            max_workers: 最大并发数
            skip_existing: 是否跳过已存在的文件

        Returns:
            dict: 下载结果统计
        """
        pass
