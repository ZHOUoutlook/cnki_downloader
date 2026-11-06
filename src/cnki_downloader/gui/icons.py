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
    elif name == 'github':
        from PyQt6.QtSvg import QSvgRenderer
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
        <path fill="{color}" d="M12 .297C5.37.297 0 5.67 0 12.297c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577
        0-.285-.01-1.04-.015-2.04-3.338.724-4.043-1.61-4.043-1.61-.546-1.387-1.333-1.756-1.333-1.756
        -1.09-.745.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998
        .108-.776.418-1.305.762-1.605-2.665-.305-5.467-1.334-5.467-5.93 0-1.31.469-2.381 1.236-3.221
        -.124-.303-.536-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.52 11.52 0 0 1 12 6.098
        c1.02.005 2.045.138 3.003.404 2.291-1.552 3.297-1.23 3.297-1.23.655 1.652.243 2.873.12 3.176
        .77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.622-5.479 5.921.43.372.823 1.102.823 2.222
        0 1.606-.015 2.898-.015 3.293 0 .322.216.694.825.576C20.565 22.092 24 17.595 24 12.297
        c0-6.627-5.373-12-12-12"/></svg>'''
        QSvgRenderer(svg.encode('utf-8')).render(painter, QRectF(0, 0, 24, 24))
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
