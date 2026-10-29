"""Hộp xác nhận reset dữ liệu: phải gõ XOA mới xóa được, mặc định giữ bản sao lưu."""

import tkinter as tk

import customtkinter as ctk

from .modal import ModalDialog
from .theme import C, font, primary_button, secondary_button

CONFIRM_WORDS = {"XOA", "XÓA"}


class ResetDialog(ModalDialog):
    """
    summary    : {"records", "parked", "photos"} - số liệu hiện có
    on_confirm : hàm nhận backup (True/False), thực hiện reset
    """

    def __init__(self, master, summary, on_confirm):
        super().__init__(master, "Reset dữ liệu")
        self.on_confirm = on_confirm

        header = ctk.CTkFrame(self, fg_color=C["danger"], corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="!", width=56, height=56, corner_radius=16, fg_color=C["danger_hover"],
                     text_color="white", font=font(30, True)).pack(side="left", padx=(24, 14), pady=18)
        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left", pady=18)
        ctk.CTkLabel(titles, text="RESET DỮ LIỆU", font=font(24, True), text_color="white", height=32).pack(anchor="w")
        ctk.CTkLabel(titles, text="Xóa toàn bộ lượt gửi xe và ảnh, bắt đầu lại từ đầu", font=font(13),
                     text_color="white", height=20).pack(anchor="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", padx=26, pady=(20, 24))

        # ----- số liệu sẽ bị xóa -----
        stats = ctk.CTkFrame(body, fg_color="transparent")
        stats.pack(fill="x")
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform="s")
        for col, (key, title) in enumerate((("records", "LƯỢT GỬI"), ("parked", "XE ĐANG GỬI"), ("photos", "ẢNH"))):
            chip = ctk.CTkFrame(stats, fg_color=C["danger_soft"], corner_radius=14)
            chip.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
            ctk.CTkLabel(chip, text=title, font=font(10, True), text_color=C["danger"], height=16).pack(
                anchor="w", padx=16, pady=(10, 0))
            ctk.CTkLabel(chip, text=str(summary[key]), font=font(26, True), text_color=C["danger"], height=34).pack(
                anchor="w", padx=16, pady=(0, 10))
        if summary["parked"]:
            ctk.CTkLabel(body, text=f"⚠   Còn {summary['parked']} xe đang gửi trong bãi — sau khi reset sẽ không "
                                    f"tra được thẻ của các xe này.", font=font(12, True), text_color=C["warn"],
                         fg_color=C["warn_soft"], corner_radius=8, height=30).pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(body, text="•  Cài đặt camera, phím tắt và các file Excel đã xuất vẫn được giữ.",
                     font=font(13), text_color=C["muted"], justify="left").pack(anchor="w", pady=(14, 6))
        self.backup = tk.BooleanVar(self, value=True)
        ctk.CTkCheckBox(body, text="Lưu bản sao lưu vào data/sao_luu trước khi xóa (khuyên dùng)",
                        variable=self.backup, font=font(13, True), text_color=C["text2"], corner_radius=6,
                        fg_color=C["accent"], hover_color=C["accent_hover"], border_color="#cbd5e1").pack(
            anchor="w", pady=(2, 14))

        ctk.CTkLabel(body, text="GÕ  XOA  ĐỂ XÁC NHẬN", font=font(12, True), text_color=C["muted"]).pack(anchor="w")
        self.entry = ctk.CTkEntry(body, font=font(26, True), height=56, justify="center", corner_radius=12,
                                  fg_color=C["surface2"], border_color=C["danger"], border_width=2,
                                  text_color=C["text"], width=480)
        self.entry.pack(fill="x", pady=(4, 0))
        self.entry.bind("<KeyRelease>", lambda _e: self._update_button())
        self.entry.bind("<Return>", lambda _e: self.submit())

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(18, 0))
        secondary_button(buttons, "Hủy   (Esc)", self.close, height=50, font=font(15, True)).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        self.confirm_btn = primary_button(buttons, "Xóa toàn bộ dữ liệu", self.submit, color=C["danger"],
                                          hover=C["danger_hover"], height=50, font=font(15, True))
        self.confirm_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self._update_button()

        self.focus_target = self.entry
        self.present()

    def _confirmed(self):
        return self.entry.get().strip().upper() in CONFIRM_WORDS

    def _update_button(self):
        self.confirm_btn.configure(state="normal" if self._confirmed() else "disabled",
                                   fg_color=C["danger"] if self._confirmed() else "#fca5a5")

    def submit(self):
        if not self._confirmed():
            self.bell()
            return
        backup = self.backup.get()
        self.close()
        self.on_confirm(backup)
