# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('C:/Users/dinht/Documents/NhaXe/assets/app.ico', '.'), ('C:/Users/dinht/Documents/NhaXe/assets/logo_mark.png', '.')]
datas += collect_data_files('customtkinter')


a = Analysis(
    ['C:/Users/dinht/Documents/NhaXe/cong_cu/trinh_cai_dat.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['cv2', 'numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GoCaiDat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:/Users/dinht/Documents/NhaXe/cong_cu/thong_tin_bo_cai.txt',
    icon=['C:/Users/dinht/Documents/NhaXe/assets/app.ico'],
)
