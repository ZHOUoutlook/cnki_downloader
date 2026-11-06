"""桌面工作文件：验证导入、保留附加字段、原子写入。"""
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path

from ..models import Paper


def _normalize_record(row, position):
    """在交给模型和视图之前验证已知字段，附加字段保持原样。"""
    label = f'第 {position} 条文献'
    if not isinstance(row, dict):
        raise ValueError(f'{label}必须是一个对象')
    row = deepcopy(row)
    text_fields = (
        '标题', '详情链接', '来源', '发表时间', '数据库类型', '下载链接',
        'HTML阅读链接', 'CNKI AI阅读链接', 'DOI', '摘要', 'ISSN', 'CN',
        '页数', '卷号', '期号', '页码范围', '基金', '专辑', '专题', '分类号', '下载状态',
    )
    for key in text_fields:
        if key not in row:
            continue
        if row[key] is None:
            row[key] = 'pending' if key == '下载状态' else ''
        elif not isinstance(row[key], str):
            raise ValueError(f'{label}的“{key}”必须是文本')
    for key in ('序号', '被引', '下载'):
        if key not in row:
            continue
        value = row[key]
        if value is None or value == '':
            row[key] = 0
        elif isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError(f'{label}的“{key}”必须是整数')
        else:
            try:
                row[key] = int(value)
            except ValueError as exc:
                raise ValueError(f'{label}的“{key}”必须是整数') from exc
    if '本地PDF路径' in row and row['本地PDF路径'] is not None and not isinstance(row['本地PDF路径'], str):
        raise ValueError(f'{label}的“本地PDF路径”必须是文本或 null')
    if '关键词' in row:
        if row['关键词'] is None:
            row['关键词'] = []
        if not isinstance(row['关键词'], list) or any(not isinstance(k, str) for k in row['关键词']):
            raise ValueError(f'{label}的“关键词”必须是文本列表')
    if '作者单位' in row:
        value = row['作者单位']
        if value is None:
            row['作者单位'] = ''
        elif not isinstance(value, str) and not (
            isinstance(value, list) and all(isinstance(org, str) for org in value)
        ):
            raise ValueError(f'{label}的“作者单位”必须是文本或文本列表')
    authors = row.get('作者', [])
    if not isinstance(authors, list) or any(not isinstance(a, dict) for a in authors):
        raise ValueError(f'{label}的“作者”必须是包含 name、profile_url 等字段的对象列表')
    for author in authors:
        for key in ('name', '作者名', 'profile_url', '作者主页链接', 'affiliation_indices', 'au_code', 'au-code'):
            if key not in author:
                continue
            if author[key] is None:
                author[key] = ''
            elif not isinstance(author[key], str):
                raise ValueError(f'{label}的作者字段“{key}”必须是文本')
    return row


class Workspace:
    def __init__(self, papers=None, path=None, raw=None):
        self.papers = list(papers or [])
        self.path = Path(path).resolve() if path else None
        self.raw = deepcopy(raw) if raw is not None else [{} for _ in self.papers]

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if not isinstance(data, list):
            raise ValueError('JSON 顶层必须是文献列表')
        records = [_normalize_record(row, position) for position, row in enumerate(data, 1)]
        return cls([Paper.from_dict(row) for row in records], path, records)

    def save(self, path=None):
        target = Path(path).resolve() if path else self.path
        if target is None:
            raise ValueError('请先选择保存文件')
        rows = []
        for paper, raw in zip(self.papers, self.raw):
            row = deepcopy(raw)
            row.update(paper.to_dict())
            # 仅对名字唯一的作者复用附加字段，避免同名作者串数据。
            old_authors = raw.get('作者', [])
            for author in row['作者']:
                old = [a for a in old_authors if a.get('name', a.get('作者名')) == author['name']]
                if len(old) == 1 and sum(a['name'] == author['name'] for a in row['作者']) == 1:
                    extra = deepcopy(old[0])
                    extra.update(author)
                    author.update(extra)
            rows.append(row)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                             prefix=target.name + '.', suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                json.dump(rows, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and Path(temporary).exists():
                Path(temporary).unlink()
        self.path = target
        self.raw = rows
        return target

    def merge(self, papers):
        """按标题与发表时间增量合并，保留详情、作者编码及下载状态。"""
        index = {(p.title, p.publish_date): i for i, p in enumerate(self.papers)}
        added = 0
        for paper in papers:
            key = (paper.title, paper.publish_date)
            if key in index:
                existing = self.papers[index[key]]
                for name in ('detail_url', 'source', 'db_type', 'citation_count', 'download_count',
                             'download_url', 'html_url', 'ai_read_url'):
                    value = getattr(paper, name)
                    if value or isinstance(value, int):
                        setattr(existing, name, value)
            else:
                index[key] = len(self.papers)
                self.papers.append(paper)
                self.raw.append({})
                added += 1
        return added
