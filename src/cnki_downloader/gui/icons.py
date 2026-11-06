"""以统一的 24 单位网格绘制桌面工作台线条图标。"""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def icon(name, color='#667085', size=20):
    """返回支持高 DPI 的圆头线条图标，无外部图片依赖。"""
    size = max(1, int(size))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 24, size / 24)
    painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    def line(x1, y1, x2, y2):
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def path(points, close=False):
        result = QPainterPath(QPointF(*points[0]))
        for point in points[1:]:
            result.lineTo(QPointF(*point))
        if close:
            result.closeSubpath()
        painter.drawPath(result)

    if name == 'book':
        painter.drawRoundedRect(QRectF(5, 3, 14, 18), 2, 2)
        line(8, 3, 8, 21)
        line(11, 8, 16, 8)
        line(11, 12, 15, 12)
    elif name == 'search':
        painter.drawEllipse(QRectF(3.5, 3.5, 12.5, 12.5))
        line(14.5, 14.5, 20.5, 20.5)
    elif name == 'layers':
        path([(3, 8), (12, 3), (21, 8), (12, 13)], True)
        path([(3, 12), (12, 17), (21, 12)])
        path([(3, 16), (12, 21), (21, 16)])
    elif name == 'download':
        line(12, 3, 12, 15)
        path([(7.5, 11), (12, 15.5), (16.5, 11)])
        path([(4, 15), (4, 20), (20, 20), (20, 15)])
    elif name == 'folder':
        path([(3, 7), (3, 5), (9, 5), (11, 8), (21, 8), (21, 20), (3, 20)], True)
        line(3, 10, 21, 10)
    elif name == 'save':
        path([(4, 3), (17, 3), (21, 7), (21, 21), (3, 21), (3, 4)], True)
        path([(7, 3), (7, 9), (16, 9), (16, 3)])
        path([(7, 21), (7, 14), (17, 14), (17, 21)])
    elif name == 'settings':
        painter.drawEllipse(QRectF(8.5, 8.5, 7, 7))
        shape = QPainterPath()
        shape.moveTo(9.5, 3)
        for point in [(14.5, 3), (15, 6), (17, 7.2), (19.8, 6.3), (22, 10.5),
                      (19.5, 12), (19.5, 14), (21, 16), (18.5, 20), (15.7, 18.8),
                      (14.5, 19.5), (14, 22), (10, 22), (9.3, 19.2), (7.5, 18.3),
                      (5, 19), (2.8, 15), (5, 13.5), (5, 11), (3, 9.5),
                      (5.5, 5.5), (8, 6.5), (9.5, 5.5)]:
            shape.lineTo(*point)
        shape.closeSubpath()
        painter.drawPath(shape)
    elif name == 'wifi':
        for x, y, end_x, control_y in [(3, 8, 21, 1.8), (6.5, 11.5, 17.5, 7.6),
                                     (9.5, 15, 14.5, 13.1)]:
            curve = QPainterPath(QPointF(x, y))
            curve.quadTo(QPointF(12, control_y), QPointF(end_x, y))
            painter.drawPath(curve)
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(11.2, 18, 1.6, 1.6))
    elif name == 'chevron':
        path([(8, 5), (15, 12), (8, 19)])
    elif name == 'clock':
        painter.drawEllipse(QRectF(3, 3, 18, 18))
        path([(12, 7), (12, 12), (16, 14)])
    elif name == 'play':
        path([(8, 4), (20, 12), (8, 20)], True)
    elif name == 'pause':
        line(8, 5, 8, 19)
        line(16, 5, 16, 19)
    elif name == 'stop':
        painter.drawRoundedRect(QRectF(5.5, 5.5, 13, 13), 1.5, 1.5)
    elif name == 'plus':
        line(12, 5, 12, 19)
        line(5, 12, 19, 12)
    elif name == 'check':
        path([(5, 12), (10, 17), (20, 6)])
    else:  # file 与未知名称均提供可辨认的文献图标。
        path([(5, 3), (14, 3), (20, 9), (20, 21), (5, 21)], True)
        path([(14, 3), (14, 9), (20, 9)])
        line(9, 13, 16, 13)
        line(9, 17, 14, 17)
    painter.end()
    return QIcon(pixmap)
