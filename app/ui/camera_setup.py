"""Cửa sổ tự tìm camera trong mạng và gán vào cổng vào / cổng ra."""

import threading

import customtkinter as ctk

from ..core.discover import scan, subnet, test_login
from .modal import ModalDialog
from .theme import C, font, pill, primary_button, secondary_button, entry

GATES = {"camera_vao": "Cổng vào", "camera_ra": "Cổng ra"}
NONE_TEXT = "Không dùng"
MAX_ROWS = 6


class CameraSetupDialog(ModalDialog):
    """
    cameras : cài đặt camera hiện tại (để điền sẵn Safety Code đã nhập trước đó)
    on_save : hàm nhận cài đặt camera mới (dạng {"camera_vao": {...}, "camera_ra": {...}})
    """

    def __init__(self, master, cameras, on_save):
        super().__init__(master, "Tự tìm camera")
        self.cameras = cameras
        self.on_save = on_save
        self.rows = []
        self.busy = False

        header = ctk.CTkFrame(self, fg_color=C["brand_navy"], corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="⌕", width=56, height=56, corner_radius=16, fg_color=C["accent"],
                     text_color="white", font=font(30, True)).pack(side="left", padx=(24, 14), pady=18)
        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left", pady=18, padx=(0, 24))
        ctk.CTkLabel(titles, text="TỰ TÌM CAMERA", font=font(22, True), text_color="white",
                     height=30).pack(anchor="w")
        ctk.CTkLabel(titles, text="Tìm camera trong mạng rồi gán vào cổng vào / cổng ra",
                     font=font(13), text_color="#cbd5e1", height=20).pack(anchor="w")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", padx=26, pady=(20, 10))

        self.status = ctk.CTkLabel(self, text="", font=font(13, True), text_color=C["text2"],
                                   fg_color="transparent", corner_radius=8, height=32)
        self.status.pack(fill="x", padx=26)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=26, pady=(8, 24))
        self.btn_skip = secondary_button(buttons, "Để sau   (Esc)", self.close, height=48, width=150,
                                         font=font(14, True))
        self.btn_skip.pack(side="left")
        self.btn_save = primary_button(buttons, "Kiểm tra và lưu", self.submit, height=48, font=font(14, True))
        self.btn_save.pack(side="right", expand=True, fill="x", padx=(10, 0))
        self.btn_rescan = secondary_button(buttons, "Quét lại", self.start_scan, height=48, width=120,
                                           font=font(14, True))
        self.btn_rescan.pack(side="right", padx=(10, 0))

        self.present()
        self.start_scan()

    # ---------------- quét mạng ----------------
    def start_scan(self):
        if self.busy:
            return
        self._set_busy(True)
        for child in self.body.winfo_children():
            child.destroy()
        self.rows = []
        dai = subnet()
        self.progress = ctk.CTkProgressBar(self.body, height=12, corner_radius=6,
                                           progress_color=C["accent"], fg_color=C["surface2"])
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(30, 14))
        self.scan_label = ctk.CTkLabel(self.body, text=f"Đang quét {dai}.1 → {dai}.254 ..." if dai
                                       else "Máy chưa nối mạng", font=font(14), text_color=C["text2"])
        self.scan_label.pack(pady=(0, 30))
        self.set_status("", "")
        if dai is None:
            self._done([])
            return
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        found = scan(progress=lambda done, total: self.after(0, self._tick, done, total))
        self.after(0, self._done, found)

    def _tick(self, done, total):
        if self.winfo_exists():
            self.progress.set(done / total)
            self.scan_label.configure(text=f"Đang quét... {done}/{total} địa chỉ")

    def _done(self, found):
        if not self.winfo_exists():
            return
        self._set_busy(False)
        for child in self.body.winfo_children():
            child.destroy()
        if not found:
            self._show_empty()
            return
        ctk.CTkLabel(self.body, text=f"Tìm thấy {len(found)} camera. Nhập Safety Code in trên tem thân camera:",
                     font=font(14, True), text_color=C["text"]).pack(anchor="w", pady=(0, 10))
        for i, cam in enumerate(found[:MAX_ROWS]):
            gate = list(GATES)[i] if i < len(GATES) else None
            self.rows.append(_CameraRow(self.body, cam, gate, self._gate_picked, self._code_for(cam["ip"])))
        if len(found) > MAX_ROWS:
            ctk.CTkLabel(self.body, text=f"(còn {len(found) - MAX_ROWS} thiết bị nữa không hiện ở đây)",
                         font=font(12), text_color=C["muted"]).pack(anchor="w", pady=(6, 0))
        self.set_status("Camera nào không phải của bãi xe thì để “Không dùng”.", "info")

    def _code_for(self, ip):
        """Nếu IP này đã từng được cấu hình thì điền sẵn Safety Code cũ."""
        for cam in self.cameras.values():
            if cam.get("ip", "").strip() == ip:
                return cam.get("mat_khau", "")
        return ""

    def _show_empty(self):
        box = ctk.CTkFrame(self.body, fg_color=C["warn_soft"], corner_radius=12)
        box.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(box, text="Không tìm thấy camera nào trong mạng", font=font(15, True),
                     text_color=C["warn"]).pack(anchor="w", padx=18, pady=(14, 6))
        ctk.CTkLabel(box, text="•  Camera đã cắm điện và đèn báo đã sáng chưa?\n"
                               "•  Camera có nối cùng mạng Wi-Fi với máy này không?\n"
                               "•  Mở app Imou Life → chọn camera → ⚙ Cài đặt → bật RTSP\n"
                               "•  Camera ở mạng khác thì phải nhập IP bằng tay trong Cài đặt → Camera",
                     font=font(13), text_color=C["text2"], justify="left").pack(anchor="w", padx=18, pady=(0, 16))

    # ---------------- gán cổng ----------------
    def _gate_picked(self, row, gate):
        """Mỗi cổng chỉ gán được 1 camera, nên gỡ camera khác đang giữ cổng đó."""
        if gate is None:
            return
        for other in self.rows:
            if other is not row and other.gate == gate:
                other.set_gate(None)

    # ---------------- lưu ----------------
    def submit(self):
        if self.busy:
            return
        chosen = {row.gate: row for row in self.rows if row.gate}
        if not chosen:
            return self.set_status("Chưa chọn camera nào cho cổng vào hoặc cổng ra", "error")
        for gate, row in chosen.items():
            if not row.code():
                row.focus_code()
                return self.set_status(f"Chưa nhập Safety Code cho camera {GATES[gate]}", "error")
        self._set_busy(True)
        self.set_status("Đang kết nối thử tới camera, đợi một chút...", "info")
        threading.Thread(target=self._test_thread, args=(chosen,), daemon=True).start()

    def _test_thread(self, chosen):
        results = {}
        for gate, row in chosen.items():
            self.after(0, row.mark, "Đang kiểm tra...", C["muted"])
            ok, message = test_login(row.ip, row.code())
            results[gate] = (ok, message)
            self.after(0, row.mark, message, C["in_text"] if ok else C["danger"])
        self.after(0, self._tested, chosen, results)

    def _tested(self, chosen, results):
        if not self.winfo_exists():
            return
        self._set_busy(False)
        hong = [GATES[g] for g, (ok, _) in results.items() if not ok]
        if hong:
            return self.set_status(f"Chưa kết nối được camera {', '.join(hong)} — xem chi tiết ở từng dòng", "error")
        cameras = {section: dict(cam) for section, cam in self.cameras.items()}
        for gate, row in chosen.items():  # cổng không được gán thì giữ nguyên cài đặt cũ
            cameras[gate].update(ip=row.ip, tai_khoan="admin", mat_khau=row.code(), url="")
        self.close()
        self.on_save(cameras)

    def set_status(self, text, level):
        colors = {"info": (C["text2"], "transparent"), "error": (C["danger"], C["danger_soft"]),
                  "ok": (C["in_text"], C["in_soft"]), "": (C["text2"], "transparent")}
        color, back = colors[level]
        self.status.configure(text=f"  {text}  " if text else "", text_color=color, fg_color=back)

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for btn in (self.btn_save, self.btn_rescan):
            btn.configure(state=state)


