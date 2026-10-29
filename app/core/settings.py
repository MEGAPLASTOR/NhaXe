"""Đọc / ghi cài đặt (phím tắt, camera, thời gian giữ ảnh, giá gửi xe, mật khẩu) trong file config.ini."""

import configparser
import copy
import hashlib

from .keys import DEFAULT_KEYS
from .pricing import DEFAULT_FRAMES, FRAME_COUNT, parse_hm

CAMERA_SECTIONS = ("camera_vao", "camera_ra")
CAMERA_FIELDS = ("ip", "tai_khoan", "mat_khau", "luong", "url")
KEY_OPTIONS = {"in": "xe_vao", "out": "xe_ra", "parked": "xe_dang_gui", "history": "lich_su",
               "reset": "reset_du_lieu"}
DEFAULT_KEEP_DAYS = 30
DEFAULT_SCALE = "auto"
SCALE_VALUES = ("auto", "100", "115", "130", "150")
DEFAULT_PASSWORD = "Nha@123"
_SALT = "vidatex-nhaxe:"

HEADER = """\
; ===== CẤU HÌNH PHẦN MỀM QUẢN LÝ NHÀ XE =====
; Có thể sửa trực tiếp trong chương trình bằng nút "Cài đặt".
;
; [camera_vao] / [camera_ra]
;   ip        : địa chỉ IP camera Imou trong mạng nhà
;   tai_khoan : mặc định admin
;   mat_khau  : mã Safety Code in trên tem camera (hoặc mật khẩu thiết bị nếu đã đổi)
;   luong     : 0 = hình nét (luồng chính), 1 = hình mượt (luồng phụ)
;   url       : địa chỉ RTSP đầy đủ nếu muốn tự nhập (bỏ qua ip / mật khẩu); 0 = dùng webcam máy tính
;   Để trống ip và url thì chạy chế độ thử với ảnh giả.
; [phim_tat]   : tên phím theo Tk (Shift_L, Shift_R, Return, F3...), nhiều phím cách nhau dấu phẩy,
;               tổ hợp phím ghi dạng Control+Delete
; [luu_tru]    : giu_anh_ngay = số ngày giữ ảnh, 0 = không bao giờ tự xóa
; [gia_ve]     : 2 khung giờ tính tiền (giờ dạng HH:MM, giá tính bằng đồng); gửi qua nhiều khung thì cộng dồn
; [bao_mat]    : mật khẩu mở Cài đặt (đã mã hóa) - đổi trong Cài đặt, xóa dòng này = về mật khẩu mặc định
; [giao_dien]  : co_giao_dien = auto (tự theo màn hình) hoặc 100 / 115 / 130 / 150 (phần trăm)
"""


def hash_password(password):
    return hashlib.sha256((_SALT + password).encode("utf-8")).hexdigest()


def check_password(settings, password):
    return hash_password(password) == settings["pass_hash"]


def _read(path):
    cfg = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";", "#"))
    cfg.read(path, encoding="utf-8-sig")
    return cfg


def load_settings(path):
    cfg = _read(path)
    keys = {}
    for action, option in KEY_OPTIONS.items():
        raw = cfg.get("phim_tat", option, fallback=None)
        keys[action] = list(DEFAULT_KEYS[action]) if raw is None else [k.strip() for k in raw.split(",") if k.strip()]
    cameras = {}
    for section in CAMERA_SECTIONS:
        cam = {field: cfg.get(section, field, fallback="").strip() for field in CAMERA_FIELDS}
        cam["tai_khoan"] = cam["tai_khoan"] or "admin"
        cam["luong"] = cam["luong"] or "0"
        cameras[section] = cam
    try:
        keep_days = max(0, int(cfg.get("luu_tru", "giu_anh_ngay", fallback=str(DEFAULT_KEEP_DAYS))))
    except ValueError:
        keep_days = DEFAULT_KEEP_DAYS
    prices = []
    for i, default in enumerate(DEFAULT_FRAMES[:FRAME_COUNT], 1):
        try:
            prices.append({
                "ten": cfg.get("gia_ve", f"khung{i}_ten", fallback=default["ten"]).strip() or default["ten"],
                "tu": parse_hm(cfg.get("gia_ve", f"khung{i}_tu", fallback=default["tu"])),
                "den": parse_hm(cfg.get("gia_ve", f"khung{i}_den", fallback=default["den"])),
                "gia": max(0, int(cfg.get("gia_ve", f"khung{i}_gia", fallback=str(default["gia"])))),
            })
        except ValueError:
            prices.append(copy.deepcopy(default))
    pass_hash = cfg.get("bao_mat", "mat_khau_cai_dat", fallback="").strip() or hash_password(DEFAULT_PASSWORD)
    scale = cfg.get("giao_dien", "co_giao_dien", fallback=DEFAULT_SCALE).strip()
    if scale not in SCALE_VALUES:
        scale = DEFAULT_SCALE
    return {"keys": keys, "cameras": cameras, "keep_days": keep_days, "prices": prices,
            "pass_hash": pass_hash, "scale": scale}


def save_settings(path, settings):
    lines = [HEADER]
    for section in CAMERA_SECTIONS:
        lines.append(f"[{section}]")
        for field in CAMERA_FIELDS:
            lines.append(f"{field} = {settings['cameras'][section][field]}")
        lines.append("")
    lines.append("[phim_tat]")
    for action, option in KEY_OPTIONS.items():
        lines.append(f"{option} = {', '.join(settings['keys'][action])}")
    lines.append("")
    lines.append("[luu_tru]")
    lines.append(f"giu_anh_ngay = {settings['keep_days']}")
    lines.append("")
    lines.append("[gia_ve]")
    for i, frame in enumerate(settings["prices"], 1):
        for field in ("ten", "tu", "den", "gia"):
            lines.append(f"khung{i}_{field} = {frame[field]}")
    lines.append("")
    lines.append("[giao_dien]")
    lines.append(f"co_giao_dien = {settings['scale']}")
    lines.append("")
    lines.append("[bao_mat]")
    lines.append(f"mat_khau_cai_dat = {settings['pass_hash']}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
