# Windows 安装包

安装包适用于 Windows 10 / 11 64 位，包含 Python、Qt 和运行依赖。
默认安装到当前用户目录，可在安装界面编辑路径或点击“Browse...”选择其他磁盘和文件夹。默认目录不需要管理员权限；自定义目录需要当前用户有写入权限。支持开始菜单、可选桌面快捷方式和卸载。
默认数据目录为“文档/CNKI论文助手/output”，卸载程序不会删除此目录。

## 重新构建

使用 Python 3.12，在 Windows 上执行（默认 MSI 构建使用该版本自带的 msilib）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build-windows.ps1
```

默认生成 `.msi`，使用 Windows Installer 完成安装和卸载。安装界面为英文，应用界面为中文。
也可安装 [Inno Setup](https://jrsoftware.org/isdl.php)，通过 `-ISCC` 参数指定 `ISCC.exe` 路径生成 `.exe` 安装包。

产物：`dist/CNKI-Paper-Assistant-<版本>-Setup-x64.msi`。
`dist/CNKI-Paper-Assistant/` 为独立运行目录，整个目录一起复制即可运行。

## 启动验证

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$check = Start-Process -FilePath '.\dist\CNKI-Paper-Assistant\CNKI-Paper-Assistant.exe' -ArgumentList '--smoke-test' -WindowStyle Hidden -Wait -PassThru
$check.ExitCode
Remove-Item Env:QT_QPA_PLATFORM
```

退出码为 0 表示打包后的 Qt 界面、文献显示及筛选功能通过启动检查。此检查不访问网络。
当前安装包没有数字签名。
