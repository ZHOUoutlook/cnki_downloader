"""具有键盘操作和详情入口的结果表。"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTableView, QAbstractItemView, QHeaderView, QMenu, QApplication

from .detail_dialog import open_web_url
from .delegates import PaperTitleDelegate, StatusDelegate


class ResultTable(QTableView):
    details_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setMouseTracking(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(64)
        self.setItemDelegateForColumn(1, PaperTitleDelegate(self))
        self.setItemDelegateForColumn(7, StatusDelegate(self, kind='code'))
        self.setItemDelegateForColumn(8, StatusDelegate(self, kind='file'))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.doubleClicked.connect(lambda index: self.details_requested.emit(self.model().paper_at(index.row())))

    def configure_columns(self):
        header = self.horizontalHeader()
        header.setMinimumSectionSize(44)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for index, width in enumerate([48, 380, 140, 110, 100, 64, 54, 125, 104]):
            self.setColumnWidth(index, width)
        for column in (0, 4, 5, 6):
            self.setColumnHidden(column, True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.model() and self.model().columnCount() == 9:
            remaining = self.viewport().width() - sum(self.columnWidth(i) for i in range(9) if i != 1 and not self.isColumnHidden(i))
            self.setColumnWidth(1, max(280, remaining))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.currentIndex().isValid():
            self.details_requested.emit(self.model().paper_at(self.currentIndex().row()))
        elif event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            QApplication.clipboard().setText('\n'.join(self.model().paper_at(i.row()).title
                                                      for i in self.selectionModel().selectedRows()))
        else:
            super().keyPressEvent(event)

    def _menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return
        paper = self.model().paper_at(index.row())
        menu = QMenu(self)
        menu.addAction('查看详情', lambda: self.details_requested.emit(paper))
        menu.addAction('复制标题', lambda: QApplication.clipboard().setText(paper.title))
        if paper.detail_url:
            menu.addAction('打开知网页面', lambda: open_web_url(paper.detail_url))
        menu.exec(self.viewport().mapToGlobal(position))