class _CameraRow(ctk.CTkFrame):
    """Một camera tìm được: IP, chọn cổng, ô nhập Safety Code."""

    def __init__(self, master, cam, gate, on_gate, code=""):
        super().__init__(master, fg_color=C["surface2"], corner_radius=12)
        self.pack(fill="x", pady=4)
        self.ip = cam["ip"]
        self.gate = gate
        self.on_gate = on_gate

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(16, 10), pady=12)
        ctk.CTkLabel(left, text=self.ip, font=font(17, True), text_color=C["text"], height=24).pack(anchor="w")
        note = "Imou / Dahua" if cam["imou"] else "chưa rõ hãng"
        ctk.CTkLabel(left, text=f"{cam['mac'] or 'không đọc được MAC'}  ·  {note}", font=font(11),
                     text_color=C["muted"], height=16).pack(anchor="w")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=(10, 16), pady=12)
        self.entry = entry(right, width=150, height=36, show="•", placeholder_text="Safety Code")
        if code:
            self.entry.insert(0, code)
        self.entry.pack(side="right")
        ctk.CTkLabel(right, text="Mã:", font=font(12), text_color=C["muted"]).pack(side="right", padx=(0, 6))

        self.buttons = {}
        middle = ctk.CTkFrame(self, fg_color="transparent")
        middle.pack(side="left", pady=12)
        for value, label in (*GATES.items(), (None, NONE_TEXT)):
            btn = ctk.CTkButton(middle, text=label, width=96, height=32, corner_radius=8,
                                font=font(12, True), border_width=1,
                                command=lambda v=value: self.set_gate(v, tell=True))
            btn.pack(side="left", padx=3)
            self.buttons[value] = btn

        self.note = ctk.CTkLabel(self, text="", font=font(12, True), text_color=C["muted"])
        self._render()

    def set_gate(self, gate, tell=False):
        self.gate = gate
        self._render()
        if tell:
            self.on_gate(self, gate)

    def _render(self):
        for value, btn in self.buttons.items():
            chosen = value == self.gate
            btn.configure(fg_color=C["accent"] if chosen else C["surface"],
                          hover_color=C["accent_hover"] if chosen else C["hover"],
                          text_color="white" if chosen else C["text2"],
                          border_color=C["accent"] if chosen else C["border"])
        self.entry.configure(state="normal" if self.gate else "disabled")

    def code(self):
        return self.entry.get().strip()

    def focus_code(self):
        self.entry.focus_set()

    def mark(self, text, color):
        self.note.configure(text=f"   {text}", text_color=color)
        self.note.pack(side="left", padx=(10, 0))
