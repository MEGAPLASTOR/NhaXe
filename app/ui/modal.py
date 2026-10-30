"""Khung chung cho hộp thoại bật lên: đứng yên giữa màn hình, chặn cửa sổ chính, tự đặt con trỏ vào ô nhập."""

import tkinter as tk

import customtkinter as ctk

from .theme import C, brand_icon, show_centered


def _alive(win):
    try:
        return bool(win.winfo_exists())
    except tk.TclError:
        return False


class ModalDialog(ctk.CTkToplevel):
    _open = []     # mọi hộp thoại đang mở, để cửa sổ chính biết lúc nào không được nhận phím tắt
    _opening = 0   # số hộp thoại đang dựng dở

    @classmethod
    def any_open(cls):
        """
        Tính cả hộp thoại đang dựng dở: CustomTkinter gọi update() giữa lúc dựng cửa sổ,
        lúc đó các phím tắt đang chờ sẽ chạy và mở thêm hộp thoại thứ hai nếu không chặn.
        """
        cls._open = [d for d in cls._open if _alive(d)]
        return cls._opening > 0 or bool(cls._open)

    # CustomTkinter hẹn gọi lại 2 hàm này sau khi cửa sổ mở (đặt màu và biểu tượng thanh tiêu đề).
    # Hộp thoại đóng sớm hơn thì chúng nổ lỗi "bad window path name", và nếu lúc đó đang dựng
    # một cửa sổ khác thì cửa sổ đó hỏng theo. Bỏ qua khi cửa sổ không còn.
    def _revert_withdraw_after_windows_set_titlebar_color(self):
        if _alive(self):
            super()._revert_withdraw_after_windows_set_titlebar_color()

    def _windows_set_titlebar_icon(self):
        if _alive(self):
            super()._windows_set_titlebar_icon()

    def __init__(self, master, title):
        ModalDialog._opening += 1
        try:
            super().__init__(master, fg_color=C["surface"])
        finally:
            ModalDialog._opening -= 1
        ModalDialog._open.append(self)
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
        if self in ModalDialog._open:
            ModalDialog._open.remove(self)
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        master.after(50, master.focus_force)
