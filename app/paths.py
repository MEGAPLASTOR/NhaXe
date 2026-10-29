"""Đường dẫn dùng chung của chương trình."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # thư mục gốc NhaXe
CONFIG_FILE = BASE_DIR / "config.ini"
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_FILE = ASSETS_DIR / "logo.png"
LOGO_MARK_FILE = ASSETS_DIR / "logo_mark.png"
ICON_FILE = ASSETS_DIR / "app.ico"
