"""GUI 样式表"""

def get_stylesheet() -> str:
    """返回应用程序样式表"""
    return """
    /* 全局样式 */
    QMainWindow, QWidget {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 9pt;
        background-color: #f5f5f5;
    }

    /* 标题栏样式 */
    QLabel#titleLabel {
        font-size: 18pt;
        font-weight: bold;
        color: #1a73e8;
        padding: 10px;
    }

    /* 面板样式 */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #ddd;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
        background-color: white;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #333;
    }

    /* 输入框样式 */
    QLineEdit {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 6px 10px;
        background-color: white;
        selection-background-color: #1a73e8;
        selection-color: white;
    }

    QLineEdit:focus {
        border: 1px solid #1a73e8;
    }

    QLineEdit[placeholder="true"] {
        color: #999;
    }

    /* 按钮样式 */
    QPushButton {
        background-color: #1a73e8;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: normal;
    }

    QPushButton:hover {
        background-color: #1557b0;
    }

    QPushButton:pressed {
        background-color: #0d47a1;
    }

    QPushButton:disabled {
        background-color: #ccc;
        color: #999;
    }

    QPushButton#secondaryBtn {
        background-color: #6c757d;
    }

    QPushButton#secondaryBtn:hover {
        background-color: #5a6268;
    }

    QPushButton#dangerBtn {
        background-color: #dc3545;
    }

    QPushButton#dangerBtn:hover {
        background-color: #c82333;
    }

    /* 表格样式 */
    QTableView {
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: white;
        selection-background-color: #e8f0fe;
        selection-color: #333;
        gridline-color: #eee;
    }

    QTableView::item {
        padding: 6px;
    }

    QTableView::item:selected {
        background-color: #e8f0fe;
        color: #333;
    }

    QTableView::item:hover {
        background-color: #f8f9fa;
    }

    QHeaderView::section {
        background-color: #f8f9fa;
        padding: 8px;
        border: none;
        border-bottom: 1px solid #ddd;
        border-right: 1px solid #ddd;
        font-weight: bold;
        color: #333;
    }

    QHeaderView::section:first {
        border-top-left-radius: 4px;
    }

    QHeaderView::section:last {
        border-top-right-radius: 4px;
        border-right: none;
    }

    /* 滚动条样式 */
    QScrollBar:vertical {
        border: none;
        background-color: #f5f5f5;
        width: 12px;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #ccc;
        border-radius: 6px;
        min-height: 30px;
        margin: 2px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #999;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    QScrollBar:horizontal {
        border: none;
        background-color: #f5f5f5;
        height: 12px;
        margin: 0;
    }

    QScrollBar::handle:horizontal {
        background-color: #ccc;
        border-radius: 6px;
        min-width: 30px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #999;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }

    /* 下拉框样式 */
    QComboBox {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 6px 10px;
        background-color: white;
    }

    QComboBox:focus {
        border: 1px solid #1a73e8;
    }

    QComboBox::drop-down {
        border: none;
        width: 20px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid #666;
        border-right: 4px solid transparent;
        border-top: 4px solid transparent;
        border-bottom: 4px solid transparent;
        margin-right: 10px;
    }

    QComboBox QAbstractItemView {
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: white;
        selection-background-color: #1a73e8;
        selection-color: white;
        padding: 4px;
    }

    /* 标签页样式 */
    QTabWidget::pane {
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: white;
    }

    QTabBar::tab {
        background-color: #f8f9fa;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }

    QTabBar::tab:selected {
        background-color: white;
        font-weight: bold;
    }

    QTabBar::tab:hover {
        background-color: #e9ecef;
    }

    /* 对话框样式 */
    QDialog {
        background-color: white;
    }

    QDialogButtonBox QPushButton {
        min-width: 80px;
    }

    /* 进度条样式 */
    QProgressBar {
        border: 1px solid #ddd;
        border-radius: 4px;
        text-align: center;
        background-color: #f5f5f5;
        height: 20px;
    }

    QProgressBar::chunk {
        background-color: #1a73e8;
        border-radius: 3px;
    }

    /* 状态栏样式 */
    QStatusBar {
        background-color: #f8f9fa;
        border-top: 1px solid #ddd;
    }

    QStatusBar::item {
        border: none;
    }

    /* 工具栏样式 */
    QToolBar {
        background-color: white;
        border: none;
        border-bottom: 1px solid #ddd;
        padding: 4px;
        spacing: 4px;
    }

    QToolBar QToolButton {
        background-color: transparent;
        border: none;
        padding: 6px 10px;
        border-radius: 4px;
    }

    QToolBar QToolButton:hover {
        background-color: #e9ecef;
    }

    /* 复选框和单选框 */
    QCheckBox, QRadioButton {
        spacing: 6px;
    }

    QCheckBox::indicator, QRadioButton::indicator {
        width: 16px;
        height: 16px;
    }

    /* 标签样式 */
    QLabel {
        background-color: transparent;
    }

    QLabel#statusLabel {
        color: #666;
    }

    QLabel#successLabel {
        color: #28a745;
    }

    QLabel#errorLabel {
        color: #dc3545;
    }

    QLabel#warningLabel {
        color: #ffc107;
    }

    /* 分割线 */
    QFrame#hLine {
        background-color: #ddd;
        border: none;
    }

    QFrame#hLine[horizontal="true"] {
        max-height: 1px;
        margin: 10px 0;
    }

    QFrame#hLine[horizontal="false"] {
        max-width: 1px;
        margin: 0 10px;
    }
    """
