"""检索条件面板。"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton, QSizePolicy


def field(title, widget):
    box = QWidget()
    box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    label = QLabel(title)
    label.setObjectName('fieldLabel')
    label.setBuddy(widget)
    layout.addWidget(label)
    layout.addWidget(widget)
    return box


class SearchPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('flowPanel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel('检索条件')
        title.setObjectName('panelTitle')
        layout.addWidget(title)
        hint = QLabel('找到需要的文献，结果自动保存。')
        hint.setObjectName('mutedLabel')
        layout.addWidget(hint)
        self.mode = QComboBox()
        self.mode.addItem('按期刊检索', 'journal')
        self.mode.addItem('按论文标题检索', 'title')
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText('输入期刊名称，如 金融研究')
        self.keyword.setClearButtonEnabled(True)
        self.keyword.setAccessibleName('检索关键词')
        layout.addWidget(field('检索方式', self.mode))
        layout.addWidget(field('关键词', self.keyword))
        pages = QHBoxLayout()
        pages.setSpacing(12)
        self.start_page = QSpinBox()
        self.start_page.setRange(1, 9999)
        self.page_count = QSpinBox()
        self.page_count.setRange(1, 9999)
        pages.addWidget(field('起始页', self.start_page))
        pages.addWidget(field('获取页数', self.page_count))
        layout.addLayout(pages)
        self.page_size = QComboBox()
        self.page_size.addItems(['20', '50', '100'])
        layout.addWidget(field('每页条数', self.page_size))
        layout.addStretch()
        self.search_btn = QPushButton('开始检索')
        self.search_btn.setObjectName('primaryButton')
        layout.addWidget(self.search_btn)
        self.mode.currentIndexChanged.connect(self._mode_changed)

    def _mode_changed(self):
        self.keyword.setPlaceholderText('输入期刊名称，如 金融研究' if self.mode.currentData() == 'journal' else '输入论文标题或关键词')
