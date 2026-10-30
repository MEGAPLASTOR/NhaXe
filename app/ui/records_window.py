"""Xem chi tiết lượt gửi, danh sách xe đang gửi, lịch sử gửi xe và lịch sử theo từng ngày."""

from datetime import date, datetime, timedelta

import customtkinter as ctk

from ..core.pricing import money
from ..core.storage import parse_time, record_duration, vn_time
from .modal import ModalDialog
from .photo_viewer import PhotoViewer
from .theme import (C, WEEKDAYS, ImageBox, entry, font, load_image, make_tree, only_digits, open_file, pill, primary_button,
                    secondary_button, segmented, show_centered, tabview, ui_scale, zebra, brand_icon)


def parse_day(text):
    text = text.strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(text)


def fee_text(fee_of, rec):
    if fee_of is None:
        return "—"
    amount, estimate = fee_of(rec)
    return f"{money(amount)} (tạm tính)" if estimate else money(amount)


def day_time(text, day):
    """Giờ trong ngày đang xem thì chỉ hiện giờ, ngày khác thì kèm ngày/tháng."""
    dt = parse_time(text)
    if dt is None:
        return "—"
    return dt.strftime("%H:%M:%S") if dt.date() == day else dt.strftime("%H:%M  %d/%m")


class RecordView(ctk.CTkFrame):
    """Thẻ thông tin 1 lượt gửi: số thẻ, trạng thái, giờ vào/ra và 2 ảnh vào/ra (nhấp đúp để mở ảnh gốc)."""

    def __init__(self, master, storage, title, vertical=False, on_undo=None, fee_of=None, on_exit=None,
                 photo_boxes=None):
        """photo_boxes: (ô ảnh vào, ô ảnh ra) nằm ở chỗ khác để hiện ảnh; có thì 2 ô của khung này
        thành ô camera trực tiếp (self.live_in / self.live_out)."""
        super().__init__(master, fg_color=C["surface"], corner_radius=16, border_width=1, border_color=C["border"])
        self.storage = storage
        self.fee_of = fee_of  # hàm nhận 1 lượt, trả về (tiền gửi, tạm tính hay không)
        self.on_undo = on_undo
        self.on_exit = on_exit   # hàm nhận số thẻ, mở luôn cửa sổ cho xe ra
        self.undo_id = None   # lượt được phép hoàn tác (lượt ra vừa ghi nhận)
        self.record = None
        self._dang_mo = False  # đang dựng cửa sổ xem ảnh

        head = ctk.CTkFrame(self, fg_color="transparent")
        self.title_label = ctk.CTkLabel(head, text=title, font=font(15, True), text_color=C["text"])
        self.title_label.pack(side="left")
        self.hint_label = ctk.CTkLabel(head, text="bấm vào ảnh để phóng to", font=font(11), text_color=C["muted"])
        self.hint_label.pack(side="right")

        # ----- vé số thẻ + thông tin -----
        info = ctk.CTkFrame(self, fg_color="transparent")
        # Màn hình chính: thẻ và thông tin nằm ngang trong 1 hàng. Hàng này phải tạo TRƯỚC rồi làm khung cha của
        # thẻ / thông tin; nếu tạo sau rồi pack(in_=...) thì nó nằm đè lên và che mất số thẻ, giờ, tiền.
        holder = info if vertical else ctk.CTkFrame(info, fg_color="transparent")
        self.ticket = ctk.CTkFrame(holder, corner_radius=14, fg_color=C["surface2"])
        # ở màn hình chính thẻ này phải gọn để nhường chỗ cho 2 khung camera
        self.ticket_caption = ctk.CTkLabel(self.ticket, text="SỐ THẺ", font=font(11, True), height=16)
        self.ticket_caption.pack(anchor="w", padx=16, pady=(10 if vertical else 8, 0))
        self.card_label = ctk.CTkLabel(self.ticket, text="—", font=font(40 if vertical else 30, True),
                                       height=48 if vertical else 36)
        self.card_label.pack(anchor="w", padx=16)
        self.badge = ctk.CTkLabel(self.ticket, text="", font=font(11, True), text_color="white",
                                  corner_radius=8, height=24 if vertical else 20)
        self.badge.pack(anchor="w", padx=16, pady=(2, 12 if vertical else 8))

        details = ctk.CTkFrame(holder, fg_color="transparent")
        self.values = {}
        rows = [("vao", "Giờ vào"), ("ra", "Giờ ra"), ("gui", "Thời gian gửi")]
        if fee_of is not None:
            rows.append(("tien", "Tiền gửi"))
        for i, (key, caption) in enumerate(rows):
            row_h = 24 if vertical else 21
            ctk.CTkLabel(details, text=caption, font=font(12), text_color=C["muted"], height=row_h).grid(
                row=i, column=0, sticky="w")
            is_fee = key == "tien"
            value = ctk.CTkLabel(details, text="", font=font(20 if is_fee else 13, True),
                                 text_color=C["accent"] if is_fee else C["text2"],
                                 height=row_h + 8 if is_fee else row_h)
            value.grid(row=i, column=1, sticky="w", padx=(14, 0))
            self.values[key] = value
        # Cửa sổ tra cứu: 2 nút nằm dưới cột thông tin. Màn hình chính: nằm trên hàng tiêu đề cho khu này thấp gọn.
        self.nut = ctk.CTkFrame(info if vertical else head, fg_color="transparent")
        self._nut_pack = {"fill": "x", "pady": (10, 0)} if vertical else {"side": "left", "padx": (16, 0)}
        self.undo_btn = ctk.CTkButton(self.nut, text="↶   Hoàn tác lượt ra", command=self._undo, height=34,
                                      corner_radius=10, fg_color=C["surface"], border_width=1,
                                      border_color="#fca5a5", text_color=C["danger"],
                                      hover_color=C["danger_soft"], font=font(12, True))
        self.exit_btn = ctk.CTkButton(self.nut, text="↑   Cho xe này ra", command=self._cho_ra, height=34,
                                      corner_radius=10, fg_color=C["out"], hover_color=C["out_hover"],
                                      text_color="white", font=font(12, True))
        if vertical:  # cửa sổ tra cứu: xếp dọc cho dễ đọc
            self.ticket.pack(fill="x")
            details.pack(fill="x", pady=(10, 0))
        else:         # màn hình chính: thẻ và thông tin nằm ngang cho thấp
            holder.pack(fill="x")
            self.ticket.pack(side="left", anchor="n")
            details.pack(side="left", anchor="n", padx=(16, 0))

        # ----- 2 ô ảnh -----
        images = ctk.CTkFrame(self, fg_color="transparent")
        min_h = int((200 if vertical else 150) * ui_scale(self))
        if photo_boxes is None:
            self.box_in = ImageBox(images, height=min_h, on_click=lambda: self._zoom("anh_vao"))
            self.box_out = ImageBox(images, height=min_h, on_click=lambda: self._zoom("anh_ra"))
            cap_in = pill(images, "↓  ẢNH LÚC VÀO", C["in_text"], C["in_soft"], size=11)
            cap_out = pill(images, "↑  ẢNH LÚC RA", C["out_text"], C["out_soft"], size=11)
            slot_in, slot_out = self.box_in, self.box_out
        else:
            # màn hình chính: ảnh đã chụp hiện ở 2 khung lớn phía trên, 2 ô này dành cho camera trực tiếp
            self.box_in, self.box_out = photo_boxes
            self.live_in = ImageBox(images, height=min_h, placeholder="Đang kết nối camera...", dark=True)
            self.live_out = ImageBox(images, height=min_h, placeholder="Đang kết nối camera...", dark=True)
            cap_in = pill(images, "●  CAMERA CỔNG VÀO", C["in_text"], C["in_soft"], size=11)
            cap_out = pill(images, "●  CAMERA CỔNG RA", C["out_text"], C["out_soft"], size=11)
            slot_in, slot_out = self.live_in, self.live_out
            self.hint_label.configure(text="bấm vào ảnh phía trên để phóng to")

        if vertical:
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(2, weight=1)
            head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
            info.grid(row=1, column=0, sticky="ew", padx=18)
            images.grid(row=2, column=0, sticky="nsew", padx=18, pady=(14, 18))
            images.grid_columnconfigure(0, weight=1)
            images.grid_rowconfigure((1, 3), weight=1, uniform="img")
            cap_in.grid(row=0, column=0, sticky="w", pady=(0, 6))
            self.box_in.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
            cap_out.grid(row=2, column=0, sticky="w", pady=(0, 6))
            self.box_out.grid(row=3, column=0, sticky="nsew")
        else:
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(1, weight=1)
            head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(10, 8))
            info.grid(row=1, column=0, sticky="nw", padx=(18, 18), pady=(0, 12))
            images.grid(row=1, column=1, sticky="nsew", padx=(0, 16), pady=(0, 12))
            images.grid_columnconfigure((0, 1), weight=1, uniform="img")
            images.grid_rowconfigure(1, weight=1)
            cap_in.grid(row=0, column=0, sticky="w", pady=(0, 6))
            slot_in.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
            cap_out.grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 6))
            slot_out.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        self.clear()

    def _paint_ticket(self, color, soft):
        self.ticket.configure(fg_color=soft)
        self.ticket_caption.configure(text_color=color)
        self.card_label.configure(text_color=color)
        self.badge.configure(fg_color=color if self.badge.cget("text") else soft)

    def clear(self, text="Chưa có lượt nào"):
        self.record = None
        self.card_label.configure(text="—")
        self.badge.configure(text="")
        self._paint_ticket(C["muted"], C["surface2"])
        for value in self.values.values():
            value.configure(text="—")
        self.box_in.show(None, text)
        self.box_out.show(None, text)
        self._nut_hien(undo=False, cho_ra=False)

    def show(self, rid, title=None):
        if title:
            self.title_label.configure(text=title)
        rec = self.storage.get(rid) if rid is not None else None
        if rec is None:
            self.clear()
            return
        self.record = rec
        parked = rec["gio_ra"] is None
        self.card_label.configure(text=rec["so_the"])
        self.badge.configure(text="   ĐANG GỬI   " if parked else "   ĐÃ RA   ")
        if parked:
            self._paint_ticket(C["in_text"], C["in_soft"])
        else:
            self._paint_ticket(C["out_text"], C["out_soft"])
        self.values["vao"].configure(text=vn_time(rec["gio_vao"]))
        self.values["ra"].configure(text=vn_time(rec["gio_ra"]) if not parked else "Chưa ra")
        self.values["gui"].configure(text=record_duration(rec))
        if "tien" in self.values:
            self.values["tien"].configure(text=fee_text(self.fee_of, rec))
        self._show_photo(self.box_in, rec["anh_vao"], "Không có ảnh vào")
        self._show_photo(self.box_out, rec["anh_ra"], "Xe chưa ra" if parked else "Không có ảnh ra")
        self._nut_hien(undo=bool(self.on_undo) and not parked and rec["id"] == self.undo_id,
                       cho_ra=bool(self.on_exit) and parked)

    def _nut_hien(self, undo, cho_ra):
        """Xe đang gửi thì cho nút cho ra; lượt vừa ghi ra thì cho nút hoàn tác."""
        for nut, hien in ((self.exit_btn, cho_ra), (self.undo_btn, undo)):
            nut.pack(side="left", padx=(0, 8)) if hien else nut.pack_forget()
        # không có nút nào thì giấu cả hàng đi, khỏi chiếm chỗ của 2 ảnh
        self.nut.pack(**self._nut_pack) if (undo or cho_ra) else self.nut.pack_forget()

    def _cho_ra(self):
        if self.record is not None and self.on_exit:
            self.on_exit(self.record["so_the"])

    def _show_photo(self, box, rel, empty_text):
        image = load_image(self.storage.abs_path(rel))
        if image is None and rel:
            empty_text = "Không còn file ảnh\n(đã xóa hoặc quá thời gian lưu)"
        box.show(image, empty_text)

    def refresh(self):
        if self.record is not None:
            self.show(self.record["id"])

    def _zoom(self, key):
        """Bấm vào ảnh thì mở cửa sổ xem ảnh to."""
        rec = self.record
        # Bấm nhanh 2 cái sẽ mở 2 cửa sổ chồng nhau rồi lỗi. Cờ _dang_mo chặn cú bấm thứ hai
        # rơi vào giữa lúc đang dựng cửa sổ, any_open chặn các cú bấm sau khi đã dựng xong.
        if rec is None or not rec[key] or self._dang_mo or ModalDialog.any_open():
            return
        is_in = key == "anh_vao"
        self._dang_mo = True
        try:
            PhotoViewer(self.winfo_toplevel(), self.storage.abs_path(rec[key]),
                        f"Thẻ {rec['so_the']}   ·   {'ẢNH LÚC VÀO' if is_in else 'ẢNH LÚC RA'}",
                        vn_time(rec["gio_vao"] if is_in else rec["gio_ra"]),
                        C["in"] if is_in else C["out"])
        finally:
            self._dang_mo = False

    def _undo(self):
        if self.record is not None and self.on_undo:
            self.on_undo(self.record["id"])


