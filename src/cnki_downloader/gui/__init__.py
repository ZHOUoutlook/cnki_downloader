"""桌面界面；按需导入 Qt，文件服务也可在无 GUI 依赖时使用。"""
from importlib import import_module

_EXPORTS = {
    'MainWindow': 'main_window', 'DetailDialog': 'detail_dialog',
    'DownloadPanel': 'download_panel', 'PaperTableModel': 'result_model',
    'ResultTable': 'result_table', 'SearchPanel': 'search_panel',
    'SettingsDialog': 'settings_dialog', 'get_stylesheet': 'styles',
    'AuthCheckWorker': 'workers',
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    value = getattr(import_module('.' + _EXPORTS[name], __name__), name)
    globals()[name] = value
    return value
