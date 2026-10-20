"""GUI 样式表"""


def get_stylesheet() -> str:
    """返回应用程序样式表。"""
    return """
    QWidget {
        font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        font-size: 10pt;
        color: #1f2937;
    }

    QWidget#appRoot {
        background-color: #eef2f6;
    }

    QScrollArea#sideScroll {
        background-color: transparent;
        border: none;
    }

    QScrollArea#sideScroll > QWidget > QWidget {
        background-color: transparent;
    }

    QFrame#topBar,
    QWidget#contentPanel,
    QWidget#sidePanel,
    QFrame#bottomPanel {
        background-color: #ffffff;
        border: 1px solid #d7dde6;
        border-radius: 8px;
    }

    QLabel#appTitle {
        font-size: 18pt;
        font-weight: 700;
        color: #123047;
    }

    QLabel#appSubtitle,
    QLabel#mutedLabel {
        color: #667085;
    }

    QLabel#sectionTitle {
        font-size: 12pt;
        font-weight: 700;
        color: #123047;
    }

    QLabel#networkStatusLabel {
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 4px 10px;
        font-weight: 600;
    }

    QLabel#networkStatusLabel[status="checking"] {
        background-color: #fff7ed;
        border-color: #fed7aa;
        color: #9a3412;
    }

    QLabel#networkStatusLabel[status="connected"] {
        background-color: #ecfdf3;
        border-color: #abefc6;
        color: #067647;
    }

    QLabel#networkStatusLabel[status="disconnected"] {
        background-color: #fff1f3;
        border-color: #fecdd3;
        color: #be123c;
    }

    QGroupBox {
        background-color: #ffffff;
        border: 1px solid #d7dde6;
        border-radius: 8px;
        margin-top: 18px;
        padding: 12px;
        font-weight: 700;
        color: #123047;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        top: 4px;
        padding: 0 8px;
        background-color: #ffffff;
    }

    QFrame#resultToolbar {
        background-color: #f8fafc;
        border: none;
        border-bottom: 1px solid #d7dde6;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }

    QFrame#panelSwitcher {
        background-color: #eef2f6;
        border: 1px solid #d7dde6;
        border-radius: 8px;
    }

    QLineEdit,
    QComboBox,
    QSpinBox {
        min-height: 30px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 4px 9px;
        background-color: #ffffff;
        selection-background-color: #1f6feb;
        selection-color: #ffffff;
    }

    QLineEdit:focus,
    QComboBox:focus,
    QSpinBox:focus {
        border: 1px solid #1f6feb;
    }

    QPushButton {
        min-height: 30px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 4px 14px;
        background-color: #ffffff;
        color: #1f2937;
    }

    QPushButton:hover {
        background-color: #f1f5f9;
        border-color: #94a3b8;
    }

    QPushButton:pressed {
        background-color: #e2e8f0;
    }

    QPushButton:disabled {
        background-color: #f1f5f9;
        color: #9aa4b2;
        border-color: #d7dde6;
    }

    QPushButton#primaryButton {
        background-color: #1f6feb;
        border-color: #1f6feb;
        color: #ffffff;
        font-weight: 600;
    }

    QPushButton#primaryButton:hover {
        background-color: #155ac7;
        border-color: #155ac7;
    }

    QPushButton#secondaryButton,
    QPushButton#ghostButton {
        background-color: #f8fafc;
        color: #27415c;
    }

    QPushButton#switchButton {
        background-color: transparent;
        border: none;
        color: #475467;
        font-weight: 600;
    }

    QPushButton#switchButton:hover {
        background-color: #f8fafc;
    }

    QPushButton#switchButton:checked {
        background-color: #ffffff;
        color: #123047;
        border: 1px solid #d7dde6;
    }

    QPushButton#dangerButton {
        background-color: #fff5f5;
        border-color: #f1b9b9;
        color: #b42318;
    }

    QPushButton#dangerButton:hover {
        background-color: #fee4e2;
    }

    QTableView {
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #e5e7eb;
        selection-background-color: #dbeafe;
        selection-color: #123047;
    }

    QTableView::item {
        padding: 6px 8px;
        border-bottom: 1px solid #edf2f7;
    }

    QTableView::item:hover {
        background-color: #eff6ff;
    }

    QHeaderView::section {
        min-height: 34px;
        background-color: #f1f5f9;
        border: none;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #d7dde6;
        padding: 5px 8px;
        font-weight: 700;
        color: #334155;
    }

    QProgressBar {
        min-height: 18px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background-color: #f1f5f9;
        text-align: center;
        color: #334155;
    }

    QProgressBar::chunk {
        border-radius: 5px;
        background-color: #2da44e;
    }

    QTextEdit {
        border: 1px solid #d7dde6;
        border-radius: 6px;
        background-color: #0f172a;
        color: #dbeafe;
        padding: 8px;
        font-family: "Cascadia Mono", "Consolas", monospace;
        font-size: 9pt;
    }

    QStatusBar {
        background-color: #ffffff;
        border-top: 1px solid #d7dde6;
        color: #667085;
    }

    QStatusBar::item {
        border: none;
    }

    QSplitter::handle {
        background-color: transparent;
    }

    QRadioButton {
        spacing: 6px;
    }

    QComboBox::drop-down,
    QSpinBox::up-button,
    QSpinBox::down-button {
        border: none;
        width: 18px;
    }
    """
