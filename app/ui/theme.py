"""Màu sắc, phông chữ và các thành phần giao diện dùng chung (giao diện sáng)."""

import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from ..paths import ICON_FILE, LOGO_MARK_FILE

FONT = "Segoe UI"

C = {
    "bg": "#eef2f7",          # nền cửa sổ
    "surface": "#ffffff",     # nền thẻ (card)
    "surface2": "#f4f6fa",    # nền ô nhập, nút phụ
    "hover": "#e6ebf2",
    "border": "#e2e8f0",
    "text": "#0f172a",
    "text2": "#334155",
    "muted": "#64748b",
    "screen": "#0f172a",      # nền khung camera
    "photo_bg": "#f1f5f9",    # nền khung ảnh
    "accent": "#256fa6",       # xanh logo VIDATEX
    "accent_hover": "#1c5785",
    "accent_soft": "#e2eef8",
    "brand_navy": "#0d2f54",
    "brand_teal": "#1f9fb3",
    "in": "#16a34a",
    "in_hover": "#15803d",
    "in_text": "#15803d",
    "in_soft": "#dcfce7",
    "out": "#ea580c",
    "out_hover": "#c2410c",
    "out_text": "#c2410c",
    "out_soft": "#ffedd5",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "danger_soft": "#fee2e2",
    "warn": "#b45309",
    "warn_soft": "#fef3c7",
    "stay": "#6d28d9",        # xe gửi qua đêm
    "stay_soft": "#ede9fe",
}

WEEKDAYS = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")


def font(size, bold=False):
    return ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal")


DESIGN_SIZE = (1366, 768)   # giao diện được vẽ cho màn hình cỡ này
SCALE_CHOICES = {"auto": "Tự động theo màn hình", "100": "Nhỏ (100%)", "115": "Vừa (115%)",
                 "130": "Lớn (130%)", "150": "Rất lớn (150%)"}
_extra_scale = 1.0          # hệ số phóng thêm do màn hình lớn / người dùng chọn
_scale_applied = False


def dpi_scale(widget):
    """Mức phóng to của Windows (1.0 = 100%, 1.5 = 150%...)."""
    return widget.winfo_fpixels("1i") / 96


def ui_scale(widget):
    """Hệ số nhân cho mọi kích thước tự tính (ảnh, chiều cao dòng bảng, cửa sổ con)."""
    return dpi_scale(widget) * _extra_scale


def auto_scale(win):
    """Màn hình càng lớn thì chữ và nút càng to, để nhìn từ xa vẫn rõ."""
    dpi = dpi_scale(win)
    rong, cao = win.winfo_screenwidth() / dpi, win.winfo_screenheight() / dpi
    thua = min(rong / DESIGN_SIZE[0], cao / DESIGN_SIZE[1]) - 1
    return min(1.5, max(1.0, round((1 + thua * 0.75) * 20) / 20))


def apply_ui_scale(win, choice):
    """
    Đặt cỡ giao diện. Trả về hệ số đang dùng.
    Nên gọi trên một cửa sổ tạm TRƯỚC khi tạo cửa sổ chính: CustomTkinter khóa kích thước
    cửa sổ 1 giây mỗi lần đổi hệ số, gọi sau sẽ làm cửa sổ chính không phóng to được.
    """
    global _extra_scale, _scale_applied
    _extra_scale = auto_scale(win) if choice == "auto" else int(choice) / 100
    ctk.set_widget_scaling(_extra_scale)
    ctk.set_window_scaling(_extra_scale)
    _scale_applied = True
    return _extra_scale


def scale_applied():
    return _scale_applied


def screen_limit(win, w_ratio=0.96, h_ratio=0.88):
    """Kích thước tối đa cho cửa sổ con, chừa chỗ cho thanh tác vụ."""
    return int(win.winfo_screenwidth() * w_ratio), int(win.winfo_screenheight() * h_ratio)


_logo_cache = {}


def logo_image(size):
    """Logo công ty (hình chữ V) dạng CTkImage vuông cạnh size, None nếu thiếu file."""
    if size not in _logo_cache:
        pil = load_image_rgba(LOGO_MARK_FILE)
        _logo_cache[size] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size)) if pil else None
    return _logo_cache[size]


def brand_icon(win):
    """Biểu tượng công ty trên thanh tiêu đề và thanh tác vụ Windows."""
    if ICON_FILE.exists():
        try:
            win.iconbitmap(str(ICON_FILE))
        except tk.TclError:
            pass


def load_image_rgba(path):
    try:
        with Image.open(path) as im:
            return im.convert("RGBA")
    except (OSError, ValueError):
        return None


