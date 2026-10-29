"""Chạy chương trình: python -m app (run.bat và shortcut Desktop đã làm sẵn)."""

import sys
from tkinter import messagebox

from .core.errors import LOG_FILE, log_error

try:
    from .ui.main_window import main

    main()
except Exception:
    log_error(*sys.exc_info())
    messagebox.showerror("Quản lý nhà xe", f"Chương trình gặp lỗi khi khởi động.\nChi tiết lỗi lưu tại:\n{LOG_FILE}")
    sys.exit(1)
