"""CNKI 论文数据模型"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Author:
    """作者信息"""
    name: str
    profile_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Paper:
    """论文信息模型"""
    seq: int  # 序号
    title: str  # 标题
    detail_url: str  # 详情链接
    authors: List[Author] = field(default_factory=list)  # 作者列表
    source: str = ""  # 来源期刊
    publish_date: str = ""  # 发表时间
    db_type: str = ""  # 数据库类型
    citation_count: int = 0  # 被引次数
    download_count: int = 0  # 下载次数
    download_url: str = ""  # PDF下载链接
    html_url: str = ""  # HTML阅读链接
    ai_read_url: str = ""  # AI阅读链接

    # PDF 下载相关字段
    local_pdf_path: Optional[str] = None  # 本地 PDF 路径
    download_status: str = "pending"  # pending, downloading, completed, failed
    _original_detail_url: Optional[str] = field(default=None, repr=False)  # 原始详情链接，用于判断是否被刷新

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {
            '序号': self.seq,
            '标题': self.title,
            '详情链接': self.detail_url,
            '作者': [author.to_dict() for author in self.authors],
            '来源': self.source,
            '发表时间': self.publish_date,
            '数据库类型': self.db_type,
            '被引': self.citation_count,
            '下载': self.download_count,
            '下载链接': self.download_url,
            'HTML阅读链接': self.html_url,
            'CNKI AI阅读链接': self.ai_read_url,
            '下载状态': self.download_status,
        }
        if self.local_pdf_path:
            result['本地PDF路径'] = self.local_pdf_path
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'Paper':
        """从字典创建 Paper 对象"""
        authors = []
        if '作者' in data:
            authors = [
                Author(name=a.get('作者名', ''), profile_url=a.get('作者主页链接', ''))
                for a in data['作者']
            ]

        detail_url = data.get('详情链接', '')
        return cls(
            seq=data.get('序号', 0),
            title=data.get('标题', ''),
            detail_url=detail_url,
            authors=authors,
            source=data.get('来源', ''),
            publish_date=data.get('发表时间', ''),
            db_type=data.get('数据库类型', ''),
            citation_count=int(data.get('被引', 0) or 0),
            download_count=int(data.get('下载', 0) or 0),
            download_url=data.get('下载链接', ''),
            html_url=data.get('HTML阅读链接', ''),
            ai_read_url=data.get('CNKI AI阅读链接', ''),
            local_pdf_path=data.get('本地PDF路径'),
            download_status=data.get('下载状态', 'pending'),
            _original_detail_url=detail_url,  # 保存原始链接
        )

    def __str__(self) -> str:
        author_names = ' | '.join([a.name for a in self.authors])
        return f"【{self.seq}】{self.title}\n   作者: {author_names}\n   来源: {self.source} | 时间: {self.publish_date}\n   被引: {self.citation_count} | 下载: {self.download_count}"
