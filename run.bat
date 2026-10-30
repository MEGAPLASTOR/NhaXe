@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VIDATEX - Quan ly nha xe

set "PYVER=3.12.10"

rem ---- Tim Python ----
call :find_python
if not defined PY goto :no_python

:run
rem ---- Kiem tra moi truong ao (.venv chep tu may khac se khong chay duoc) ----
if not exist ".venv\Scripts\python.exe" goto :make_venv
".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
if not errorlevel 1 goto :check_libs
echo Thu muc .venv duoc chep tu may khac, dang tao lai cho may nay...
rmdir /s /q ".venv" >nul 2>nul
if exist ".venv\Scripts\python.exe" (
    rem Windows con giu file vai giay sau khi tien trinh vua thoat - doi roi xoa lai
    ping -n 4 127.0.0.1 >nul 2>nul
    rmdir /s /q ".venv" >nul 2>nul
)
if exist ".venv\Scripts\python.exe" goto :venv_locked

:make_venv
echo Dang tao moi truong Python lan dau, doi mot chut...
%PY% -m venv .venv
if errorlevel 1 goto :fail

:check_libs
rem ---- Cai thu vien neu chua co ----
".venv\Scripts\python.exe" -c "import cv2, PIL, customtkinter, edge_tts" >nul 2>nul
if errorlevel 1 (
    echo Dang cai thu vien opencv-python, pillow, customtkinter, edge-tts - chi can lam 1 lan...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto :fail
)

rem ---- Chay chuong trinh ----
".venv\Scripts\python.exe" -m app
if errorlevel 1 goto :fail
exit /b 0


rem ================= Cai Python =================
:no_python
echo.
echo Chua cai Python tren may nay.
echo Chuong trinh can Python de chay. Se tai khoang 25 MB tu python.org.
choice /c YN /m "Tai va cai Python %PYVER% tu dong"
if errorlevel 2 goto :manual

rem ---- Cach 1: winget (neu may co san) ----
where winget >nul 2>nul
if not errorlevel 1 (
    echo.
    echo Dang cai Python bang winget...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    call :find_python
    if defined PY goto :installed
    echo winget khong cai duoc. Thu cach tai truc tiep...
)

rem ---- Cach 2: tai thang tu python.org ----
set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-arm64.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%.exe"
set "PYEXE=%TEMP%\cai-python-%PYVER%.exe"

echo.
echo Dang tai Python %PYVER% ...
if exist "%PYEXE%" del "%PYEXE%" >nul 2>nul
curl -L --fail -o "%PYEXE%" "%PYURL%" 2>nul
if not exist "%PYEXE%" (
    echo Thu tai lai bang PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=3072; (New-Object Net.WebClient).DownloadFile('%PYURL%','%PYEXE%')"
)
if not exist "%PYEXE%" goto :manual

echo Dang cai Python, vui long doi vai phut va dung tat cua so nay...
"%PYEXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
del "%PYEXE%" >nul 2>nul
call :find_python
if not defined PY goto :manual

:installed
echo.
echo Da cai xong Python. Dang khoi dong chuong trinh...
echo.
goto :run

:manual
echo.
echo Khong cai tu dong duoc. Hay cai tay:
echo   1. Vao https://www.python.org/downloads/
echo   2. Tai Python 3.12 va cai, nho TICK o "Add python.exe to PATH"
echo   3. Chay lai run.bat
echo.
choice /c YN /m "Mo trang tai Python bang trinh duyet"
if not errorlevel 2 start "" "https://www.python.org/downloads/"
pause
exit /b 1

:venv_locked
echo.
echo Khong xoa duoc thu muc .venv (co the dang bi chuong trinh khac mo).
echo Hay dong het cac cua so lien quan, xoa tay thu muc .venv roi chay lai run.bat.
pause
exit /b 1

:fail
echo.
echo Co loi xay ra. Xem thong bao phia tren.
pause
exit /b 1


rem ---- Tim Python o PATH hoac o thu muc cai mac dinh ----
:find_python
set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%~fD\python.exe" set PY="%%~fD\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%~fD\python.exe" set PY="%%~fD\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles(x86)%\Python3*") do if exist "%%~fD\python.exe" set PY="%%~fD\python.exe"
goto :eof
