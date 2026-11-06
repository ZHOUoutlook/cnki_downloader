"""文献表格的双行标题和轻量状态徽标。"""
from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


def _background(painter, option):
    selected = bool(option.state & QStyle.StateFlag.State_Selected)
    if selected:
        color = QColor('#EEF0FF')
    elif option.state & QStyle.StateFlag.State_MouseOver:
        color = QColor('#F8F9FD')
    elif option.features & QStyleOptionViewItem.ViewItemFeature.Alternate:
        color = option.palette.alternateBase().color()
    else:
        color = option.palette.base().color()
    painter.fillRect(option.rect, color)
    return selected


class PaperTitleDelegate(QStyledItemDelegate):
    """标题和来源日期共享一个宽列，保留完整内容的模型提示。"""
    def paint(self, painter, option, index):
        paper = index.model().paper_at(index.row())
        if paper is None:
            return super().paint(painter, option, index)
        painter.save()
        selected = _background(painter, option)
        title_font = QFont(option.font)
        title_font.setWeight(QFont.Weight.Medium)
        subtitle_font = QFont(option.font)
        if subtitle_font.pointSizeF() > 0:
            subtitle_font.setPointSizeF(max(8, subtitle_font.pointSizeF() - 1))
        elif subtitle_font.pixelSize() > 0:
            subtitle_font.setPixelSize(max(10, subtitle_font.pixelSize() - 2))
        metrics = QFontMetrics(title_font)
        secondary_metrics = QFontMetrics(subtitle_font)
        content = option.rect.adjusted(14, 5, -14, -5)
        total_height = metrics.height() + secondary_metrics.height() + 3
        top = content.top() + max(0, (content.height() - total_height) // 2)
        title_rect = content.adjusted(0, top - content.top(), 0, 0)
        title_rect.setHeight(metrics.height())
        painter.setFont(title_font)
        painter.setPen(QColor('#4145B5' if selected else '#242A3B'))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         metrics.elidedText(str(paper.title), Qt.TextElideMode.ElideRight, content.width()))
        subtitle = '  ·  '.join(str(v) for v in (paper.source, paper.publish_date) if v)
        if not subtitle:
            subtitle = '文献信息待补全'
        subtitle_rect = content.adjusted(0, top + metrics.height() + 3 - content.top(), 0, 0)
        subtitle_rect.setHeight(secondary_metrics.height())
        painter.setFont(subtitle_font)
        painter.setPen(QColor('#7B80AA' if selected else '#667085'))
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         secondary_metrics.elidedText(subtitle, Qt.TextElideMode.ElideRight, content.width()))
        painter.restore()

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        metrics = QFontMetrics(option.font)
        return QSize(base.width(), max(58, metrics.height() * 2 + 15))


class StatusDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, kind='file'):
        super().__init__(parent)
        self.kind = kind

    def paint(self, painter, option, index):
        paper = index.model().paper_at(index.row())
        if paper is None:
            return super().paint(painter, option, index)
        if self.kind == 'code':
            total = len(paper.authors)
            complete = sum(bool(author.au_code) for author in paper.authors)
            text = f'{complete}/{total} 已补全' if complete else '待补全'
            foreground, background = ('#5B5FEF', '#F0EFFF') if total and complete == total else ('#667085', '#F0F2F6')
        else:
            text, foreground, background = {
                'completed': ('已下载', '#1F785D', '#EAF7F0'),
                'failed': ('下载失败', '#AD3E49', '#FCEEEF'),
                'downloading': ('下载中', '#5B5FEF', '#F0EFFF'),
            }.get(paper.download_status, ('待下载', '#667085', '#F0F2F6'))
        painter.save()
        _background(painter, option)
        font = QFont(option.font)
        if font.pointSizeF() > 0:
            font.setPointSizeF(max(8, font.pointSizeF() - 1))
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        available = max(0, option.rect.width() - 16)
        badge_width = min(available, metrics.horizontalAdvance(text) + 18)
        badge_height = min(option.rect.height() - 12, metrics.height() + 9)
        badge = QRectF(option.rect.x() + (option.rect.width() - badge_width) / 2,
                       option.rect.y() + (option.rect.height() - badge_height) / 2,
                       badge_width, badge_height)
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(badge, 5, 5)
        painter.setPen(QColor(foreground))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter,
                         metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(0, int(badge_width - 12))))
        painter.restore()
