"""结果表格模型与稳定的字段排序规则。"""
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QColor

STATUS = {'pending': '待下载', 'downloading': '下载中', 'completed': '已下载', 'failed': '失败'}


class PaperTableModel(QAbstractTableModel):
    COLUMN_MAP = [('seq', '序号'), ('title', '标题'), ('authors', '作者'), ('source', '来源'),
                  ('publish_date', '发表时间'), ('citation_count', '被引'), ('download_count', '下载'),
                  ('au_code', '作者编码'), ('download_status', '文件状态')]

    def __init__(self, parent=None, columns=None):
        super().__init__(parent)
        self._papers = []

    def set_papers(self, papers):
        self.beginResetModel()
        self._papers = list(papers)
        self.endResetModel()

    def clear(self):
        self.set_papers([])

    def paper_at(self, row):
        return self._papers[row] if 0 <= row < len(self._papers) else None

    def paper_count(self):
        return len(self._papers)

    def rowCount(self, parent=None):
        return 0 if parent and parent.isValid() else len(self._papers)

    def columnCount(self, parent=None):
        return len(self.COLUMN_MAP)

    @staticmethod
    def sort_key(paper, column):
        name = PaperTableModel.COLUMN_MAP[column][0]
        if name == 'authors':
            return ' '.join(a.name for a in paper.authors).casefold()
        if name == 'au_code':
            return sum(bool(a.au_code) for a in paper.authors)
        value = getattr(paper, name, '')
        if name in ('seq', 'citation_count', 'download_count'):
            return int(value or 0)
        return str(value or '').casefold()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._papers):
            return None
        paper = self._papers[index.row()]
        name = self.COLUMN_MAP[index.column()][0]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            if name == 'authors':
                return '、'.join(a.name for a in paper.authors) or '待补全'
            if name == 'au_code':
                return f'{sum(bool(a.au_code) for a in paper.authors)}/{len(paper.authors)}' if paper.authors else '待补全'
            if name == 'download_status':
                return STATUS.get(paper.download_status, paper.download_status)
            return str(getattr(paper, name, '') or '')
        if role == Qt.ItemDataRole.ForegroundRole and name == 'download_status':
            return QColor({'completed': '#067647', 'failed': '#b42318'}.get(paper.download_status, '#667085'))
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMN_MAP[section][1]

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        self.set_papers(sorted(self._papers, key=lambda p: self.sort_key(p, column),
                               reverse=order == Qt.SortOrder.DescendingOrder))
