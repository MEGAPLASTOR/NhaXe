"""Ghi lỗi ra file data/loi.log (cần thiết khi chạy bằng shortcut không có cửa sổ đen)."""

import traceback
from datetime import datetime

from ..paths import DATA_DIR

LOG_FILE = DATA_DIR / "loi.log"


def log_error(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}")
    except OSError:
        pass
    print(text)
