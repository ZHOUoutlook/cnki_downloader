"""下载参数面板。"""
from pathlib import Path
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton, QHBoxLayout, QFileDialog, QLabel, QMessageBox
from .search_panel import field
from .icons import icon


class DownloadPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('flowPanel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel('下载设置')
        title.setObjectName('panelTitle')
        layout.addWidget(title)
        hint = QLabel('下载 PDF / CAJ，需要知网授权 IP。')
        hint.setObjectName('mutedLabel')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.output_dir = QLineEdit(str(Path('output/pdfs').resolve()))
        self.output_dir.setAccessibleName('下载保存目录')
        self.browse_btn = QPushButton('…')
        self.browse_btn.setToolTip('选择保存目录')
        self.browse_btn.setAccessibleName('选择保存目录')
        self.browse_btn.setFixedWidth(38)
        directory = QWidget()
        row = QHBoxLayout(directory)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self.output_dir, 1)
        row.addWidget(self.browse_btn)
        layout.addWidget(field('保存位置', directory))
        self.delay_min_spin = QDoubleSpinBox()
        self.delay_max_spin = QDoubleSpinBox()
        for spin in (self.delay_min_spin, self.delay_max_spin):
            spin.setRange(0, 600)
            spin.setDecimals(1)
            spin.setSuffix(' 秒')
        self.delay_min_spin.setValue(9)
        self.delay_max_spin.setValue(11)
        self.delay_min_spin.setAccessibleName('最短随机请求间隔')
        self.delay_max_spin.setAccessibleName('最长随机请求间隔')
        self.delay_min_spin.valueChanged.connect(self.delay_max_spin.setMinimum)
        self.delay_max_spin.setMinimum(self.delay_min_spin.value())
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(field('最短间隔', self.delay_min_spin))
        row.addWidget(field('最长间隔', self.delay_max_spin))
        layout.addLayout(row)
        self.delay_min_spin.setToolTip('两篇文献之间及失败重试前，在最短和最长间隔之间重新随机等待')
        self.delay_max_spin.setToolTip('与最短间隔相等时，使用固定等待时间')
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        self.retries_spin.setValue(3)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 100000)
        self.limit_spin.setSpecialValueText('不限')
        row.addWidget(field('失败重试', self.retries_spin))
        row.addWidget(field('本次数量上限', self.limit_spin))
        layout.addLayout(row)
        footnote = QLabel('已有本地文件会自动跳过。\n处理范围在文献列表底部选择。')
        footnote.setObjectName('mutedLabel')
        footnote.setWordWrap(True)
        layout.addWidget(footnote)
        layout.addStretch()
        self.download_btn = QPushButton('开始下载')
        self.download_btn.setObjectName('primaryButton')
        layout.addWidget(self.download_btn)
        self.open_dir_btn = QPushButton('打开下载目录')
        self.open_dir_btn.setIcon(icon('folder', size=18))
        self.open_dir_btn.setToolTip('在文件管理器中查看下载的 PDF / CAJ')
        self.open_dir_btn.clicked.connect(self.open_output_directory)
        layout.addWidget(self.open_dir_btn)
        self.browse_btn.clicked.connect(self.browse)

    def browse(self):
        path = QFileDialog.getExistingDirectory(self, '选择下载目录', self.output_dir.text())
        if path:
            self.output_dir.setText(path)

    def open_output_directory(self):
        value = self.output_dir.text().strip()
        directory = Path(value).expanduser().resolve() if value else None
        if directory is None or not directory.is_dir():
            QMessageBox.information(self, '打开下载目录', '下载目录尚不存在，请先选择已有目录或完成一次下载。')
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            QMessageBox.warning(self, '打开失败', f'无法打开目录：{directory}')
