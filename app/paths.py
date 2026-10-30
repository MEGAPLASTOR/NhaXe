"""
Đường dẫn dùng chung của chương trình.

Chạy bằng mã nguồn  : mọi thứ nằm trong thư mục NhaXe.
Chạy bằng file .exe : cài đặt và dữ liệu nằm cạnh file exe (để chép đi đâu cũng mang theo được),
                      còn logo và biểu tượng nằm sẵn bên trong gói exe.
"""

import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)   # True khi đang chạy bản đóng gói bằng PyInstaller

if FROZEN:
    BASE_DIR = Path(sys.executable).resolve().parent
    ASSETS_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR)) / "assets"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    ASSETS_DIR = BASE_DIR / "assets"

CONFIG_FILE = BASE_DIR / "config.ini"
DATA_DIR = BASE_DIR / "data"
LOGO_FILE = ASSETS_DIR / "logo.png"
LOGO_MARK_FILE = ASSETS_DIR / "logo_mark.png"
ICON_FILE = ASSETS_DIR / "app.ico"
VOICE_DIR = BASE_DIR / "giong_doc"          # chương trình đọc Piper + giọng Tiếng Việt (nằm cạnh file exe)
SOUND_CACHE_DIR = DATA_DIR / "am_thanh"     # câu đọc đã tạo sẵn
