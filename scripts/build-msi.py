"""Build a per-user x64 MSI using the Python 3.12 Windows Installer library."""
import sys
import tomllib
import uuid
from pathlib import Path
import msilib
from msilib import schema, sequence

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
SOURCE = ROOT / 'dist' / 'CNKI-Paper-Assistant'
OUTPUT = ROOT / 'dist' / f'CNKI-Paper-Assistant-{VERSION}-Setup-x64.msi'
NAMESPACE = uuid.UUID('e4cc962d-5f7d-45ef-a95b-41cddbb5cdb0')


def guid(name):
    return '{' + str(uuid.uuid5(NAMESPACE, name)).upper() + '}'


def build():
    assert sys.platform == 'win32' and sys.maxsize > 2**32
    assert (SOURCE / 'CNKI-Paper-Assistant.exe').is_file()
    db = msilib.init_database(str(OUTPUT), schema, 'CNKI Paper Assistant',
                             guid('product-' + VERSION), VERSION, 'ZHOUoutlook')
    msilib.add_tables(db, sequence)
    add = lambda table, rows: msilib.add_data(db, table, rows)
    add('Property', [
        ('UpgradeCode', '{' + str(NAMESPACE).upper() + '}'),
        ('INSTALLLEVEL', '1'), ('ARPNOMODIFY', '1'), ('ARPNOREPAIR', '1'),
        ('ARPPRODUCTICON', 'AppIcon'),
        ('ARPURLINFOABOUT', 'https://github.com/ZHOUoutlook/cnki_downloader'),
        ('SecureCustomProperties', 'OLDPRODUCTS;NEWERPRODUCTS;INSTALLDIR'),
        ('DefaultUIFont', 'DlgFont8'),
    ])
    add('Upgrade', [
        ('{' + str(NAMESPACE).upper() + '}', None, VERSION, None, 1, None, 'OLDPRODUCTS'),
        ('{' + str(NAMESPACE).upper() + '}', VERSION, None, None, 258, None, 'NEWERPRODUCTS'),
    ])
    for table in ('InstallUISequence', 'InstallExecuteSequence'):
        db.OpenView(f"UPDATE `{table}` SET `Sequence`=300 WHERE `Action`='LaunchConditions'").Execute(None)
    add('LaunchCondition', [
        ('VersionNT64', 'Windows 10 or later (64-bit) is required.'),
        ('NOT NEWERPRODUCTS OR Installed', 'A newer version is already installed.'),
    ])
    cab = msilib.CAB('application.cab')
    feature = msilib.Feature(db, 'Main', 'CNKI Paper Assistant', 'Desktop application', 1)
    desktop_feature = msilib.Feature(db, 'DesktopShortcut', 'Desktop shortcut',
                                      'Optional desktop shortcut', 2, level=2, parent=feature)
    add('Condition', [('DesktopShortcut', 1, 'CREATE_DESKTOP_SHORTCUT=1')])
    feature.set_current()
    target = msilib.Directory(db, cab, None, str(SOURCE), 'TARGETDIR', 'SourceDir')
    local = msilib.Directory(db, cab, target, '.', 'LocalAppDataFolder', '.')
    programs = msilib.Directory(db, cab, local, '.', 'ProgramsDir', 'Programs')
    appdir = msilib.Directory(db, cab, programs, '.', 'INSTALLDIR', 'CNKIPaperAssistant')
    directories = {Path('.'): appdir}
    executable = None
    for index, path in enumerate(sorted(SOURCE.rglob('*'))):
        relative = path.relative_to(SOURCE)
        if path.is_dir():
            parent = directories[relative.parent]
            directories[relative] = msilib.Directory(db, cab, parent, path.name,
                                                    f'Dir{index}', path.name)
        elif path.is_file():
            directory = directories[relative.parent]
            directory.start_component(f'FileComponent{index}', feature, 0,
                                      keyfile=path.name, uuid=guid(relative.as_posix()))
            file_id = directory.add_file(path.name)
            if path.name == 'CNKI-Paper-Assistant.exe':
                executable = file_id
    # Each shortcut has a per-user registry key path for reliable uninstall.
    start = msilib.Directory(db, cab, target, '.', 'ProgramMenuFolder', '.')
    menu = msilib.Directory(db, cab, start, '.', 'AppMenu', 'CNKI Paper Assistant')
    desktop = msilib.Directory(db, cab, target, '.', 'DesktopFolder', '.')
    for name, directory, condition in [
        ('StartMenu', menu, None),
        ('Desktop', desktop, None),
    ]:
        component, key = name + 'ShortcutComponent', name + 'ShortcutKey'
        add('Component', [(component, guid(component), directory.logical, 260, condition, key)])
        shortcut_feature = 'DesktopShortcut' if name == 'Desktop' else 'Main'
        add('FeatureComponents', [(shortcut_feature, component)])
        add('Registry', [(key, 1, r'Software\ZHOUoutlook\CNKIPaperAssistant', name, VERSION, component)])
        add('Shortcut', [(name + 'Shortcut', directory.logical,
                          'CNKI Paper Assistant', component, f'[#%s]' % executable,
                          None, 'CNKI Paper Assistant', None, 'AppIcon', 0, 1, 'INSTALLDIR')])
        if name == 'StartMenu':
            add('RemoveFile', [('RemoveAppMenu', component, None, directory.logical, 2)])
    add('Icon', [('AppIcon', msilib.Binary(str(ROOT / 'packaging/windows/app.ico')))])
    add('TextStyle', [('DlgFont8', 'Segoe UI', 9, None, 0)])
    add('CheckBox', [('CREATE_DESKTOP_SHORTCUT', '1')])
    welcome = msilib.Dialog(db, 'WelcomeDlg', 50, 50, 370, 210, 3,
                           'CNKI Paper Assistant Setup', 'LocationPath', 'Install', 'Cancel')
    welcome.text('Heading', 20, 20, 330, 25, 3, 'Install CNKI Paper Assistant ' + VERSION)
    welcome.text('Info', 20, 52, 330, 32, 3, 'Python is included. No administrator permission is required.')
    welcome.text('Location', 20, 88, 330, 14, 3, 'Install folder:')
    welcome.control('LocationPath', 'PathEdit', 20, 105, 255, 20, 3,
                    'INSTALLDIR', None, 'Browse', 'Choose the installation folder|')
    welcome.pushbutton('Browse', 285, 105, 60, 20, 3, 'Browse...', 'Desktop').event('SpawnDialog', 'BrowseDlg')
    welcome.checkbox('Desktop', 20, 135, 300, 18, 3, 'CREATE_DESKTOP_SHORTCUT',
                     'Create a desktop shortcut', 'Install')
    install = welcome.pushbutton('Install', 205, 175, 65, 20, 3, 'Install', 'Cancel')
    install.event('SetTargetPath', 'INSTALLDIR', ordering=1)
    install.event('AddLocal', 'DesktopShortcut', 'CREATE_DESKTOP_SHORTCUT=1', 2)
    install.event('Remove', 'DesktopShortcut', 'NOT CREATE_DESKTOP_SHORTCUT', 3)
    install.event('EndDialog', 'Return', ordering=4)
    welcome.pushbutton('Cancel', 280, 175, 65, 20, 3, 'Cancel', 'LocationPath').event('EndDialog', 'Exit')
    browse = msilib.Dialog(db, 'BrowseDlg', 50, 50, 370, 290, 3,
                          'Choose installation folder', 'Folders', 'OK', 'Cancel')
    browse.text('Label', 20, 12, 330, 14, 3, 'Select a folder or enter a complete path:')
    browse.control('Drives', 'DirectoryCombo', 20, 30, 265, 60,
                   3 | 0x00010000 | 0x00020000 | 0x00040000,
                   'INSTALLDIR', None, 'Up', None)
    folders = browse.control('Folders', 'DirectoryList', 20, 60, 325, 145, 3,
                             'INSTALLDIR', None, 'Path', None)
    folders.mapping('DirectoryListUp', 'Up')
    browse.pushbutton('Up', 295, 30, 50, 18, 3, 'Up', 'Folders').event('DirectoryListUp', '0')
    browse.control('Path', 'PathEdit', 20, 218, 325, 20, 3,
                   'INSTALLDIR', None, 'OK', 'Installation folder|')
    okay = browse.pushbutton('OK', 205, 255, 65, 20, 3, 'OK', 'Cancel')
    okay.event('SetTargetPath', 'INSTALLDIR', ordering=1)
    okay.event('EndDialog', 'Return', ordering=2)
    cancel = browse.pushbutton('Cancel', 280, 255, 65, 20, 3, 'Cancel', 'Drives')
    cancel.event('Reset', '0', ordering=1)
    cancel.event('EndDialog', 'Return', ordering=2)
    add('InstallUISequence', [('WelcomeDlg', 'NOT Installed', 1230)])
    for name, text in [('ExitDialog', 'Setup completed.'), ('FatalError', 'Setup failed. Please retry or check the installer log.'),
                       ('UserExit', 'Setup was cancelled.')]:
        dialog = msilib.Dialog(db, name, 50, 50, 370, 160, 3,
                              'CNKI Paper Assistant Setup', 'Close', 'Close', 'Close')
        dialog.text('Message', 20, 25, 330, 60, 3, text)
        dialog.pushbutton('Close', 280, 120, 65, 20, 3, 'Close', None).event('EndDialog', 'Return')
    cab.commit(db)
    db.Commit()
    print(OUTPUT)


if __name__ == '__main__':
    build()