class RecordsWindow(ctk.CTkToplevel):
    """Cửa sổ tra cứu: tab Xe đang gửi, Lịch sử gửi xe (tìm theo số thẻ, ngày, trạng thái) và Theo từng ngày."""

    TABS = ("Xe đang gửi", "Lịch sử gửi xe", "Theo từng ngày")
    STATUS = {"Tất cả": "all", "Đang gửi": "in", "Đã ra": "out"}
    SIZE = (1280, 760)

    def __init__(self, master, storage, tab=0, fee_of=None, on_exit=None):
        super().__init__(master, fg_color=C["bg"])
        self.withdraw()  # ẩn cho đến khi đặt đúng giữa màn hình
        self.storage = storage
        self.fee_of = fee_of
        self.history_rows = []
        self.day_rows = []
        self.day = date.today()
        self.title("Tra cứu xe gửi")
        brand_icon(self)
        self.geometry(f"{self.SIZE[0]}x{self.SIZE[1]}")
        self.minsize(1040, 620)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 0))
        ctk.CTkLabel(head, text="Tra cứu xe gửi", font=font(22, True), text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(head, text="Xem xe đang gửi, tìm lại lịch sử theo số thẻ, xem từng ngày", font=font(12),
                     text_color=C["muted"]).pack(side="left", padx=14, pady=(6, 0))

        self.tabs = tabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=(20, 8), pady=(4, 20))
        self._build_parked(self.tabs.add(self.TABS[0]))
        self._build_history(self.tabs.add(self.TABS[1]))
        self._build_daily(self.tabs.add(self.TABS[2]))

        self.detail = RecordView(self, storage, "Chi tiết lượt gửi", vertical=True, fee_of=fee_of,
                                 on_exit=self._cho_xe_ra if on_exit else None)
        self._on_exit = on_exit
        self.detail.clear("Chọn 1 dòng trong bảng")
        self.detail.grid(row=1, column=1, sticky="nsew", padx=(8, 20), pady=(18, 20))

        self.refresh()
        self.show_tab(tab)
        show_centered(self, self.SIZE)
        self.after(150, self._bring_front)

    def _bring_front(self):
        self.lift()
        self.focus_force()

    def show_tab(self, index):
        self.tabs.set(self.TABS[index])

    def refresh(self):
        self.load_parked()
        self.search_history()
        self.load_day()
        self.detail.refresh()

    # ----- tab xe đang gửi -----
    def _build_parked(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 12))
        self.parked_search = only_digits(entry(bar, placeholder_text="Tìm theo số thẻ...", width=260))
        self.parked_search.pack(side="left")
        self.parked_search.bind("<KeyRelease>", lambda _e: self.load_parked())
        secondary_button(bar, "Làm mới", self.refresh, width=110, height=38).pack(side="left", padx=8)
        self.parked_count = pill(bar, "", C["in_text"], C["in_soft"], size=13)
        self.parked_count.pack(side="right")

        holder, self.parked_tree = make_tree(tab, [
            ("stt", "#", 50, "center"),
            ("the", "Số thẻ", 120, "center"),
            ("vao", "Giờ vào", 220, "center"),
            ("gui", "Đã gửi", 180, "center"),
        ])
        holder.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.parked_tree.bind("<<TreeviewSelect>>", lambda _e: self._select(self.parked_tree))

    def load_parked(self):
        rows = self.storage.list_parked(self.parked_search.get().strip().upper())
        tree = self.parked_tree
        tree.delete(*tree.get_children())
        for i, r in enumerate(rows):
            tree.insert("", "end", iid=str(r["id"]), tags=zebra(i),
                        values=(i + 1, r["so_the"], vn_time(r["gio_vao"]), record_duration(r)))
        self.parked_count.configure(text=f"  {len(rows)} xe đang gửi  ")

    # ----- tab lịch sử -----
    def _build_history(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        row1 = ctk.CTkFrame(tab, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 10))
        self.h_card = only_digits(entry(row1, placeholder_text="Số thẻ", width=120))
        self.h_card.pack(side="left")
        ctk.CTkLabel(row1, text="Từ ngày", font=font(13), text_color=C["muted"]).pack(side="left", padx=(16, 6))
        self.h_from = entry(row1, placeholder_text="dd/mm/yyyy", width=130)
        self.h_from.pack(side="left")
        ctk.CTkLabel(row1, text="đến", font=font(13), text_color=C["muted"]).pack(side="left", padx=6)
        self.h_to = entry(row1, placeholder_text="dd/mm/yyyy", width=130)
        self.h_to.pack(side="left")
        primary_button(row1, "Tìm kiếm", self.search_history, width=110, height=38).pack(side="left", padx=(12, 6))
        secondary_button(row1, "Xuất Excel", self.export, width=110, height=38).pack(side="left")
        for e in (self.h_card, self.h_from, self.h_to):
            e.bind("<Return>", lambda _e: self.search_history())

        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 12))
        for text, back_from, back_to in (("Hôm nay", 0, 0), ("Hôm qua", 1, 1), ("7 ngày", 6, 0),
                                         ("30 ngày", 29, 0), ("Mọi ngày", None, None)):
            secondary_button(row2, text, lambda a=back_from, b=back_to: self.set_range(a, b),
                             width=80, height=30, font=font(12)).pack(side="left", padx=(0, 6))
        self.h_status = segmented(row2, list(self.STATUS), command=lambda _v: self.search_history(), height=30)
        self.h_status.set("Tất cả")
        self.h_status.pack(side="left", padx=(10, 0))
        self.h_count = ctk.CTkLabel(row2, text="", font=font(13, True), text_color=C["muted"])
        self.h_count.pack(side="right")

        holder, self.h_tree = make_tree(tab, [
            ("the", "Số thẻ", 80, "center"),
            ("vao", "Giờ vào", 160, "center"),
            ("ra", "Giờ ra", 160, "center"),
            ("gui", "Thời gian gửi", 120, "center"),
            ("tt", "Trạng thái", 100, "center"),
            ("tien", "Tiền gửi", 100, "center"),
        ])
        holder.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.h_tree.bind("<<TreeviewSelect>>", lambda _e: self._select(self.h_tree))
        self.set_range(0, 0, search=False)

    def set_range(self, back_from, back_to, search=True):
        """Đặt khoảng ngày lùi lại so với hôm nay (None = bỏ lọc theo ngày)."""
        for e in (self.h_from, self.h_to):
            e.delete(0, "end")
        if back_from is not None:
            today = date.today()
            self.h_from.insert(0, (today - timedelta(days=back_from)).strftime("%d/%m/%Y"))
            self.h_to.insert(0, (today - timedelta(days=back_to)).strftime("%d/%m/%Y"))
        if search:
            self.search_history()

    def search_history(self):
        try:
            day_from, day_to = parse_day(self.h_from.get()), parse_day(self.h_to.get())
        except ValueError:
            self.h_count.configure(text="Ngày không hợp lệ — nhập dạng dd/mm/yyyy", text_color=C["danger"])
            return
        day_from, day_to = day_from or day_to, day_to or day_from
        if day_from and day_from > day_to:
            day_from, day_to = day_to, day_from
        rows = self.storage.search(self.h_card.get().strip().upper(), day_from, day_to,
                                   self.STATUS[self.h_status.get()])
        self.history_rows = rows
        tree = self.h_tree
        tree.delete(*tree.get_children())
        for i, r in enumerate(rows):
            parked = r["gio_ra"] is None
            tree.insert("", "end", iid=str(r["id"]), tags=("IN" if parked else "OUT", *zebra(i)),
                        values=(r["so_the"], vn_time(r["gio_vao"]), vn_time(r["gio_ra"]), record_duration(r),
                                "●  Đang gửi" if parked else "●  Đã ra", self._fee_cell(r)))
        self.h_count.configure(text=f"Tìm thấy {len(rows)} lượt", text_color=C["muted"])

    def export(self):
        if not self.history_rows:
            self.h_count.configure(text="Không có dữ liệu để xuất", text_color=C["warn"])
            return
        path = self.storage.export_csv(self.history_rows, self.fee_of)
        self.h_count.configure(text=f"Đã xuất {path.name}", text_color=C["in_text"])
        open_file(path.parent)

    def _fee_cell(self, rec):
        if self.fee_of is None:
            return "—"
        amount, estimate = self.fee_of(rec)
        return f"~ {money(amount)}" if estimate else money(amount)

    # ----- tab theo từng ngày -----
    def _build_daily(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 10))
        secondary_button(bar, "‹", lambda: self.shift_day(-1), width=42, height=38, font=font(22, True)).pack(side="left")
        self.d_entry = entry(bar, width=140, justify="center", font=font(15, True), placeholder_text="dd/mm/yyyy")
        self.d_entry.pack(side="left", padx=6)
        self.d_next = secondary_button(bar, "›", lambda: self.shift_day(1), width=42, height=38, font=font(22, True))
        self.d_next.pack(side="left")
        secondary_button(bar, "Hôm nay", lambda: self.set_day(date.today()), width=90, height=38).pack(
            side="left", padx=(10, 0))
        self.d_title = ctk.CTkLabel(bar, text="", font=font(14, True), text_color=C["text2"])
        self.d_title.pack(side="left", padx=14)
        secondary_button(bar, "Xuất Excel", self.export_day, width=110, height=38).pack(side="right")
        self.d_entry.bind("<Return>", lambda _e: self._entry_day())

        chips = ctk.CTkFrame(tab, fg_color="transparent")
        chips.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 12))
        chips.grid_columnconfigure(tuple(range(5)), weight=1, uniform="chip")
        self.d_stats = {}
        for col, (key, title, color, soft) in enumerate((
                ("total", "XE TRONG NGÀY", C["accent"], C["accent_soft"]),
                ("in", "VÀO", C["in_text"], C["in_soft"]),
                ("out", "RA", C["out_text"], C["out_soft"]),
                ("stay", "CÒN TRONG BÃI", C["stay"], C["stay_soft"]),
                ("money", "TIỀN THU (XE ĐÃ RA)", C["brand_navy"], "#dbe4ee"))):
            chip = ctk.CTkFrame(chips, fg_color=soft, corner_radius=12)
            chip.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
            ctk.CTkLabel(chip, text=title, font=font(10, True), text_color=color, height=16).pack(
                anchor="w", padx=12, pady=(8, 0))
            value = ctk.CTkLabel(chip, text="0", font=font(20, True), text_color=color, height=28)
            value.pack(anchor="w", padx=12, pady=(0, 8))
            self.d_stats[key] = value

        holder, self.d_tree = make_tree(tab, [
            ("the", "Số thẻ", 70, "center"),
            ("vao", "Giờ vào", 110, "center"),
            ("ra", "Giờ ra", 110, "center"),
            ("gui", "Thời gian gửi", 160, "center"),
            ("tt", "Trạng thái", 120, "center"),
            ("tien", "Tiền gửi", 110, "center"),
        ])
        holder.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.d_tree.bind("<<TreeviewSelect>>", lambda _e: self._select(self.d_tree))
        self.d_note = ctk.CTkLabel(tab, text="Xe đang gửi hiện ở mọi ngày từ ngày vào đến hôm nay; xe đã ra chỉ hiện "
                                             "đến ngày ra.   ~ = tiền tạm tính đến hiện tại.",
                                   font=font(12), text_color=C["muted"])
        self.d_note.grid(row=3, column=0, sticky="w", padx=8, pady=(4, 0))
        self.set_day(self.day, load=False)

    def set_day(self, day, load=True):
        self.day = min(day, date.today())
        self.d_entry.delete(0, "end")
        self.d_entry.insert(0, self.day.strftime("%d/%m/%Y"))
        if load:
            self.load_day()

    def shift_day(self, step):
        self.set_day(self.day + timedelta(days=step))

    def _entry_day(self):
        try:
            day = parse_day(self.d_entry.get())
        except ValueError:
            day = None
        if day is None:
            self.d_title.configure(text="Ngày không hợp lệ — nhập dạng dd/mm/yyyy", text_color=C["danger"])
            return
        self.set_day(day)

    def load_day(self):
        day, today = self.day, date.today()
        rows = self.storage.day_records(day)
        self.day_rows = rows
        label = "Hôm nay" if day == today else ("Hôm qua" if day == today - timedelta(days=1) else WEEKDAYS[day.weekday()])
        self.d_title.configure(text=f"{label}, {day:%d/%m/%Y}", text_color=C["text2"])
        self.d_next.configure(state="disabled" if day >= today else "normal")

        tree = self.d_tree
        tree.delete(*tree.get_children())
        stats = dict.fromkeys(("total", "in", "out", "stay", "money"), 0)
        d = day.isoformat()
        for i, r in enumerate(rows):
            entered_today = r["gio_vao"][:10] == d
            left_today = r["gio_ra"] is not None and r["gio_ra"][:10] == d
            if left_today:
                status, tag = "●  Đã ra", "OUT"
                if self.fee_of is not None:
                    stats["money"] += self.fee_of(r)[0]
            elif r["gio_ra"] is None and day == today:
                status, tag = "●  Đang gửi", "IN"
            else:
                status, tag = "●  Gửi qua đêm", "STAY"
            stats["total"] += 1
            stats["in"] += entered_today
            stats["out"] += left_today
            stats["stay"] += not left_today
            tree.insert("", "end", iid=str(r["id"]), tags=(tag, *zebra(i)),
                        values=(r["so_the"], day_time(r["gio_vao"], day), day_time(r["gio_ra"], day),
                                record_duration(r), status, self._fee_cell(r)))
        for key, value in stats.items():
            self.d_stats[key].configure(text=money(value) if key == "money" else str(value))

    def export_day(self):
        if not self.day_rows:
            self.d_title.configure(text="Ngày này không có xe để xuất", text_color=C["warn"])
            return
        path = self.storage.export_csv(self.day_rows, self.fee_of, name=f"ngay_{self.day:%d-%m-%Y}")
        self.d_title.configure(text=f"Đã xuất {path.name}", text_color=C["in_text"])
        open_file(path.parent)

    def _cho_xe_ra(self, card):
        """Đóng cửa sổ tra cứu rồi mở cửa sổ xe ra, nếu không hộp thoại sẽ nằm khuất phía sau."""
        on_exit = self._on_exit
        master = self.master
        self.destroy()
        master.after(120, lambda: on_exit(card))

    def _select(self, tree):
        selected = tree.selection()
        if selected:
            self.detail.show(int(selected[0]))
