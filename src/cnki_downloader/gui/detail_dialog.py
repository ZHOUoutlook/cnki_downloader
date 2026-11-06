"""展示文献信息、作者编码与文件入口。"""
from html import escape
from pathlib import Path
from urllib.parse import urljoin

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QPushButton


def open_web_url(url):
    address = QUrl(urljoin('https://kns.cnki.net/', url))
    if address.scheme() in ('http', 'https'):
        QDesktopServices.openUrl(address)


class DetailDialog(QDialog):
    def __init__(self, paper, parent=None):
        super().__init__(parent)
        self.setWindowTitle('文献详情')
        self.resize(760, 660)
        layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(lambda url: open_web_url(url.toString()))
        parts = [f'<h2>{escape(paper.title)}</h2>']
        for key, value in paper.to_dict().items():
            if key == '标题':
                continue
            if key == '作者':
                text = '<br>'.join(
                    f'{escape(a.name)} · au-code：{escape(a.au_code or "尚未获取")} '
                    + (f'<a href="{escape(a.profile_url, quote=True)}">作者主页</a>' if a.profile_url else '')
                    for a in paper.authors) or '尚未获取'
            elif isinstance(value, list):
                text = escape('；'.join(str(v) for v in value))
            elif '链接' in key and value:
                text = f'<a href="{escape(str(value), quote=True)}">{escape(str(value))}</a>'
            else:
                text = escape(str(value or '—')).replace('\n', '<br>')
            parts.append(f'<p><b>{escape(key)}</b><br>{text}</p>')
        self.browser.setHtml(''.join(parts))
        layout.addWidget(self.browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        copy = QPushButton('复制标题')
        copy.clicked.connect(lambda: self._copy_title(paper.title))
        buttons.addButton(copy, QDialogButtonBox.ButtonRole.ActionRole)
        local = QPushButton('打开本地文件')
        local.setEnabled(bool(paper.local_pdf_path and Path(paper.local_pdf_path).is_file()))
        local.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(paper.local_pdf_path).resolve()))))
        buttons.addButton(local, QDialogButtonBox.ButtonRole.ActionRole)
        layout.addWidget(buttons)

    def _copy_title(self, title):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(title)
