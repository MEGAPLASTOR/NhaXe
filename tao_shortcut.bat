@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Tao shortcut "Quan ly nha xe" ngoai Desktop, co logo VIDATEX, mo khong hien cua so den.
if not exist ".venv\Scripts\pythonw.exe" (
    echo Hay chay run.bat it nhat 1 lan truoc de cai dat chuong trinh.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Quan ly nha xe.lnk'); $s.TargetPath = '%~dp0.venv\Scripts\pythonw.exe'; $s.Arguments = '-m app'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = '%~dp0assets\app.ico'; $s.Description = 'Quan ly nha xe - VIDATEX JSC'; $s.Save()"
if errorlevel 1 (
    echo Khong tao duoc shortcut.
) else (
    echo Da tao shortcut "Quan ly nha xe" ngoai Desktop.
)
pause