"""Windows 安装版入口；用户数据与安装目录分开保存。"""
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QSettings, QStandardPaths


def main():
    if '--smoke-test' in sys.argv:
        import tempfile
        from PyQt6.QtWidgets import QApplication
        from cnki_downloader.gui.main_window import MainWindow
        from cnki_downloader.models import Paper
        app = QApplication([])
        app.setStyle('Fusion')
        with tempfile.TemporaryDirectory(prefix='cnki-smoke-') as temporary:
            window = MainWindow(QSettings(str(Path(temporary) / 'settings.ini'), QSettings.Format.IniFormat))
            window.workspace.papers = [Paper(1, '安装包启动测试', '/test')]
            window.apply_result_filter()
            window.show()
            app.processEvents()
            assert window.table_model.rowCount() == 1
            assert window.network_btn.isEnabled()
            assert window.menuBar().isHidden()
            window.view_group.button(3).click()
            assert not window.filtered_papers
            window.close()
        return 0
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    data_dir = Path(documents or Path.home()) / 'CNKI论文助手'
    (data_dir / 'output').mkdir(parents=True, exist_ok=True)
    os.chdir(data_dir)
    from cnki_downloader.gui_app import main as gui_main
    return gui_main()


if __name__ == '__main__':
    sys.exit(main())
