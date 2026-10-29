"""Khung chung cho hộp thoại bật lên: đứng yên giữa màn hình, chặn cửa sổ chính, tự đặt con trỏ vào ô nhập."""

import tkinter as tk

import customtkinter as ctk

from .theme import C, brand_icon, show_centered


class ModalDialog(ctk.CTkToplevel):
    def __init__(self, master, title):
        super().__init__(master, fg_color=C["surface"])
        self.withdraw()  # ẩn cho đến khi đặt đúng giữa màn hình, tránh cửa sổ hiện ra rồi bị nhảy chỗ
        self.title(title)
        brand_icon(self)
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())
        self.focus_target = None  # CTkEntry nhận con trỏ khi mở

    def present(self):
        """Gọi ở cuối __init__ của lớp con, sau khi dựng xong giao diện."""
        # Cửa sổ vừa được chọn thì đưa con trỏ vào ô nhập luôn
        self.bind("<FocusIn>", lambda e: self._focus_entry() if e.widget is self else None)
        show_centered(self)
        self.after(30, self._activate)
        # CustomTkinter có thể vẽ lại cửa sổ sau khi mở và làm mất con trỏ, nên thử đặt lại vài lần
        for delay in (150, 300, 600):
            self.after(delay, self._focus_entry)

    def _activate(self):
        try:
            self.lift()
            self.grab_set()
        except tk.TclError:
            pass
        self._focus_entry()

    def _focus_entry(self):
        if self.focus_target is None:
            return
        try:
            if not self.winfo_exists():
                return
            inner = self.focus_target._entry  # ô nhập tk thật bên trong CTkEntry
            if self.focus_get() is not inner:
                self.focus_force()
                inner.focus_force()
                inner.icursor("end")
        except (tk.TclError, KeyError, AttributeError):
            pass

    def close(self):
        master = self.master
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        master.after(50, master.focus_force)
