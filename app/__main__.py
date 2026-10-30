"""Chạy chương trình: python -m app (run.bat, shortcut Desktop và bản .exe đều gọi vào đây)."""

import sys
from tkinter import messagebox

from .core.errors import LOG_FILE, log_error


def run():
    try:
        from .ui.main_window import main

        main()
    except Exception:
        log_error(*sys.exc_info())
        messagebox.showerror("Quản lý nhà xe",
                             f"Chương trình gặp lỗi khi khởi động.\nChi tiết lỗi lưu tại:\n{LOG_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    run()
