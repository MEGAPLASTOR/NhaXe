"""
Phần mềm quản lý nhà xe - 2 camera (cổng VÀO / cổng RA).

Xe vào : nhấn phím xe vào (mặc định Shift TRÁI) -> chụp ảnh camera vào, hiện ô nhập số thẻ -> Enter.
Xe ra  : nhấn phím xe ra (mặc định Enter / Shift phải) -> chụp ảnh camera ra, hiện ô nhập số thẻ -> Enter.
Xe đang gửi (F3), Lịch sử (F4). Đổi phím, camera, giá gửi xe, thời gian lưu ảnh trong nút Cài đặt (có mật khẩu).
Cài đặt lưu trong config.ini, dữ liệu và ảnh lưu trong thư mục data.
"""

import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from .. import APP_NAME, COMPANY, VERSION
from ..core.camera import CONNECTED, CameraStream, camera_source
from ..core.errors import log_error
from ..core.keys import ACTIONS, COMBO_MODIFIERS, event_key, keys_text
from ..core.pricing import calc_fee, money
from ..core.settings import check_password, load_settings, save_settings
from ..core.storage import Storage, parse_time, record_duration, short_time, vn_time
from ..paths import CONFIG_FILE, DATA_DIR
from .card_dialog import CardDialog
from .password_dialog import PasswordDialog
from .records_window import RecordsWindow, RecordView
from .reset_dialog import ResetDialog
from .settings_window import SettingsWindow
from .theme import (C, WEEKDAYS, ImageBox, apply_ui_scale, bgr_to_pil, brand_icon, card, font, keycap,
                    logo_image, make_tree, pill, primary_button, scale_applied, secondary_button,
                    style_treeview, ui_scale, zebra)

KEY_COOLDOWN = 0.6             # giây, chống lặp khi giữ phím
CLEANUP_INTERVAL = 3600 * 1000  # dọn ảnh cũ mỗi giờ (mili giây)

STATUS_STYLE = {  # mức thông báo -> (màu chữ, màu nền)
    "info": (C["text2"], C["surface2"]),
    "ok": (C["in_text"], C["in_soft"]),
    "in": (C["in_text"], C["in_soft"]),
    "out": (C["out_text"], C["out_soft"]),
    "warn": (C["warn"], C["warn_soft"]),
    "error": (C["danger"], C["danger_soft"]),
}


