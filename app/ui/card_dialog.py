"""Cửa sổ nhập số thẻ khi xe vào / xe ra."""

import customtkinter as ctk

from ..core.storage import CARD_PATTERN
from .modal import ModalDialog
from .theme import C, ImageBox, font, primary_button, secondary_button, ui_scale


class CardDialog(ModalDialog):
    """
    kind      : "IN" hoặc "OUT"
    photo     : ảnh PIL vừa chụp (None nếu camera mất tín hiệu)
    on_submit : hàm nhận số thẻ, trả về chuỗi lỗi hoặc None nếu thành công
    preview   : (tùy chọn) hàm nhận số thẻ đang gõ, trả về dòng thông tin (giờ vào, tiền gửi) hoặc None
    """

    def __init__(self, master, kind, photo, when, on_submit, preview=None):
        is_in = kind == "IN"
        super().__init__(master, "Xe vào" if is_in else "Xe ra")
        self.on_submit = on_submit
        self.preview = preview
        color = C["in"] if is_in else C["out"]
        hover = C["in_hover"] if is_in else C["out_hover"]
        soft = C["in_soft"] if is_in else C["out_soft"]

        # ----- tiêu đề màu -----
        header = ctk.CTkFrame(self, fg_color=color, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="↓" if is_in else "↑", width=56, height=56, corner_radius=16,
                     fg_color=hover, text_color="white", font=font(30, True)).pack(side="left", padx=(24, 14), pady=18)
        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left", pady=18)
        ctk.CTkLabel(titles, text="XE VÀO BÃI" if is_in else "XE RA KHỎI BÃI", font=font(24, True),
                     text_color="white", height=32).pack(anchor="w")
        gate = "Cổng vào" if is_in else "Cổng ra"
        ctk.CTkLabel(titles, text=f"{gate}   ·   chụp lúc {when:%H:%M:%S   %d/%m/%Y}", font=font(13),
                     text_color="white", height=20).pack(anchor="w")

        # ----- ảnh vừa chụp -----
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", padx=26, pady=(20, 24))
        s = ui_scale(self)
        frame = ctk.CTkFrame(body, fg_color=C["photo_bg"], corner_radius=14, border_width=1, border_color=C["border"])
        frame.pack()
        # giới hạn theo màn hình để hộp thoại không cao quá, tràn ra ngoài màn hình thấp
        box_w = min(int(540 * s), int(self.winfo_screenwidth() * 0.42),
                    int(self.winfo_screenheight() * 0.33 * 540 / 304))
        box = ImageBox(frame, width=box_w, height=int(box_w * 304 / 540),
                       placeholder="Không có ảnh\nCamera đang mất tín hiệu")
        box.pack(padx=8, pady=8)
        box.show(photo)

        # ----- ô nhập số thẻ -----
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=(18, 6))
        ctk.CTkLabel(row, text="SỐ THẺ", font=font(12, True), text_color=C["muted"]).pack(side="left")
        ctk.CTkLabel(row, text="Gõ số in trên thẻ rồi nhấn Enter", font=font(12),
                     text_color="#94a3b8").pack(side="right")
        self.entry = ctk.CTkEntry(body, font=font(42, True), height=80, justify="center", corner_radius=14,
                                  fg_color=soft, border_color=color, border_width=2, text_color=C["text"])
        self.entry.pack(fill="x")
        if preview is not None:
            self.info = ctk.CTkLabel(body, text="", font=font(15, True), text_color=C["out_text"],
                                     fg_color="transparent", corner_radius=8, height=34)
            self.info.pack(fill="x", pady=(10, 0))
            self.entry.bind("<KeyRelease>", lambda _e: self._update_preview())
        self.error = ctk.CTkLabel(body, text="", font=font(13, True), text_color=C["danger"],
                                  fg_color="transparent", corner_radius=8, height=30)
        self.error.pack(fill="x", pady=(10, 0))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        secondary_button(buttons, "Hủy   (Esc)", self.close, height=52, font=font(15, True)).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        primary_button(buttons, ("Cho xe vào" if is_in else "Cho xe ra") + "   (Enter)", self.submit,
                       color=color, hover=hover, height=52, font=font(15, True)).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        self.entry.bind("<Return>", lambda _e: self.submit())
        self.entry.bind("<KP_Enter>", lambda _e: self.submit())
        self.focus_target = self.entry
        self.present()

    def _update_preview(self):
        card = self.entry.get().strip().upper()
        text = self.preview(card) if CARD_PATTERN.match(card) else None
        if text:
            self.info.configure(text=text, fg_color=C["out_soft"])
        else:
            self.info.configure(text="", fg_color="transparent")

    def submit(self):
        card = self.entry.get().strip().upper()
        if not card:
            return self._fail("Chưa nhập số thẻ")
        if not CARD_PATTERN.match(card):
            return self._fail("Số thẻ chỉ gồm chữ và số, tối đa 20 ký tự")
        error = self.on_submit(card)
        if error:
            return self._fail(error)
        self.close()

    def _fail(self, message):
        self.error.configure(text=f"⚠   {message}", fg_color=C["danger_soft"])
        self.bell()
        self.entry.delete(0, "end")
        self.entry.focus_set()
