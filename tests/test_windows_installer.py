"""Verify the authored MSI UI using a small isolated application payload."""
import importlib.util
import sys
from pathlib import Path

import pytest

if sys.platform != 'win32':
    pytest.skip('Windows Installer is Windows-only', allow_module_level=True)
msilib = pytest.importorskip('msilib')


@pytest.fixture(scope='module')
def installer(tmp_path_factory):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('build_msi', root / 'scripts/build-msi.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    temporary = tmp_path_factory.mktemp('installer')
    module.SOURCE = temporary / 'application'
    module.SOURCE.mkdir()
    (module.SOURCE / 'CNKI-Paper-Assistant.exe').write_bytes(b'installer test payload')
    module.OUTPUT = temporary / 'test.msi'
    module.build()
    return msilib.OpenDatabase(str(module.OUTPUT), msilib.MSIDBOPEN_READONLY)


def rows(database, query):
    view = database.OpenView(query)
    view.Execute(None)
    results = []
    while record := view.Fetch():
        results.append(tuple(record.GetString(i) for i in range(1, record.GetFieldCount() + 1)))
    view.Close()
    return results


def test_destination_can_be_edited_and_browsed(installer):
    controls = rows(installer, "SELECT `Type`, `Property` FROM `Control` WHERE `Dialog_`='WelcomeDlg'")
    assert ('PathEdit', 'INSTALLDIR') in controls
    assert rows(installer, "SELECT `Argument` FROM `ControlEvent` WHERE `Dialog_`='WelcomeDlg' AND `Event`='SpawnDialog'") == [('BrowseDlg',)]
    browser = rows(installer, "SELECT `Type`, `Property` FROM `Control` WHERE `Dialog_`='BrowseDlg'")
    for control_type in ('PathEdit', 'DirectoryCombo', 'DirectoryList'):
        assert (control_type, 'INSTALLDIR') in browser


def test_chosen_path_is_applied_before_installation(installer):
    events = rows(installer, "SELECT `Event`, `Argument` FROM `ControlEvent` WHERE `Dialog_`='WelcomeDlg' AND `Control_`='Install' ORDER BY `Ordering`")
    assert events[0] == ('SetTargetPath', 'INSTALLDIR')
    assert events[-1] == ('EndDialog', 'Return')
    browse_events = rows(installer, "SELECT `Event`, `Argument` FROM `ControlEvent` WHERE `Dialog_`='BrowseDlg' AND `Control_`='OK' ORDER BY `Ordering`")
    assert browse_events == [('SetTargetPath', 'INSTALLDIR'), ('EndDialog', 'Return')]
    cancel = rows(installer, "SELECT `Event` FROM `ControlEvent` WHERE `Dialog_`='BrowseDlg' AND `Control_`='Cancel' ORDER BY `Ordering`")
    assert cancel == [('Reset',), ('EndDialog',)]


def test_control_help_uses_windows_installer_format(installer):
    for (help_text,) in rows(installer, 'SELECT `Help` FROM `Control`'):
        assert not help_text or '|' in help_text