def show_centered(win, size=None):
    """
    Đặt cửa sổ con vào giữa cửa sổ chính rồi mới hiện, để cửa sổ không bị nhảy chỗ.
    Cửa sổ phải được withdraw() ngay sau khi tạo. size = (rộng, cao) như khi gọi geometry(),
    bỏ trống thì lấy theo kích thước nội dung.
    """
    win.update_idletasks()
    max_w, max_h = screen_limit(win)
    if size is None:
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        geometry = ""  # giữ nguyên cỡ theo nội dung, chỉ đặt vị trí
    else:
        scale = ui_scale(win)
        w, h = min(int(size[0] * scale), max_w), min(int(size[1] * scale), max_h)
        # hạ giới hạn nhỏ nhất xuống, nếu không màn hình thấp sẽ bị ép cửa sổ cao quá
        win.tk.call("wm", "minsize", win._w, min(win.winfo_reqwidth(), w), min(win.winfo_reqheight(), h))
        geometry = f"{w}x{h}"
    master = win.master
    x = master.winfo_rootx() + (master.winfo_width() - w) // 2
    y = master.winfo_rooty() + (master.winfo_height() - h) // 2
    x = max(0, min(x, win.winfo_screenwidth() - w))
    y = max(0, min(y, max_h - h))
    win.tk.call("wm", "geometry", win._w, f"{geometry}+{x}+{y}")
    win.deiconify()


def fit_size(w, h, box_w, box_h):
    scale = min(box_w / w, box_h / h)
    return max(1, int(w * scale)), max(1, int(h * scale))


def bgr_to_pil(frame):
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def load_image(path):
    if not path:
        return None
    try:
        with Image.open(path) as im:
            return im.convert("RGB")
    except (OSError, ValueError):
        return None


def open_file(path):
    """Mở ảnh / thư mục bằng chương trình mặc định của Windows."""
    if path and os.path.exists(path) and hasattr(os, "startfile"):
        os.startfile(str(path))


# ---------------- Thành phần có sẵn kiểu ----------------
def card(master, **kw):
    """Khung trắng bo góc có viền mảnh."""
    kw.setdefault("corner_radius", 16)
    return ctk.CTkFrame(master, fg_color=C["surface"], border_width=1, border_color=C["border"], **kw)


def keycap(master, text):
    """Nhãn trông như phím bấm trên bàn phím."""
    frame = ctk.CTkFrame(master, fg_color=C["surface"], corner_radius=6, border_width=1, border_color="#cbd5e1")
    frame.label = ctk.CTkLabel(frame, text=text, font=font(11, True), text_color=C["text2"], height=20)
    frame.label.pack(padx=8, pady=1)
    return frame


def tabview(master):
    """Khung có tab, nút chọn tab kiểu iOS."""
    return ctk.CTkTabview(master, fg_color=C["surface"], corner_radius=16, border_width=1,
                          border_color=C["border"],
                          segmented_button_fg_color="#e2e8f0",
                          segmented_button_unselected_color="#e2e8f0",
                          segmented_button_unselected_hover_color="#d5dde8",
                          segmented_button_selected_color=C["surface"],
                          segmented_button_selected_hover_color=C["surface"],
                          text_color=C["text"])


def pill(master, text, color, soft, size=12):
    """Nhãn bo tròn nền nhạt, chữ màu."""
    return ctk.CTkLabel(master, text=f"  {text}  ", fg_color=soft, text_color=color, corner_radius=10,
                        font=font(size, True), height=26)


def primary_button(master, text, command, color=None, hover=None, **kw):
    kw.setdefault("height", 40)
    kw.setdefault("font", font(13, True))
    return ctk.CTkButton(master, text=text, command=command, corner_radius=10, text_color="white",
                         fg_color=color or C["accent"], hover_color=hover or C["accent_hover"], **kw)


def secondary_button(master, text, command, **kw):
    kw.setdefault("height", 40)
    kw.setdefault("font", font(13, True))
    return ctk.CTkButton(master, text=text, command=command, corner_radius=10, text_color=C["text2"],
                         fg_color=C["surface2"], hover_color=C["hover"], border_width=1,
                         border_color=C["border"], **kw)


def entry(master, **kw):
    kw.setdefault("height", 38)
    kw.setdefault("font", font(14))
    return ctk.CTkEntry(master, corner_radius=10, fg_color=C["surface2"], border_color=C["border"],
                        border_width=1, text_color=C["text"], placeholder_text_color="#94a3b8", **kw)


def segmented(master, values, command=None, **kw):
    """Nút chọn kiểu iOS: nền xám, mục đang chọn màu trắng."""
    return ctk.CTkSegmentedButton(master, values=values, command=command, corner_radius=10,
                                  fg_color="#e2e8f0", unselected_color="#e2e8f0",
                                  unselected_hover_color="#d5dde8", selected_color=C["surface"],
                                  selected_hover_color=C["surface"], text_color=C["text"],
                                  font=font(12, True), **kw)


