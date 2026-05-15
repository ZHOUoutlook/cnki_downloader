"""论文结果表格模型"""

from typing import List

from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QColor

from ..models import Paper


class PaperTableModel(QAbstractTableModel):
    """论文表格模型，支持 QTableView 展示"""

    # 列映射：索引 -> Paper 字段
    COLUMN_MAP = [
        ("seq", "序号"),
        ("title", "标题"),
        ("authors", "作者"),
        ("source", "来源"),
        ("publish_date", "时间"),
        ("citation_count", "被引"),
        ("download_count", "下载"),
    ]

    def __init__(self, parent=None, columns=None):
        super().__init__(parent)
        self._papers: List[Paper] = []
        self._columns = columns or [col for _, col in self.COLUMN_MAP]

    def paper_count(self) -> int:
        return len(self._papers)

    def set_papers(self, papers: List[Paper]):
        """替换所有论文数据"""
        self.beginResetModel()
        self._papers = papers
        self.endResetModel()

    def append_papers(self, papers: List[Paper]):
        """追加论文数据"""
        if not papers:
            return
        begin = len(self._papers)
        self._papers.extend(papers)
        end = begin + len(papers) - 1
        self.beginInsertRows(self.index(0, 0), begin, end)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._papers.clear()
        self.endResetModel()

    # ── QAbstractTableModel 接口 ──────────────────────────────

    def rowCount(self, parent=None):
        return len(self._papers)

    def columnCount(self, parent=None):
        return len(self._columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        paper = self._papers[index.row()]
        col_name = self.COLUMN_MAP[index.column()][0]
        value = getattr(paper, col_name, "")

        if role == Qt.ItemDataRole.DisplayRole:
            if col_name == "authors":
                return " | ".join(a.name for a in value)
            if col_name == "seq":
                return str(value)
            return str(value) if value is not None else ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            # 序号、被引、下载列右对齐
            if col_name in ("seq", "citation_count", "download_count"):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ForegroundRole and col_name == "citation_count":
            # 被引数为 0 时用灰色
            if value == 0 or value == "0":
                return QColor("#999")

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._columns):
                return self._columns[section]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)
        return None

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        """支持按列排序"""
        col_name = self.COLUMN_MAP[column][0]
        reverse = (order == Qt.SortOrder.DescendingOrder)

        def sort_key(paper):
            val = getattr(paper, col_name, "")
            if val is None or val == "":
                return -1 if not reverse else float('inf')
            if isinstance(val, (int, float)):
                return val
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0

        self.layoutAboutToBeChanged.emit()
        self._papers.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()
