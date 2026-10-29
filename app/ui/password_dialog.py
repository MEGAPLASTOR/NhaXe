"""Hộp nhập mật khẩu quản lý (mở Cài đặt, reset dữ liệu) và hộp đổi mật khẩu."""

import customtkinter as ctk

from .modal import ModalDialog
from .theme import C, font, primary_button, secondary_button

MIN_LENGTH = 4


def _header(win, title, subtitle):
    header = ctk.CTkFrame(win, fg_color=C["brand_navy"], corner_radius=0)
    header.pack(fill="x")
    ctk.CTkLabel(header, text="🔒", width=56, height=56, corner_radius=16, fg_color=C["accent"],
                 text_color="white", font=font(26, True)).pack(side="left", padx=(24, 14), pady=18)
    titles = ctk.CTkFrame(header, fg_color="transparent")
    titles.pack(side="left", pady=18, padx=(0, 24))
    ctk.CTkLabel(titles, text=title, font=font(22, True), text_color="white", height=30).pack(anchor="w")
    ctk.CTkLabel(titles, text=subtitle, font=font(13), text_color="#cbd5e1", height=20).pack(anchor="w")


def _password_entry(master, **kw):
    kw.setdefault("font", font(22, True))
    kw.setdefault("height", 54)
    return ctk.CTkEntry(master, show="•", justify="center", corner_radius=12, fg_color=C["surface2"],
                        border_color=C["accent"], border_width=2, text_color=C["text"], width=420, **kw)


class PasswordDialog(ModalDialog):
    """
    check      : hàm nhận mật khẩu, trả về True nếu đúng
    on_success : hàm gọi sau khi nhập đúng (hộp đã đóng)
    """

    def __init__(self, master, check, on_success, purpose="mở Cài đặt"):
        super().__init__(master, "Nhập mật khẩu")
        self.check = check
        self.on_success = on_success
        _header(self, "MẬT KHẨU QUẢN LÝ", f"Nhập mật khẩu để {purpose}")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", padx=26, pady=(20, 24))
        ctk.CTkLabel(body, text="MẬT KHẨU", font=font(12, True), text_color=C["muted"]).pack(anchor="w")
        self.entry = _password_entry(body)
        self.entry.pack(fill="x", pady=(4, 0))
        self.entry.bind("<Return>", lambda _e: self.submit())
        self.entry.bind("<KP_Enter>", lambda _e: self.submit())
        self.error = ctk.CTkLabel(body, text="", font=font(13, True), text_color=C["danger"],
                                  fg_color="transparent", corner_radius=8, height=30)
        self.error.pack(fill="x", pady=(10, 0))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        secondary_button(buttons, "Hủy   (Esc)", self.close, height=48, font=font(14, True)).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        primary_button(buttons, "Mở khóa   (Enter)", self.submit, height=48, font=font(14, True)).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        self.focus_target = self.entry
        self.present()

    def submit(self):
        if not self.check(self.entry.get()):
            self.error.configure(text="⚠   Sai mật khẩu, vui lòng nhập lại", fg_color=C["danger_soft"])
            self.bell()
            self.entry.delete(0, "end")
            self.entry.focus_set()
            return
        master = self.master
        self.close()
        master.after(80, self.on_success)


class ChangePasswordDialog(ModalDialog):
    """
    check   : hàm nhận mật khẩu, trả về True nếu đúng mật khẩu hiện tại
    on_done : hàm nhận mật khẩu mới (đã kiểm tra hợp lệ), lưu lại
    """

    def __init__(self, master, check, on_done):
        super().__init__(master, "Đổi mật khẩu")
        self.check = check
        self.on_done = on_done
        _header(self, "ĐỔI MẬT KHẨU", "Mật khẩu dùng để mở Cài đặt và reset dữ liệu")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", padx=26, pady=(18, 24))
        self.fields = []
        for caption in ("MẬT KHẨU HIỆN TẠI", "MẬT KHẨU MỚI", "NHẬP LẠI MẬT KHẨU MỚI"):
            ctk.CTkLabel(body, text=caption, font=font(12, True), text_color=C["muted"], height=22).pack(
                anchor="w", pady=(6, 0))
            e = _password_entry(body, font=font(18, True), height=46)
            e.pack(fill="x", pady=(2, 0))
            self.fields.append(e)
        for i, e in enumerate(self.fields):
            nxt = self.fields[i + 1] if i + 1 < len(self.fields) else None
            action = (lambda _e, n=nxt: (n.focus_set(), "break")[1]) if nxt else (lambda _e: self.submit())
            e.bind("<Return>", action)
            e.bind("<KP_Enter>", action)
        ctk.CTkLabel(body, text=f"Mật khẩu mới tối thiểu {MIN_LENGTH} ký tự, phân biệt chữ hoa / thường.",
                     font=font(12), text_color=C["muted"]).pack(anchor="w", pady=(8, 0))
        self.error = ctk.CTkLabel(body, text="", font=font(13, True), text_color=C["danger"],
                                  fg_color="transparent", corner_radius=8, height=30)
        self.error.pack(fill="x", pady=(6, 0))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        secondary_button(buttons, "Hủy   (Esc)", self.close, height=48, font=font(14, True)).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        primary_button(buttons, "Đổi mật khẩu", self.submit, height=48, font=font(14, True)).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        self.focus_target = self.fields[0]
        self.present()

    def submit(self):
        current, new, again = (e.get() for e in self.fields)
        if not self.check(current):
            return self._fail("Mật khẩu hiện tại không đúng", 0)
        if len(new) < MIN_LENGTH:
            return self._fail(f"Mật khẩu mới phải có ít nhất {MIN_LENGTH} ký tự", 1)
        if new != again:
            return self._fail("Hai lần nhập mật khẩu mới không giống nhau", 2)
        self.close()
        self.on_done(new)

    def _fail(self, message, index):
        self.error.configure(text=f"⚠   {message}", fg_color=C["danger_soft"])
        self.bell()
        for e in self.fields[index:]:
            e.delete(0, "end")
        self.fields[index].focus_set()
