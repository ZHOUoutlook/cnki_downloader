"""应用偏好设置。"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox,
                            QComboBox, QSpinBox, QLabel)


class SettingsDialog(QDialog):
    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.setWindowTitle('设置')
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.page_size = QComboBox()
        self.page_size.addItems(['20', '50', '100', '200'])
        self.page_size.setCurrentText(str(values.get('result_page_size', 20)))
        self.font_size = QSpinBox()
        self.font_size.setRange(9, 16)
        self.font_size.setValue(int(values.get('font_size', 10)))
        form.addRow('结果每页条数', self.page_size)
        form.addRow('界面字号', self.font_size)
        layout.addLayout(form)
        hint = QLabel('下载目录、间隔、重试次数和搜索条件会自动记住。\n搜索、详情和作者编码使用匿名会话；下载需要授权 IP。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('保存')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {'result_page_size': int(self.page_size.currentText()), 'font_size': self.font_size.value()}
