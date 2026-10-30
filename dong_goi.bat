@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Dong goi QuanLyNhaXe - VIDATEX
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "RA=%ROOT%\ban_phat_hanh"
set "TAM=%ROOT%\cong_cu\build"

echo ===================================================
echo     DONG GOI PHAN MEM - VIDATEX
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Chua co moi truong Python. Hay chay run.bat mot lan truoc, roi chay lai file nay.
    pause
    exit /b 1
)
set "PY=.venv\Scripts\python.exe"

"%PY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo Dang cai PyInstaller - chi can lam 1 lan...
    "%PY%" -m pip install --disable-pip-version-check pyinstaller
    if errorlevel 1 goto :fail
)

echo.
echo [1/3] Dong goi chuong trinh chinh...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name QuanLyNhaXe ^
    --icon "%ROOT%\assets\app.ico" ^
    --add-data "%ROOT%\assets;assets" ^
    --collect-data customtkinter ^
    --hidden-import edge_tts ^
    --version-file "%ROOT%\cong_cu\thong_tin_phien_ban.txt" ^
    --distpath "%RA%" --workpath "%TAM%" --specpath "%ROOT%\cong_cu" ^
    "%ROOT%\QuanLyNhaXe.py" >"%TAM%_1.log" 2>&1
if errorlevel 1 goto :loi_log
rem giong doc Piper (~100 MB) de thanh thu muc rieng canh exe, khong nhet vao exe cho khoi mo cham
if exist "%ROOT%\giong_doc" xcopy /e /i /y /q "%ROOT%\giong_doc" "%RA%\giong_doc" >nul

echo [2/3] Dong goi trinh go cai dat...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name GoCaiDat ^
    --icon "%ROOT%\assets\app.ico" ^
    --add-data "%ROOT%\assets\app.ico;." ^
    --add-data "%ROOT%\assets\logo_mark.png;." ^
    --collect-data customtkinter ^
    --exclude-module cv2 --exclude-module numpy ^
    --version-file "%ROOT%\cong_cu\thong_tin_bo_cai.txt" ^
    --distpath "%TAM%\go" --workpath "%TAM%" --specpath "%ROOT%\cong_cu" ^
    "%ROOT%\cong_cu\trinh_cai_dat.py" >"%TAM%_2.log" 2>&1
if errorlevel 1 goto :loi_log

echo [3/3] Dong goi bo cai dat...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name CaiDat_QuanLyNhaXe ^
    --icon "%ROOT%\assets\app.ico" ^
    --add-data "%RA%\QuanLyNhaXe.exe;." ^
    --add-data "%ROOT%\giong_doc;giong_doc" ^
    --add-data "%TAM%\go\GoCaiDat.exe;." ^
    --add-data "%ROOT%\assets\app.ico;." ^
    --add-data "%ROOT%\assets\logo_mark.png;." ^
    --collect-data customtkinter ^
    --exclude-module cv2 --exclude-module numpy ^
    --version-file "%ROOT%\cong_cu\thong_tin_bo_cai.txt" ^
    --distpath "%RA%" --workpath "%TAM%" --specpath "%ROOT%\cong_cu" ^
    "%ROOT%\cong_cu\trinh_cai_dat.py" >"%TAM%_3.log" 2>&1
if errorlevel 1 goto :loi_log

echo.
echo ===================================================
echo  XONG! Hai file trong thu muc ban_phat_hanh:
echo.
echo   CaiDat_QuanLyNhaXe.exe   ^<- GUI CHO KHACH FILE NAY
echo        bo cai dat: chon thu muc, tao shortcut,
echo        go duoc trong Apps and features
echo.
echo   QuanLyNhaXe.exe          ^<- ban chay truc tiep, khong can cai
echo        (chep kem thu muc giong_doc de co giong doc khi mat mang)
echo ===================================================
echo.
choice /c YN /m "Mo thu muc ban_phat_hanh"
if not errorlevel 2 explorer "%RA%"
exit /b 0

:loi_log
echo.
echo Dong goi that bai. Chi tiet trong: %TAM%_*.log
pause
exit /b 1

:fail
echo.
echo Dong goi that bai. Xem thong bao phia tren.
pause
exit /b 1
