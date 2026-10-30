"""Cửa sổ xem ảnh phóng to: bấm vào ảnh xe vào / xe ra ở bất kỳ đâu là mở ra."""

import customtkinter as ctk

from .modal import ModalDialog
from .theme import (C, ImageBox, fit_size, font, load_image, open_file, primary_button, screen_limit,
                    secondary_button, ui_scale)


class PhotoViewer(ModalDialog):
    """
    path    : đường dẫn ảnh (có thể không còn file)
    title   : dòng chữ lớn, vd "Thẻ 27  ·  ẢNH LÚC VÀO"
    detail  : dòng chữ nhỏ bên dưới, vd thời gian
    color   : màu nền thanh tiêu đề (xanh cho xe vào, cam cho xe ra)
    """

    def __init__(self, master, path, title, detail="", color=None):
        super().__init__(master, "Xem ảnh")
        self.path = path
        color = color or C["brand_navy"]
        image = load_image(path)

        head = ctk.CTkFrame(self, fg_color=color, corner_radius=0)
        head.pack(fill="x")
        names = ctk.CTkFrame(head, fg_color="transparent")
        names.pack(side="left", padx=24, pady=14)
        ctk.CTkLabel(names, text=title, font=font(18, True), text_color="white", height=26).pack(anchor="w")
        if detail:
            ctk.CTkLabel(names, text=detail, font=font(13), text_color="#e2e8f0", height=20).pack(anchor="w")
        ctk.CTkLabel(head, text="Bấm vào ảnh hoặc Esc để đóng", font=font(12), text_color="#cbd5e1").pack(
            side="right", padx=24)

        # ảnh to hết mức màn hình cho phép, vẫn giữ đúng tỉ lệ
        max_w, max_h = screen_limit(self, 0.92, 0.86)
        box_w, box_h = max_w - int(48 * ui_scale(self)), max_h - int(160 * ui_scale(self))
        if image is not None:
            box_w, box_h = fit_size(image.width, image.height, box_w, box_h)
        else:
            box_w, box_h = min(box_w, int(640 * ui_scale(self))), min(box_h, int(360 * ui_scale(self)))
        box = ImageBox(self, width=box_w, height=box_h, on_click=self.close)
        box.pack(padx=24, pady=(20, 10))
        box.show(image, "Không còn file ảnh\n(đã xóa hoặc quá thời gian lưu)")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(6, 20))
        secondary_button(buttons, "Đóng   (Esc)", self.close, width=160, height=44,
                         font=font(14, True)).pack(side="left")
        if image is not None:
            primary_button(buttons, "Mở bằng trình xem ảnh của Windows", self._open, height=44,
                           font=font(14, True)).pack(side="right")
        self.present()

    def _open(self):
        open_file(self.path)
        self.close()
