"""Màn hình khóa: phủ kín cửa sổ chính, phải nhập mật khẩu quản lý mới dùng tiếp được."""

import customtkinter as ctk

from .. import APP_NAME, COMPANY
from .theme import C, font, logo_image, primary_button


class LockScreen(ctk.CTkFrame):
    """
    check     : hàm nhận mật khẩu, trả về True nếu đúng
    on_unlock : hàm gọi khi mở khóa thành công
    """

    def __init__(self, master, check, on_unlock):
        super().__init__(master, fg_color=C["brand_navy"], corner_radius=0)
        self.check = check
        self.on_unlock = on_unlock
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()

        giua = ctk.CTkFrame(self, fg_color="transparent")
        giua.place(relx=0.5, rely=0.5, anchor="center")

        logo = logo_image(84)
        if logo is not None:
            ctk.CTkLabel(giua, text="", image=logo).pack(pady=(0, 10))
        ctk.CTkLabel(giua, text=COMPANY, font=font(13, True), text_color=C["brand_teal"],
                     height=18).pack()
        ctk.CTkLabel(giua, text=APP_NAME, font=font(30, True), text_color="white",
                     height=40).pack(pady=(0, 6))

        ctk.CTkLabel(giua, text="🔒   MÀN HÌNH ĐANG KHÓA", font=font(15, True), text_color="#fbbf24",
                     fg_color="#1e3a5f", corner_radius=10, height=38, width=320).pack(pady=(10, 4))
        ctk.CTkLabel(giua, text="Nhập mật khẩu quản lý để dùng tiếp", font=font(13),
                     text_color="#cbd5e1", height=22).pack(pady=(0, 14))

        self.entry = ctk.CTkEntry(giua, show="•", justify="center", font=font(22, True), height=54,
                                  width=360, corner_radius=12, fg_color="#1e3a5f",
                                  border_color=C["accent"], border_width=2, text_color="white")
        self.entry.pack()
        self.entry.bind("<Return>", lambda _e: self.submit())
        self.entry.bind("<KP_Enter>", lambda _e: self.submit())

        self.loi = ctk.CTkLabel(giua, text="", font=font(13, True), text_color="#fca5a5",
                                fg_color="transparent", corner_radius=8, height=32)
        self.loi.pack(fill="x", pady=(8, 0))
        primary_button(giua, "Mở khóa   (Enter)", self.submit, width=360, height=48,
                       font=font(15, True)).pack(pady=(4, 0))

        # bấm đâu trong màn khóa cũng trả con trỏ về ô mật khẩu
        for widget in (self, giua):
            widget.bind("<Button-1>", lambda _e: self.entry.focus_set())
        for delay in (50, 200, 500):
            self.after(delay, self._lay_con_tro)

    def _lay_con_tro(self):
        try:
            if self.winfo_exists():
                self.lift()
                self.entry.focus_force()
        except Exception:
            pass

    def submit(self):
        if not self.check(self.entry.get()):
            self.loi.configure(text="⚠   Sai mật khẩu, vui lòng nhập lại", fg_color="#7f1d1d")
            self.bell()
            self.entry.delete(0, "end")
            self.entry.focus_set()
            return
        self.on_unlock()
