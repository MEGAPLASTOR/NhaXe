"""Cửa sổ Cài đặt: phím tắt, camera, giá gửi xe, thời gian lưu ảnh, đổi mật khẩu."""

import copy
import tkinter as tk
from datetime import datetime, timedelta

import customtkinter as ctk

from ..core.keys import (ACTION_TITLES, ACTIONS, COMBO_MODIFIERS, DEFAULT_KEYS, MAX_KEYS, RESERVED, event_key,
                         key_name, keys_text)
from ..core.pricing import fee_detail, detail_text, money, parse_hm, parse_money
from ..core.settings import check_password, hash_password
from .password_dialog import ChangePasswordDialog
from .theme import (C, SCALE_CHOICES, auto_scale, card, entry, font, open_file, pill, primary_button,
                   secondary_button, segmented, brand_icon, show_centered, tabview)

STREAMS = {"0": "Nét (luồng chính)", "1": "Mượt (luồng phụ)"}
SIZE = (940, 700)


class SettingsWindow(ctk.CTkToplevel):
    """
    settings   : cài đặt hiện tại (được sao chép, chỉ áp dụng khi bấm Lưu)
    on_save    : hàm nhận cài đặt mới
    on_cleanup : hàm nhận số ngày giữ ảnh, dọn ảnh cũ ngay và trả về số ảnh đã xóa
    on_reset   : hàm mở hộp xác nhận reset dữ liệu
    on_password: hàm nhận mã băm mật khẩu mới, lưu ngay (không cần bấm Lưu cài đặt)
    """

    def __init__(self, master, settings, on_save, on_cleanup, image_dir, on_reset, on_password):
        super().__init__(master, fg_color=C["bg"])
        self.withdraw()  # ẩn cho đến khi đặt đúng giữa màn hình
        self.settings = copy.deepcopy(settings)
        self.on_save = on_save
        self.on_cleanup = on_cleanup
        self.on_reset = on_reset
        self.on_password = on_password
        self._scale_at_open = self.settings["scale"]
        self.image_dir = image_dir
        self.capturing = None     # (chức năng, vị trí) đang chờ nhấn phím
        self._pending_mod = None  # Ctrl / Alt vừa nhấn khi đang chờ phím (có thể là tổ hợp)

        self.title("Cài đặt")
        brand_icon(self)
        self.geometry(f"{SIZE[0]}x{SIZE[1]}")
        self.minsize(880, 680)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.close)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(18, 0))
        ctk.CTkLabel(head, text="⚙  Cài đặt", font=font(22, True), text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(head, text="Phím tắt, camera, giá gửi xe và thời gian lưu ảnh", font=font(12),
                     text_color=C["muted"]).pack(side="left", padx=14, pady=(6, 0))

        self.tabs = tabview(self)
        self.tabs.pack(fill="both", expand=True, padx=22, pady=(4, 0))
        self._build_keys(self.tabs.add("Phím tắt"))
        self._build_cameras(self.tabs.add("Camera"))
        self._build_prices(self.tabs.add("Giá gửi xe"))
        self._build_storage(self.tabs.add("Lưu trữ ảnh"))
        self._build_display(self.tabs.add("Giao diện"))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=16)
        secondary_button(footer, "🔒  Đổi mật khẩu", self._change_password, width=150, height=42).pack(side="left")
        self.footer_note = ctk.CTkLabel(footer, text="", font=font(13, True), text_color=C["danger"])
        self.footer_note.pack(side="left", padx=14)
        primary_button(footer, "Lưu cài đặt", self.save, width=150, height=42).pack(side="right")
        secondary_button(footer, "Hủy", self.close, width=110, height=42).pack(side="right", padx=8)

        self.bind("<KeyPress>", self._on_key)
        self.bind("<KeyRelease>", self._on_key_release)
        show_centered(self, SIZE)
        self.after(100, self._activate)

    def _activate(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except tk.TclError:
            pass

    # ================= Phím tắt =================
    def _build_keys(self, tab):
        ctk.CTkLabel(tab, text="Bấm vào ô phím rồi nhấn phím muốn dùng (có thể giữ Ctrl / Alt để tạo tổ hợp).   "
                               "Backspace = bỏ phím.   Esc luôn dùng để hủy.",
                     font=font(13), text_color=C["muted"]).pack(anchor="w", padx=10, pady=(10, 12))
        table = card(tab)
        table.pack(fill="x", padx=10)
        table.grid_columnconfigure((1, 2), weight=1)
        for col, title in enumerate(("CHỨC NĂNG", "PHÍM CHÍNH", "PHÍM PHỤ")):
            ctk.CTkLabel(table, text=title, font=font(11, True), text_color=C["muted"]).grid(
                row=0, column=col, sticky="w", padx=20, pady=(14, 4))
        self.key_buttons = {}
        for r, (action, title) in enumerate(ACTIONS, 1):
            pady = (8, 18) if r == len(ACTIONS) else 8
            ctk.CTkLabel(table, text=title, font=font(15, True), text_color=C["text"]).grid(
                row=r, column=0, sticky="w", padx=20, pady=pady)
            for slot in range(MAX_KEYS):
                btn = ctk.CTkButton(table, text="", height=42, corner_radius=10, font=font(14, True),
                                    border_width=1, command=lambda a=action, s=slot: self._start_capture(a, s))
                btn.grid(row=r, column=slot + 1, sticky="ew", padx=(12, 20 if slot else 12), pady=pady)
                self.key_buttons[(action, slot)] = btn

        bottom = ctk.CTkFrame(tab, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=12)
        secondary_button(bottom, "Khôi phục mặc định", self._reset_keys, width=180, height=36).pack(side="left")
        self.key_note = ctk.CTkLabel(bottom, text="", font=font(13, True), text_color=C["accent"])
        self.key_note.pack(side="left", padx=14)
        self._render_keys()

    def _render_keys(self):
        for (action, slot), btn in self.key_buttons.items():
            keys = self.settings["keys"][action]
            if self.capturing == (action, slot):
                btn.configure(text="Nhấn phím bất kỳ...", fg_color=C["accent_soft"], hover_color=C["accent_soft"],
                              text_color=C["accent"], border_color=C["accent"])
            elif slot < len(keys):
                btn.configure(text=key_name(keys[slot]), fg_color=C["surface2"], hover_color=C["hover"],
                              text_color=C["text"], border_color=C["border"])
            else:
                btn.configure(text="+  Thêm phím", fg_color=C["surface"], hover_color=C["surface2"],
                              text_color="#94a3b8", border_color=C["border"])

    def _start_capture(self, action, slot):
        self.capturing = (action, slot)
        self.key_note.configure(text=f"Đang chờ phím cho “{ACTION_TITLES[action]}”...", text_color=C["accent"])
        self._render_keys()
        self.focus_force()

    def _on_key(self, event):
        if self.capturing is None:
            return None
        key = event_key(event)
        if key in COMBO_MODIFIERS:
            # Ctrl / Alt: chờ xem có bấm thêm phím khác (Ctrl + Delete) hay thả ra luôn (dùng Ctrl làm phím)
            self._pending_mod = key
            return "break"
        self._pending_mod = None
        self._assign(key)
        return "break"

    def _on_key_release(self, event):
        if self.capturing is not None and self._pending_mod == event.keysym:
            key, self._pending_mod = self._pending_mod, None
            self._assign(key)

    def _assign(self, key):
        action, slot = self.capturing
        self.capturing = None
        keys = self.settings["keys"][action]
        if key in RESERVED:
            self.key_note.configure(text="Esc được dành để hủy, không gán được", text_color=C["warn"])
        elif key in ("BackSpace", "Delete"):
            if slot < len(keys):
                keys.pop(slot)
            self.key_note.configure(text=f"Đã bỏ phím của “{ACTION_TITLES[action]}”", text_color=C["muted"])
        else:
            note = f"Đã gán {key_name(key)} cho “{ACTION_TITLES[action]}”"
            for other, other_keys in self.settings["keys"].items():
                if other != action and key in other_keys:
                    other_keys.remove(key)
                    note += f"  (đã gỡ khỏi “{ACTION_TITLES[other]}”)"
            new_keys = list(keys)
            if slot < len(new_keys):
                new_keys[slot] = key
            else:
                new_keys.append(key)
            keys[:] = list(dict.fromkeys(new_keys))[:MAX_KEYS]  # bỏ trùng, giữ thứ tự
            self.key_note.configure(text=note, text_color=C["in_text"])
        self._render_keys()

    def _reset_keys(self):
        self.capturing = None
        self.settings["keys"] = copy.deepcopy(DEFAULT_KEYS)
        self.key_note.configure(text="Đã khôi phục phím mặc định", text_color=C["muted"])
        self._render_keys()

    # ================= Camera =================
    def _build_cameras(self, tab):
        tab.grid_columnconfigure((0, 1), weight=1, uniform="cam")
        self.cam_fields = {}
        gates = (("camera_vao", "●  CAMERA CỔNG VÀO", C["in_text"], C["in_soft"]),
                 ("camera_ra", "●  CAMERA CỔNG RA", C["out_text"], C["out_soft"]))
        for col, (section, title, color, soft) in enumerate(gates):
            box = card(tab)
            box.grid(row=0, column=col, sticky="nsew", padx=8, pady=(10, 0))
            pill(box, title, color, soft, size=12).pack(anchor="w", padx=18, pady=(16, 10))
            values = self.settings["cameras"][section]
            fields = {}
            for key, label, extra in (("ip", "Địa chỉ IP", {"placeholder_text": "VD: 192.168.1.100"}),
                                      ("tai_khoan", "Tài khoản", {}),
                                      ("mat_khau", "Mật khẩu (Safety Code trên tem camera)", {"show": "•"}),
                                      ("url", "Địa chỉ RTSP đầy đủ (nâng cao, có thể bỏ trống)", {})):
                ctk.CTkLabel(box, text=label, font=font(12, True), text_color=C["muted"], height=20).pack(
                    anchor="w", padx=18)
                e = entry(box, height=34, **extra)
                e.pack(fill="x", padx=18, pady=(2, 8))
                if values[key]:
                    e.insert(0, values[key])
                fields[key] = e
            ctk.CTkLabel(box, text="Chất lượng hình", font=font(12, True), text_color=C["muted"], height=20).pack(
                anchor="w", padx=18)
            stream = segmented(box, list(STREAMS.values()), height=32)
            stream.set(STREAMS.get(values["luong"], STREAMS["0"]))
            stream.pack(anchor="w", padx=18, pady=(2, 18))
            fields["luong"] = stream
            self.cam_fields[section] = fields
        ctk.CTkLabel(tab, text="Để trống IP và địa chỉ RTSP → chạy chế độ thử.   Nhập 0 vào ô RTSP → dùng webcam máy tính.\n"
                               "Camera sẽ được kết nối lại ngay khi bấm Lưu cài đặt.",
                     font=font(12), text_color=C["muted"], justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=10, pady=12)

    # ================= Giá gửi xe =================
    def _build_prices(self, tab):
        tab.grid_columnconfigure((0, 1), weight=1, uniform="price")
        self.price_fields = []
        styles = ((C["accent"], C["accent_soft"]), (C["brand_navy"], "#dbe4ee"))
        for col, frame in enumerate(self.settings["prices"]):
            color, soft = styles[col % len(styles)]
            box = card(tab)
            box.grid(row=0, column=col, sticky="nsew", padx=8, pady=(10, 0))
            box.grid_columnconfigure((0, 1), weight=1, uniform="f")
            pill(box, f"●  KHUNG GIỜ {col + 1}", color, soft, size=12).grid(
                row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 8))
            fields = {}
            for r, c, key, label, span in ((1, 0, "ten", "Tên khung", 2), (3, 0, "tu", "Từ giờ", 1),
                                           (3, 1, "den", "Đến giờ", 1), (5, 0, "gia", "Giá mỗi lượt (đồng)", 2)):
                ctk.CTkLabel(box, text=label, font=font(12, True), text_color=C["muted"], height=20).grid(
                    row=r, column=c, columnspan=span, sticky="w", padx=(18 if c == 0 else 6, 18))
                big = key == "gia"
                e = entry(box, height=40 if big else 34, font=font(18 if big else 14, big),
                          placeholder_text="VD: 06:00" if key in ("tu", "den") else "")
                e.grid(row=r + 1, column=c, columnspan=span, sticky="ew",
                       padx=(18 if c == 0 else 6, 18 if c + span == 2 else 6), pady=(2, 10))
                value = frame[key]
                e.insert(0, f"{value:,}".replace(",", ".") if key == "gia" else str(value))
                e.bind("<KeyRelease>", lambda _e: self._try_fee())
                fields[key] = e
            box.grid_rowconfigure(7, minsize=8)
            self.price_fields.append(fields)

        ctk.CTkLabel(tab, text="•  Xe gửi chạm khung giờ nào thì tính tiền khung đó.   Gửi qua nhiều khung hoặc qua "
                               "ngày hôm sau thì cộng dồn từng khung đã đi qua.\n"
                               "•  Giờ kết thúc nhỏ hơn giờ bắt đầu là khung qua đêm, VD 18:00 → 06:00.   "
                               "Giá 0 = khung miễn phí.",
                     font=font(12), text_color=C["muted"], justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(12, 10))

        calc = card(tab)
        calc.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8)
        ctk.CTkLabel(calc, text="Thử tính tiền", font=font(15, True), text_color=C["text"]).pack(
            anchor="w", padx=18, pady=(14, 6))
        row = ctk.CTkFrame(calc, fg_color="transparent")
        row.pack(fill="x", padx=18)
        now = datetime.now().replace(second=0, microsecond=0)
        self.calc_in = self._time_entry(row, "Giờ vào", now - timedelta(hours=3))
        self.calc_out = self._time_entry(row, "Giờ ra", now)
        primary_button(row, "Tính tiền", self._try_fee, width=110, height=36).pack(side="left", padx=(14, 0))
        result = ctk.CTkFrame(calc, fg_color="transparent")
        result.pack(fill="x", padx=18, pady=(10, 14))
        self.fee_total = ctk.CTkLabel(result, text="", font=font(24, True), text_color=C["accent"])
        self.fee_total.pack(side="left")
        self.fee_detail = ctk.CTkLabel(result, text="", font=font(13), text_color=C["text2"], justify="left")
        self.fee_detail.pack(side="left", padx=16)
        self._try_fee()

    def _time_entry(self, master, caption, value):
        ctk.CTkLabel(master, text=caption, font=font(13), text_color=C["muted"]).pack(side="left", padx=(0, 6))
        e = entry(master, width=170, height=36, justify="center", placeholder_text="dd/mm/yyyy HH:MM")
        e.insert(0, value.strftime("%d/%m/%Y %H:%M"))
        e.pack(side="left", padx=(0, 14))
        e.bind("<Return>", lambda _e: self._try_fee())
        return e

    def _read_prices(self):
        """Đọc 2 khung giờ trên form. Trả về (danh sách khung, lỗi)."""
        frames = []
        for i, fields in enumerate(self.price_fields, 1):
            name = fields["ten"].get().strip() or f"Khung {i}"
            try:
                start, end = parse_hm(fields["tu"].get()), parse_hm(fields["den"].get())
            except ValueError:
                return None, f"Khung {i}: giờ phải dạng HH:MM, VD 06:00"
            try:
                price = parse_money(fields["gia"].get())
            except ValueError:
                return None, f"Khung {i}: giá phải là số tiền, VD 5000"
            frames.append({"ten": name, "tu": start, "den": end, "gia": price})
        return frames, None

    @staticmethod
    def _parse_datetime(text):
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %Hh%M", "%d-%m-%Y %H:%M"):
            try:
                return datetime.strptime(" ".join(text.split()), fmt)
            except ValueError:
                pass
        raise ValueError(text)

    def _try_fee(self):
        """Tính thử theo bảng giá đang nhập trên form (chưa cần lưu)."""
        frames, error = self._read_prices()
        if error:
            self.fee_total.configure(text="")
            self.fee_detail.configure(text=error, text_color=C["danger"])
            return
        try:
            start, end = self._parse_datetime(self.calc_in.get()), self._parse_datetime(self.calc_out.get())
        except ValueError:
            self.fee_total.configure(text="")
            self.fee_detail.configure(text="Giờ vào / ra phải dạng dd/mm/yyyy HH:MM", text_color=C["danger"])
            return
        if end < start:
            self.fee_total.configure(text="")
            self.fee_detail.configure(text="Giờ ra phải sau giờ vào", text_color=C["danger"])
            return
        total, items = fee_detail(start, end, frames)
        self.fee_total.configure(text=money(total))
        self.fee_detail.configure(text=detail_text(items), text_color=C["text2"])

    # ================= Lưu trữ ảnh =================
    def _build_storage(self, tab):
        box = card(tab)
        box.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(box, text="Tự động xóa ảnh cũ", font=font(16, True), text_color=C["text"]).pack(
            anchor="w", padx=20, pady=(18, 6))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(anchor="w", padx=20, pady=(4, 8))
        ctk.CTkLabel(row, text="Xóa ảnh sau", font=font(14), text_color=C["text2"]).pack(side="left")
        self.keep_entry = entry(row, width=80, justify="center", font=font(15, True))
        self.keep_entry.insert(0, str(self.settings["keep_days"]))
        self.keep_entry.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="ngày kể từ ngày chụp", font=font(14), text_color=C["text2"]).pack(side="left")
        ctk.CTkLabel(box, text="•  Nhập 0 để không bao giờ tự xóa.\n"
                               "•  Ảnh lúc vào của xe còn đang gửi trong bãi luôn được giữ lại.\n"
                               "•  Thông tin lượt gửi (số thẻ, giờ vào, giờ ra) vẫn còn trong lịch sử, chỉ xóa file ảnh.\n"
                               "•  Chương trình tự dọn khi mở và mỗi giờ một lần.",
                     font=font(13), text_color=C["muted"], justify="left").pack(anchor="w", padx=20, pady=(4, 14))
        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 20))
        secondary_button(actions, "Dọn ảnh cũ ngay", self._cleanup_now, width=160, height=38).pack(side="left")
        secondary_button(actions, "Mở thư mục ảnh", lambda: open_file(self.image_dir), width=160,
                         height=38).pack(side="left", padx=8)
        self.cleanup_note = ctk.CTkLabel(actions, text="", font=font(13, True), text_color=C["in_text"])
        self.cleanup_note.pack(side="left", padx=10)

        danger = ctk.CTkFrame(tab, fg_color=C["danger_soft"], corner_radius=16, border_width=1, border_color="#fca5a5")
        danger.pack(fill="x", padx=10, pady=(14, 0))
        text = ctk.CTkFrame(danger, fg_color="transparent")
        text.pack(side="left", padx=20, pady=16)
        ctk.CTkLabel(text, text="Reset dữ liệu", font=font(16, True), text_color=C["danger"], height=24).pack(anchor="w")
        reset_keys = keys_text(self.settings["keys"]["reset"])
        ctk.CTkLabel(text, text=f"Xóa toàn bộ lượt gửi xe và ảnh, bắt đầu lại từ đầu.   Phím tắt: {reset_keys}",
                     font=font(12), text_color=C["text2"], height=20).pack(anchor="w")
        primary_button(danger, "Reset dữ liệu...", self._reset_data, color=C["danger"], hover=C["danger_hover"],
                       width=160, height=40).pack(side="right", padx=20)

    def _reset_data(self):
        """Đóng Cài đặt rồi mở hộp xác nhận reset của cửa sổ chính."""
        self.close()
        self.master.after(120, self.on_reset)

    def _read_keep_days(self):
        try:
            days = int(self.keep_entry.get().strip() or "0")
            if days < 0:
                raise ValueError
            return days
        except ValueError:
            self.tabs.set("Lưu trữ ảnh")
            self.footer_note.configure(text="Số ngày giữ ảnh phải là số nguyên ≥ 0", text_color=C["danger"])
            return None

    def _cleanup_now(self):
        days = self._read_keep_days()
        if days is None:
            return
        if days == 0:
            self.cleanup_note.configure(text="Đang đặt 0 ngày = không xóa ảnh", text_color=C["warn"])
            return
        removed = self.on_cleanup(days)
        self.cleanup_note.configure(text=f"Đã xóa {removed} ảnh cũ hơn {days} ngày", text_color=C["in_text"])

    # ================= Giao diện =================
    def _build_display(self, tab):
        box = card(tab)
        box.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(box, text="Cỡ chữ và nút bấm", font=font(16, True), text_color=C["text"]).pack(
            anchor="w", padx=20, pady=(18, 4))
        auto = int(auto_scale(self) * 100)
        ctk.CTkLabel(box, text=f"Màn hình máy này là {self.winfo_screenwidth()} × {self.winfo_screenheight()}, "
                               f"chế độ Tự động đang dùng cỡ {auto}%.",
                     font=font(13), text_color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 10))
        self.scale_buttons = {}
        for value, label in SCALE_CHOICES.items():
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            btn = ctk.CTkButton(row, text=label, height=42, corner_radius=10, font=font(14, True),
                                anchor="w", border_width=1,
                                command=lambda v=value: self._pick_scale(v))
            btn.pack(fill="x")
            self.scale_buttons[value] = btn
        ctk.CTkLabel(box, text="Màn hình càng lớn thì nên chọn cỡ càng to để đứng xa vẫn đọc được.",
                     font=font(13), text_color=C["muted"]).pack(anchor="w", padx=20, pady=(12, 18))
        self.scale_note = ctk.CTkLabel(tab, text="", font=font(13, True), text_color=C["warn"],
                                       fg_color=C["warn_soft"], corner_radius=8, height=34)
        self._render_scale()

    def _pick_scale(self, value):
        self.settings["scale"] = value
        self._render_scale()

    def _render_scale(self):
        for value, btn in self.scale_buttons.items():
            chosen = value == self.settings["scale"]
            btn.configure(fg_color=C["accent_soft"] if chosen else C["surface"],
                          hover_color=C["accent_soft"] if chosen else C["surface2"],
                          text_color=C["accent"] if chosen else C["text2"],
                          border_color=C["accent"] if chosen else C["border"],
                          text=("●   " if chosen else "○   ") + SCALE_CHOICES[value])
        if self.settings["scale"] == self._scale_at_open:
            self.scale_note.pack_forget()
        else:
            self.scale_note.configure(text="   Cỡ mới áp dụng sau khi lưu và mở lại chương trình   ")
            self.scale_note.pack(anchor="w", padx=10, pady=12)

    # ================= Mật khẩu =================
    def _change_password(self):
        dialog = ChangePasswordDialog(self, lambda pw: check_password(self.settings, pw), self._password_changed)
        self.wait_window(dialog)
        if self.winfo_exists():
            self.after(60, self._activate)  # lấy lại quyền điều khiển sau khi hộp đổi mật khẩu đóng

    def _password_changed(self, password):
        self.settings["pass_hash"] = hash_password(password)
        self.on_password(self.settings["pass_hash"])
        self.footer_note.configure(text="✓  Đã đổi mật khẩu", text_color=C["in_text"])

    # ================= Lưu / đóng =================
    def save(self):
        days = self._read_keep_days()
        if days is None:
            return
        prices, error = self._read_prices()
        if error:
            self.tabs.set("Giá gửi xe")
            self.footer_note.configure(text=error, text_color=C["danger"])
            return
        self.settings["keep_days"] = days
        self.settings["prices"] = prices
        for section, fields in self.cam_fields.items():
            cam = self.settings["cameras"][section]
            for key in ("ip", "tai_khoan", "mat_khau", "url"):
                cam[key] = fields[key].get().strip()
            cam["tai_khoan"] = cam["tai_khoan"] or "admin"
            cam["luong"] = "1" if fields["luong"].get() == STREAMS["1"] else "0"
        self.on_save(self.settings)
        self.close()

    def close(self):
        master = self.master
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        master.after(50, master.focus_force)