def draw_live_badge(img):
    """Vẽ nhãn LIVE và đồng hồ lên khung hình hiển thị (không ảnh hưởng ảnh lưu)."""
    h, w = img.shape[:2]
    s = max(0.6, w / 900)
    pad = int(12 * s)
    # LIVE
    bw, bh = int(78 * s), int(28 * s)
    cv2.rectangle(img, (pad, pad), (pad + bw, pad + bh), (38, 38, 220), -1)
    cv2.circle(img, (pad + int(14 * s), pad + bh // 2), int(5 * s), (255, 255, 255), -1)
    cv2.putText(img, "LIVE", (pad + int(26 * s), pad + int(20 * s)), cv2.FONT_HERSHEY_SIMPLEX,
                0.6 * s, (255, 255, 255), max(1, int(2 * s)), cv2.LINE_AA)
    # đồng hồ
    text = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55 * s, max(1, int(s)))
    x1 = w - pad - tw - int(16 * s)
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, pad), (w - pad, pad + bh), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)
    cv2.putText(img, text, (x1 + int(8 * s), pad + bh // 2 + th // 2), cv2.FONT_HERSHEY_SIMPLEX,
                0.55 * s, (255, 255, 255), max(1, int(s)), cv2.LINE_AA)
    return img


class ImageBox(tk.Frame):
    """Khung hiển thị ảnh tự co giãn theo kích thước, giữ đúng tỉ lệ."""

    def __init__(self, master, placeholder="Chưa có ảnh", width=0, height=0, on_double_click=None, dark=False):
        bg = C["screen"] if dark else C["photo_bg"]
        super().__init__(master, bg=bg, width=width, height=height, highlightthickness=0, bd=0)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.placeholder = placeholder
        self.label = tk.Label(self, bg=bg, fg="#94a3b8", font=(FONT, 12), text=placeholder,
                              justify="center", bd=0, padx=0, pady=0, highlightthickness=0)
        self.label.place(relx=0.5, rely=0.5, anchor="center")
        self._pil = None
        self._photo = None
        self.bind("<Configure>", lambda _e: self._render())
        if on_double_click:
            for widget in (self, self.label):
                widget.bind("<Double-Button-1>", lambda _e: on_double_click())
                widget.configure(cursor="hand2")

    def show(self, pil=None, text=None):
        """Hiện ảnh PIL; None thì hiện dòng chữ thay thế."""
        self._pil = pil
        if pil is None:
            self._photo = None
            self.label.configure(image="", text=text or self.placeholder)
        else:
            self._render()

    def show_frame(self, frame, live=False):
        """Hiện khung hình camera (numpy BGR) - dùng cho video trực tiếp."""
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2 or h < 2:
            return
        fh, fw = frame.shape[:2]
        small = cv2.resize(frame, fit_size(fw, fh, w, h), interpolation=cv2.INTER_AREA)
        if live:
            draw_live_badge(small)
        self._pil = None
        self._photo = ImageTk.PhotoImage(bgr_to_pil(small))
        self.label.configure(image=self._photo, text="")

    def _render(self):
        if self._pil is None:
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2 or h < 2:
            return  # chưa hiện lên màn hình, sẽ vẽ lại khi có sự kiện <Configure>
        self._photo = ImageTk.PhotoImage(self._pil.resize(fit_size(*self._pil.size, w, h), Image.Resampling.LANCZOS))
        self.label.configure(image=self._photo, text="")


def style_treeview(root):
    """Giao diện sáng cho bảng dữ liệu (ttk.Treeview)."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Light.Treeview", background=C["surface"], fieldbackground=C["surface"],
                    foreground=C["text2"], borderwidth=0, rowheight=int(32 * ui_scale(root)), font=(FONT, 11))
    style.configure("Light.Treeview.Heading", background=C["surface2"], foreground=C["muted"],
                    relief="flat", borderwidth=0, font=(FONT, 10, "bold"), padding=(6, 8))
    style.map("Light.Treeview", background=[("selected", C["accent_soft"])],
              foreground=[("selected", C["accent"])])
    style.map("Light.Treeview.Heading", background=[("active", C["hover"])])
    style.layout("Light.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


def make_tree(master, columns, rows=10):
    """Tạo bảng có thanh cuộn. columns = [(khóa, tiêu đề, độ rộng, căn lề)]. Trả về (khung, bảng)."""
    holder = ctk.CTkFrame(master, fg_color=C["surface"], corner_radius=12, border_width=1, border_color=C["border"])
    holder.grid_rowconfigure(0, weight=1)
    holder.grid_columnconfigure(0, weight=1)
    scale = ui_scale(master)
    tree = ttk.Treeview(holder, columns=[c[0] for c in columns], show="headings",
                        style="Light.Treeview", selectmode="browse", height=rows)
    for key, title, width, anchor in columns:
        tree.heading(key, text=title, anchor=anchor)
        tree.column(key, width=int(width * scale), minwidth=int(40 * scale), anchor=anchor, stretch=True)
    bar = ctk.CTkScrollbar(holder, command=tree.yview, fg_color="transparent",
                           button_color="#cbd5e1", button_hover_color="#94a3b8")
    tree.configure(yscrollcommand=bar.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
    bar.grid(row=0, column=1, sticky="ns", padx=2, pady=6)
    tree.tag_configure("odd", background="#f8fafc")
    tree.tag_configure("IN", foreground=C["in_text"])
    tree.tag_configure("OUT", foreground=C["out_text"])
    tree.tag_configure("STAY", foreground=C["stay"])
    return holder, tree


def zebra(i):
    """Tag tô màu xen kẽ cho dòng thứ i."""
    return ("odd",) if i % 2 else ()