class CameraCard(ctk.CTkFrame):
    """Khung camera trực tiếp của 1 cổng, kèm nút ghi nhận."""

    def __init__(self, master, title, color, soft, hover, action, command):
        super().__init__(master, fg_color=C["surface"], corner_radius=16, border_width=1, border_color=C["border"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 10))
        pill(top, f"●  {title}", color, soft, size=13).pack(side="left")
        self.state_label = ctk.CTkLabel(top, text="", font=font(12, True), text_color=C["muted"])
        self.state_label.pack(side="right")

        self.screen = ImageBox(self, placeholder="Đang kết nối camera...", dark=True)
        self.screen.grid(row=1, column=0, sticky="nsew", padx=16)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(12, 14))
        ctk.CTkLabel(bottom, text="Nhấn", font=font(13), text_color=C["muted"]).pack(side="left")
        self.key_cap = keycap(bottom, "")
        self.key_cap.pack(side="left", padx=8)
        ctk.CTkLabel(bottom, text=f"để {action.lower()}", font=font(13), text_color=C["muted"]).pack(side="left")
        primary_button(bottom, action, command, color=color, hover=hover, width=170, height=38).pack(side="right")
        self._last_state = None

    def set_keys(self, keys):
        self.key_cap.label.configure(text=keys_text(keys))

    def update_view(self, cam):
        frame = cam.latest()
        if frame is not None:
            self.screen.show_frame(frame, live=cam.configured)
            state = (f"●  {cam.state}", C["in_text"] if cam.configured else C["warn"])
        else:
            text = cam.state if cam.state != CONNECTED else "Không nhận được hình mới..."
            self.screen.show(None, f"MẤT TÍN HIỆU\n{text}")
            state = (f"●  {text}", C["danger"])
        if state != self._last_state:
            self.state_label.configure(text=state[0], text_color=state[1])
            self._last_state = state


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=C["bg"])
        self.settings = load_settings(CONFIG_FILE)
        if not scale_applied():  # main() đã đặt sẵn; nhánh này cho lúc chạy thử
            apply_ui_scale(self, self.settings["scale"])
        self.title(f"{APP_NAME} — {COMPANY}  v{VERSION}")
        brand_icon(self)
        self.report_callback_exception = self._on_error
        self._size_window()
        style_treeview(self)

        self.storage = Storage(DATA_DIR)
        self._start_cameras()

        self.dialog = None      # cửa sổ nhập số thẻ đang mở
        self.records = None     # cửa sổ tra cứu
        self.settings_win = None
        self.key_map = {}       # phím -> chức năng
        self._last_key = None
        self._last_key_time = 0.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_body()
        self._build_footer()
        self._pending_mod = None  # Ctrl / Alt đang giữ, chưa biết có bấm kèm phím khác không
        self.bind("<KeyPress>", self._on_key)
        self.bind("<KeyRelease>", self._on_key_release)
        self._apply_keys()

        self.refresh_data()
        self.set_status("Sẵn sàng làm việc", "ok")
        self._tick_clock()
        self._tick_cameras()
        self.after(3000, self._auto_cleanup)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ================= Giao diện =================
    def _size_window(self):
        """Mở to hết màn hình. Cỡ nhỏ nhất không được vượt quá màn hình, nếu không cửa sổ sẽ lòi ra ngoài."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        scale = ui_scale(self)
        # geometry / minsize của CustomTkinter tự nhân hệ số, nên ở đây truyền cỡ chưa nhân
        self.minsize(min(1100, int((sw - 40) / scale)), min(680, int((sh - 120) / scale)))
        self.geometry(f"{int(sw * 0.88 / scale)}x{int(sh * 0.84 / scale)}")
        self.after(60, self._maximize)

    def _maximize(self, tries=25):
        """state('zoomed') có lúc chưa ăn vì cửa sổ chưa hiện xong, nên thử lại vài lần."""
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        if tries and self.winfo_width() < self.winfo_screenwidth() * 0.9:
            self.after(120, lambda: self._maximize(tries - 1))

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0, border_width=0)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(bar, fg_color=C["border"], height=1, corner_radius=0).grid(
            row=1, column=0, columnspan=3, sticky="ew")

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=22, pady=12, sticky="w")
        logo = logo_image(52)
        if logo is not None:
            ctk.CTkLabel(brand, text="", image=logo).pack(side="left")
        else:
            ctk.CTkLabel(brand, text="V", width=52, height=52, corner_radius=14, fg_color=C["accent"],
                         text_color="white", font=font(26, True)).pack(side="left")
        ctk.CTkFrame(brand, fg_color=C["border"], width=1, height=40).pack(side="left", padx=14)
        names = ctk.CTkFrame(brand, fg_color="transparent")
        names.pack(side="left")
        ctk.CTkLabel(names, text=COMPANY, font=font(11, True), text_color=C["brand_teal"], height=16).pack(anchor="w")
        ctk.CTkLabel(names, text=APP_NAME, font=font(21, True), text_color=C["brand_navy"], height=28).pack(anchor="w")
        ctk.CTkLabel(names, text="Hệ thống ghi nhận xe vào / ra bằng camera", font=font(11),
                     text_color=C["muted"], height=16).pack(anchor="w")

        stats = ctk.CTkFrame(bar, fg_color="transparent")
        stats.grid(row=0, column=1)
        self.stat_labels = {}
        for key, title, color, soft in (("parked", "ĐANG GỬI", C["accent"], C["accent_soft"]),
                                        ("in", "VÀO HÔM NAY", C["in_text"], C["in_soft"]),
                                        ("out", "RA HÔM NAY", C["out_text"], C["out_soft"])):
            chip = ctk.CTkFrame(stats, fg_color=soft, corner_radius=14)
            chip.pack(side="left", padx=6)
            ctk.CTkLabel(chip, text=title, font=font(10, True), text_color=color, height=16).pack(
                anchor="w", padx=18, pady=(8, 0))
            value = ctk.CTkLabel(chip, text="0", font=font(24, True), text_color=color, height=30)
            value.pack(anchor="w", padx=18, pady=(0, 8))
            self.stat_labels[key] = value

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=2, padx=22, sticky="e")
        self.btn_parked = secondary_button(right, "", lambda: self.open_records(0), width=160)
        self.btn_parked.pack(side="left", padx=4)
        self.btn_history = secondary_button(right, "", lambda: self.open_records(1), width=140)
        self.btn_history.pack(side="left", padx=4)
        secondary_button(right, "⚙  Cài đặt", self.open_settings, width=120).pack(side="left", padx=4)
        clock = ctk.CTkFrame(right, fg_color="transparent")
        clock.pack(side="left", padx=(20, 0))
        self.clock_time = ctk.CTkLabel(clock, text="", font=font(24, True), text_color=C["text"], height=30)
        self.clock_time.pack(anchor="e")
        self.clock_date = ctk.CTkLabel(clock, text="", font=font(12), text_color=C["muted"], height=18)
        self.clock_date.pack(anchor="e")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=14)
        body.grid_columnconfigure((0, 1), weight=1, uniform="cam")
        body.grid_rowconfigure(0, weight=1)  # camera chiếm phần lớn màn hình
        body.grid_rowconfigure(1, weight=0)

        self.view_in = CameraCard(body, "CỔNG VÀO", C["in"], C["in_soft"], C["in_hover"],
                                  "Ghi nhận xe vào", self.start_entry)
        self.view_in.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.view_out = CameraCard(body, "CỔNG RA", C["out"], C["out_soft"], C["out_hover"],
                                   "Ghi nhận xe ra", self.start_exit)
        self.view_out.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        bottom = ctk.CTkFrame(body, fg_color="transparent")
        bottom.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        self.last_view = RecordView(bottom, self.storage, "Lượt vừa ghi nhận", on_undo=self.undo_exit,
                                    fee_of=self.fee_of)
        self.last_view.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        recent = card(bottom)
        recent.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        head = ctk.CTkFrame(recent, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(head, text="Hoạt động gần đây", font=font(15, True), text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(head, text="bấm để xem lại", font=font(11), text_color=C["muted"]).pack(side="right")
        holder, self.recent_tree = make_tree(recent, [
            ("gio", "Thời gian", 100, "center"),
            ("the", "Số thẻ", 80, "center"),
            ("loai", "Loại", 70, "center"),
        ], rows=6)
        holder.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.recent_tree.bind("<<TreeviewSelect>>", self._on_recent_select)

    def _build_footer(self):
        bar = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        ctk.CTkFrame(bar, fg_color=C["border"], height=1, corner_radius=0).pack(fill="x", side="top")
        self.key_hints = ctk.CTkFrame(bar, fg_color="transparent")
        self.key_hints.pack(side="left", padx=18, pady=8)
        ctk.CTkLabel(bar, text=f"© {COMPANY}  ·  v{VERSION}", font=font(11), text_color="#94a3b8").pack(
            side="right", padx=(0, 18))
        self.status_label = ctk.CTkLabel(bar, text="", font=font(13, True), corner_radius=10, height=30)
        self.status_label.pack(side="right", padx=12, pady=6)

    # ================= Phím tắt =================
    def _apply_keys(self):
        """Cập nhật bảng phím -> chức năng và các nhãn phím trên màn hình theo cài đặt."""
        keys = self.settings["keys"]
        self.key_map = {key: action for action, action_keys in keys.items() for key in action_keys}
        self.view_in.set_keys(keys["in"])
        self.view_out.set_keys(keys["out"])
        self.btn_parked.configure(text=f"Xe đang gửi   ({keys_text(keys['parked'])})")
        self.btn_history.configure(text=f"Lịch sử   ({keys_text(keys['history'])})")
        for child in self.key_hints.winfo_children():
            child.destroy()
        for action, title in ACTIONS:
            if keys[action] and action != "reset":  # không quảng cáo phím xóa dữ liệu ở thanh dưới
                keycap(self.key_hints, keys_text(keys[action])).pack(side="left")
                ctk.CTkLabel(self.key_hints, text=title, font=font(12), text_color=C["muted"]).pack(
                    side="left", padx=(6, 20))
        keycap(self.key_hints, "Esc").pack(side="left")
        ctk.CTkLabel(self.key_hints, text="Hủy / đóng", font=font(12), text_color=C["muted"]).pack(side="left", padx=6)

    def _on_key(self, event):
        key = event_key(event)
        if key in COMBO_MODIFIERS:
            # Ctrl / Alt có thể là đầu của tổ hợp (Ctrl + Delete): chỉ tính là phím riêng khi thả ra
            self._pending_mod = key
            return None
        self._pending_mod = None
        return self._run_key(key)

    def _on_key_release(self, event):
        if self._pending_mod is not None and event.keysym == self._pending_mod:
            key, self._pending_mod = self._pending_mod, None
            self._run_key(key)

    def _run_key(self, key):
        action = self.key_map.get(key)
        if action is None:
            return None
        now = time.monotonic()
        repeated = action == self._last_key and now - self._last_key_time < KEY_COOLDOWN
        self._last_key, self._last_key_time = action, now  # giữ phím thì không chạy lại liên tục
        if repeated:
            return "break"
        if action == "in":
            self.start_entry()
        elif action == "out":
            self.start_exit()
        elif action == "parked":
            self.open_records(0)
        elif action == "history":
            self.open_records(1)
        elif action == "reset":
            self.open_reset()
        return "break"

    def _busy(self):
        return any(w is not None and w.winfo_exists() for w in (self.dialog, self.settings_win))

    # ================= Nghiệp vụ =================
    def start_entry(self):
        if self._busy():
            return
        frame, when = self._snapshot(self.cam_in, "vào")
        photo = bgr_to_pil(frame) if frame is not None else None
        self.dialog = CardDialog(self, "IN", photo, when, lambda card_no: self._commit_in(card_no, frame, when))

    def start_exit(self):
        if self._busy():
            return
        frame, when = self._snapshot(self.cam_out, "ra")
        photo = bgr_to_pil(frame) if frame is not None else None
        self.dialog = CardDialog(self, "OUT", photo, when, lambda card_no: self._commit_out(card_no, frame, when),
                                 preview=lambda card_no: self._exit_preview(card_no, when))

    def _snapshot(self, cam, gate):
        """Chụp ảnh ngay lúc bấm phím."""
        when = datetime.now()
        frame = cam.latest()
        if frame is None:
            self.set_status(f"Camera {gate} mất tín hiệu — lượt này sẽ không có ảnh", "warn")
            return None, when
        return frame.copy(), when

    def _commit_in(self, card_no, frame, when):
        rec = self.storage.parked(card_no)
        if rec is not None:
            return f"Thẻ {card_no} đang có xe trong bãi (vào lúc {vn_time(rec['gio_vao'])})"
        image = self.storage.save_photo(frame, card_no, when, "IN") if frame is not None else ""
        rid = self.storage.add_in(card_no, when, image)
        self.last_view.undo_id = None
        self.last_view.show(rid, "Lượt vừa ghi nhận")
        self.refresh_data()
        self.set_status(f"XE VÀO  ·  thẻ {card_no}  ·  {when:%H:%M:%S}", "in")
        return None

    def fee_of(self, rec):
        """Tiền gửi của 1 lượt -> (số tiền, tạm tính hay không). Xe đang gửi thì tạm tính đến hiện tại."""
        if rec["gio_ra"] is not None and rec["tien"] is not None:
            return rec["tien"], False  # đã chốt lúc xe ra, đổi bảng giá sau này không ảnh hưởng
        end = parse_time(rec["gio_ra"]) or datetime.now()
        return calc_fee(parse_time(rec["gio_vao"]), end, self.settings["prices"]), rec["gio_ra"] is None

    def _exit_preview(self, card_no, when):
        """Thông tin hiện ngay khi đang gõ số thẻ ở cửa sổ xe ra."""
        rec = self.storage.parked(card_no) if card_no else None
        if rec is None:
            return None
        fee = calc_fee(parse_time(rec["gio_vao"]), when, self.settings["prices"])
        return f"Vào lúc {vn_time(rec['gio_vao'])}   ·   Tiền gửi: {money(fee)}"

    def _commit_out(self, card_no, frame, when):
        rec = self.storage.parked(card_no)
        if rec is None:
            return f"Thẻ {card_no} không có xe nào đang gửi!"
        fee = calc_fee(parse_time(rec["gio_vao"]), when, self.settings["prices"])
        image = self.storage.save_photo(frame, card_no, when, "OUT") if frame is not None else ""
        self.storage.set_out(rec["id"], when, image, fee)
        self.last_view.undo_id = rec["id"]
        self.last_view.show(rec["id"], "Lượt vừa ghi nhận")
        self.refresh_data()
        self.set_status(f"XE RA  ·  thẻ {card_no}  ·  đã gửi {record_duration(self.storage.get(rec['id']))}"
                        f"  ·  THU {money(fee)}", "out")
        return None

    def undo_exit(self, rid):
        rec = self.storage.get(rid)
        if rec is None or rec["gio_ra"] is None:
            return
        card_no = rec["so_the"]
        if self.storage.parked(card_no) is not None:
            self.set_status(f"Không hoàn tác được: thẻ {card_no} đang có xe khác gửi", "error")
            return
        if not messagebox.askyesno("Hoàn tác lượt ra",
                                   f"Hoàn tác lượt ra của thẻ {card_no}?\nXe sẽ được tính là vẫn đang gửi trong bãi.",
                                   parent=self):
            return
        self.storage.undo_out(rid)
        self.last_view.undo_id = None
        self.last_view.show(rid)
        self.refresh_data()
        self.set_status(f"Đã hoàn tác lượt ra của thẻ {card_no}", "warn")

    def open_records(self, tab):
        if self._busy():
            return
        if self.records is not None and self.records.winfo_exists():
            self.records.refresh()
            self.records.show_tab(tab)
            self.records.lift()
            self.records.focus_force()
        else:
            self.records = RecordsWindow(self, self.storage, tab, self.fee_of)

    # ================= Cài đặt =================
    def _ask_password(self, purpose, on_success):
        self.dialog = PasswordDialog(self, lambda pw: check_password(self.settings, pw), on_success, purpose)

    def open_settings(self):
        if self._busy():
            return
        self._ask_password("mở Cài đặt", self._show_settings)

    def _show_settings(self):
        if self._busy():
            return
        self.settings_win = SettingsWindow(self, self.settings, self.apply_settings, self.cleanup_photos,
                                           self.storage.image_dir, lambda: self.open_reset(authorized=True),
                                           self.change_password)

    def change_password(self, pass_hash):
        self.settings["pass_hash"] = pass_hash
        save_settings(CONFIG_FILE, self.settings)
        self.set_status("Đã đổi mật khẩu Cài đặt", "ok")

    # ================= Reset dữ liệu =================
    def open_reset(self, authorized=False):
        """Phím tắt reset phải nhập mật khẩu; mở từ trong Cài đặt thì đã nhập rồi."""
        if self._busy():
            return
        if not authorized:
            self._ask_password("reset dữ liệu", lambda: self.open_reset(authorized=True))
            return
        if self.records is not None and self.records.winfo_exists():
            self.records.destroy()
        self.dialog = ResetDialog(self, self.storage.summary(), self.do_reset)

    def do_reset(self, backup):
        try:
            dest = self.storage.reset(backup)
        except OSError as exc:
            # vd. đang mở ảnh / thư mục ảnh bằng chương trình khác nên không chuyển được
            self.storage._open()
            self.set_status(f"Không reset được: {exc}", "error")
            return
        self.last_view.undo_id = None
        self.last_view.clear()
        self.refresh_data()
        if dest is not None:
            self.set_status(f"Đã reset dữ liệu — bản sao lưu: data/sao_luu/{dest.name}", "warn")
        else:
            self.set_status("Đã reset dữ liệu (không giữ bản sao lưu)", "warn")

    def apply_settings(self, new):
        old = self.settings
        save_settings(CONFIG_FILE, new)
        self.settings = new
        self._apply_keys()
        if new["cameras"] != old["cameras"]:
            self.cam_in.stop()
            self.cam_out.stop()
            self._start_cameras()
            self.view_in._last_state = self.view_out._last_state = None
        if new["keep_days"] != old["keep_days"]:
            self.cleanup_photos()
        if new["prices"] != old["prices"]:
            self.refresh_data()  # tiền tạm tính của xe đang gửi theo bảng giá mới
            self.last_view.refresh()
        if new["scale"] != old["scale"]:
            self.set_status("Đã lưu cài đặt — mở lại chương trình để áp dụng cỡ giao diện mới", "warn")
            return
        self.set_status("Đã lưu cài đặt", "ok")

    def _start_cameras(self):
        cams = self.settings["cameras"]
        self.cam_in = CameraStream("CAMERA VAO", camera_source(cams["camera_vao"]))
        self.cam_out = CameraStream("CAMERA RA", camera_source(cams["camera_ra"]))

    def cleanup_photos(self, keep_days=None):
        """Xóa ảnh đã lưu quá số ngày cài đặt (mặc định 30 ngày). Trả về số ảnh đã xóa."""
        days = self.settings["keep_days"] if keep_days is None else keep_days
        removed = self.storage.cleanup_photos(days)
        if removed:
            self.set_status(f"Đã tự xóa {removed} ảnh lưu quá {days} ngày", "info")
            self.last_view.refresh()
        return removed

    def _auto_cleanup(self):
        self.cleanup_photos()
        self.after(CLEANUP_INTERVAL, self._auto_cleanup)

    # ================= Cập nhật hiển thị =================
    def refresh_stats(self):
        for key, value in self.storage.stats().items():
            self.stat_labels[key].configure(text=str(value))

    def refresh_data(self):
        self.refresh_stats()
        tree = self.recent_tree
        tree.delete(*tree.get_children())
        for i, r in enumerate(self.storage.recent_events()):
            is_in = r["loai"] == "IN"
            tree.insert("", "end", iid=f"{r['loai']}-{r['id']}", tags=(r["loai"], *zebra(i)),
                        values=(short_time(r["thoi_gian"]), r["so_the"], "↓  VÀO" if is_in else "↑  RA"))
        if self.records is not None and self.records.winfo_exists():
            self.records.refresh()

    def _on_recent_select(self, _event):
        selected = self.recent_tree.selection()
        if selected:
            self.last_view.show(int(selected[0].split("-")[1]), "Xem lại lượt gửi")
        self.focus_set()  # trả phím tắt về cửa sổ chính

    def set_status(self, text, level="info"):
        color, soft = STATUS_STYLE[level]
        self.status_label.configure(text=f"   {datetime.now():%H:%M:%S}   ·   {text}   ", text_color=color, fg_color=soft)

    def _tick_clock(self):
        now = datetime.now()
        self.clock_time.configure(text=now.strftime("%H:%M:%S"))
        self.clock_date.configure(text=f"{WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y}")
        if now.second == 0:
            self.refresh_stats()  # cập nhật số liệu "hôm nay" khi qua ngày mới
        self.after(1000, self._tick_clock)

    def _tick_cameras(self):
        self.view_in.update_view(self.cam_in)
        self.view_out.update_view(self.cam_out)
        self.after(40, self._tick_cameras)

    def _on_error(self, exc_type, exc, tb):
        log_error(exc_type, exc, tb)
        try:
            self.set_status("Có lỗi xảy ra — chi tiết trong data/loi.log", "error")
        except Exception:
            pass

    def on_close(self):
        self.cam_in.stop()
        self.cam_out.stop()
        self.destroy()


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    # đo màn hình và đặt cỡ giao diện trên một cửa sổ tạm, trước khi dựng cửa sổ chính
    probe = tk.Tk()
    probe.withdraw()
    try:
        apply_ui_scale(probe, load_settings(CONFIG_FILE)["scale"])
    finally:
        probe.destroy()
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
