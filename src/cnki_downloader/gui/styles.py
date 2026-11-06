"""工作台统一视觉：中性色、靛蓝强调、轻量边界。"""


def get_stylesheet():
    return '''
    QWidget { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 10pt; color: #30364A; }
    QMainWindow, QWidget#appRoot, QWidget#workspace { background: #F5F6FA; }
    QFrame#appHeader { background: white; border-bottom: 1px solid #E9EBF2; }
    QFrame#sidebar { background: #FFFFFF; border-right: 1px solid #E9EBF2; }
    QLabel { background: transparent; }
    QLabel#brandTitle { color: #242A3B; font-size: 14pt; font-weight: 700; }
    QLabel#headerCaption { color: #6E788C; font-size: 9pt; }
    QLabel#pageTitle { color: #242A3B; font-size: 20pt; font-weight: 700; }
    QLabel#panelTitle { color: #30364A; font-size: 12pt; font-weight: 600; }
    QLabel#sectionTitle { color: #30364A; font-size: 10pt; font-weight: 600; }
    QLabel#eyebrow { color: #667085; font-size: 8pt; font-weight: 600; }
    QLabel#mutedLabel, QLabel#fieldLabel { color: #667085; font-size: 9pt; }
    QLabel#countBadge { color: #656B80; background: #ECEEF5; border-radius: 10px; padding: 2px 9px; font-size: 9pt; }
    QLabel#fileBreadcrumb { color: #667085; font-size: 9pt; }
    QFrame#contentPanel { background: white; border: 1px solid #E8EAF2; border-radius: 12px; }
    QFrame#taskPanel { background: white; border: 1px solid #E8EAF2; border-radius: 10px; }
    QWidget#flowPanel, QStackedWidget { background: transparent; }
    QFrame#separator { background: #ECEEF4; border: none; max-height: 1px; }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background: #FAFBFE; color: #41485D; border: 1px solid #E3E6EF;
        border-radius: 7px; min-height: 26px; padding: 5px 10px;
        selection-background-color: #E4E6FF; selection-color: #343C8F;
    }
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #C8CDD9; }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #767AF2; background: white; }
    QLineEdit#libraryFilter { background: #F6F7FB; border: none; min-height: 28px; padding-left: 10px; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView { background: white; border: 1px solid #E3E6EF; selection-background-color: #EEEFFF; color: #30364A; outline: none; padding: 5px; }
    QSpinBox::up-button, QDoubleSpinBox::up-button { border: none; width: 18px; }
    QSpinBox::down-button, QDoubleSpinBox::down-button { border: none; width: 18px; }
    QPushButton {
        background: white; color: #626B80; border: 1px solid #E3E6EF; border-radius: 7px;
        min-height: 26px; padding: 5px 12px;
    }
    QPushButton:hover { background: #F5F6FC; border-color: #CCD0DF; color: #363F5A; }
    QPushButton:pressed { background: #EAECF7; }
    QPushButton:focus { border-color: #767AF2; }
    QPushButton:disabled { color: #B4BAC9; background: #FAFBFD; border-color: #EFF0F5; }
    QPushButton#primaryButton { background: #5B5FEF; border-color: #5B5FEF; color: white; font-weight: 600; min-height: 30px; }
    QPushButton#primaryButton:hover { background: #4D51DD; border-color: #4D51DD; }
    QPushButton#primaryButton:pressed { background: #4246CE; }
    QPushButton#primaryButton:disabled { color: #B7B9D7; background: #EEEFFA; border-color: #EEEFFA; }
    QPushButton#ghostButton { background: transparent; border: 1px solid transparent; padding: 5px 8px; }
    QPushButton#ghostButton:hover { background: #F0F2F8; }
    QPushButton#navButton { text-align: left; border: none; border-radius: 7px; padding: 6px 14px; color: #7A8295; min-height: 24px; }
    QPushButton#navButton:hover { color: #545BC9; background: #F6F6FD; }
    QPushButton#navButton:checked { color: #5358DC; background: #EFF0FF; font-weight: 600; }
    QPushButton#viewTab { border: none; border-radius: 0; border-bottom: 2px solid transparent; color: #667085; padding: 10px 4px; }
    QPushButton#viewTab:checked { color: #5358DC; border-bottom-color: #6266ED; font-weight: 600; }
    QPushButton#viewTab:hover { background: #FAFAFF; color: #5358DC; }
    QPushButton#dangerButton { color: #C4606B; background: transparent; border-color: #EFDDE1; }
    QPushButton#dangerButton:hover { background: #FFF1F3; }
    QPushButton#dangerButton:disabled { color: #C5C9D3; border-color: #ECEEF4; }
    QTableView { background: white; alternate-background-color: #FFFFFF; border: none; gridline-color: transparent;
        selection-background-color: #EEF0FF; selection-color: #30364A; outline: none; }
    QTableView::item { border: none; border-bottom: 1px solid #F0F1F6; padding: 6px 12px; }
    QTableView::item:hover { background: #FAFAFE; }
    QTableView::item:selected { background: #EEF0FF; }
    QHeaderView { background: #F8F9FC; }
    QHeaderView::section { background: #F8F9FC; color: #667085; font-size: 9pt; font-weight: 400;
        border: none; border-bottom: 1px solid #ECEEF4; min-height: 30px; padding: 5px 12px; text-align: left; }
    QScrollBar:vertical { width: 8px; background: transparent; margin: 3px 0; }
    QScrollBar::handle:vertical { background: #DCE0E9; border-radius: 4px; min-height: 32px; }
    QScrollBar::handle:vertical:hover { background: #B9BFCD; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar:horizontal { height: 8px; background: transparent; }
    QScrollBar::handle:horizontal { background: #DCE0E9; border-radius: 4px; min-width: 32px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
    QProgressBar { min-height: 4px; max-height: 4px; background: #ECEEF8; border: none; border-radius: 2px; color: transparent; }
    QProgressBar::chunk { background: #7377EF; border-radius: 2px; }
    QPlainTextEdit { background: #F8F9FD; color: #70798E; border: none; border-radius: 7px; padding: 10px;
        font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI"; font-size: 9pt; }
    QTextBrowser { background: white; color: #41485D; border: none; padding: 12px; }
    QDialog, QMessageBox { background: white; }
    QGroupBox { border: none; background: transparent; margin-top: 16px; padding-top: 14px; font-weight: 600; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; color: #41485D; }
    QMenuBar { background: white; color: #7B8496; border: none; font-size: 9pt; }
    QMenuBar::item { padding: 4px 10px; }
    QMenuBar::item:selected { background: #F1F2FC; color: #5358DC; }
    QMenu { background: white; border: 1px solid #E3E6EF; padding: 6px; }
    QMenu::item { padding: 7px 20px; border-radius: 4px; }
    QMenu::item:selected { background: #EFF0FF; color: #5358DC; }
    QStatusBar { background: #F5F6FA; color: #9CA3B3; border: none; font-size: 8pt; }
    QStatusBar::item { border: none; }
    QToolTip { background: #30364A; color: white; border: none; padding: 6px 10px; }
    '''
