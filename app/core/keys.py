"""
Phím tắt: danh sách chức năng, phím mặc định, tên hiển thị và đọc phím từ sự kiện bàn phím.

Phím được lưu theo tên của Tk (Shift_L, Return, F3...). Tổ hợp phím ghi dạng "Control+Delete", "Alt+F1".
"""

import ctypes
import sys

ACTIONS = (("in", "Xe vào"), ("out", "Xe ra"), ("parked", "Xe đang gửi"), ("history", "Lịch sử"),
           ("reset", "Reset dữ liệu"))
ACTION_TITLES = dict(ACTIONS)
DEFAULT_KEYS = {"in": ["Shift_L"], "out": ["Return", "Shift_R"], "parked": ["F3"], "history": ["F4"],
                "reset": ["Control+Delete"]}
MAX_KEYS = 2                 # mỗi chức năng tối đa 2 phím
RESERVED = {"Escape", "F11"}  # Esc để hủy, F11 để thoát toàn màn hình        # Esc luôn dùng để hủy / đóng
COMBO_MODIFIERS = {"Control_L", "Control_R", "Alt_L", "Alt_R"}  # phím có thể bấm kèm phím khác

# Bit trạng thái phím bổ trợ trong sự kiện Tk
CONTROL_MASK = 0x0004
ALT_MASK = 0x20000 if sys.platform == "win32" else 0x0008

MODIFIER_NAMES = {"Control": "Ctrl", "Alt": "Alt"}
NAMES = {
    "Shift_L": "Shift trái", "Shift_R": "Shift phải",
    "Control_L": "Ctrl trái", "Control_R": "Ctrl phải",
    "Alt_L": "Alt trái", "Alt_R": "Alt phải",
    "Return": "Enter", "KP_Enter": "Enter (phím số)",
    "space": "Space", "Tab": "Tab", "BackSpace": "Backspace", "Delete": "Delete", "Insert": "Insert",
    "Home": "Home", "End": "End", "Prior": "Page Up", "Next": "Page Down", "Caps_Lock": "Caps Lock",
    "Up": "Mũi tên lên", "Down": "Mũi tên xuống", "Left": "Mũi tên trái", "Right": "Mũi tên phải",
    "KP_Add": "+ (phím số)", "KP_Subtract": "- (phím số)", "KP_Multiply": "* (phím số)",
    "KP_Divide": "/ (phím số)", "KP_Decimal": ". (phím số)",
    "plus": "+", "minus": "-", "equal": "=", "comma": ",", "period": ".", "slash": "/",
    "semicolon": ";", "apostrophe": "'", "bracketleft": "[", "bracketright": "]", "backslash": "\\",
    "grave": "`",
}


def _single_name(keysym):
    if keysym in NAMES:
        return NAMES[keysym]
    if keysym.startswith("KP_") and keysym[3:].isdigit():
        return f"{keysym[3:]} (phím số)"
    return keysym.upper() if len(keysym) == 1 else keysym


def key_name(key):
    """Tên dễ đọc, ví dụ "Control+Delete" -> "Ctrl + Delete"."""
    *mods, base = key.split("+")
    return " + ".join([MODIFIER_NAMES.get(m, m) for m in mods] + [_single_name(base)])


def keys_text(keys):
    return " / ".join(key_name(k) for k in keys) or "—"


def event_key(event):
    """
    Tên phím của sự kiện: phân biệt Shift trái / phải, chữ cái không phân biệt hoa thường,
    có giữ Ctrl / Alt thì ghép thành tổ hợp (Control+Delete).
    """
    keysym = event.keysym
    if keysym == "Shift_L" and sys.platform == "win32":
        # Dự phòng cho bản Tk không phân biệt được 2 phím Shift
        try:
            get_key_state = ctypes.windll.user32.GetKeyState
            get_key_state.restype = ctypes.c_short
            if get_key_state(0xA1) & 0x8000 and not get_key_state(0xA0) & 0x8000:  # VK_RSHIFT / VK_LSHIFT
                return "Shift_R"
        except Exception:
            pass
    if keysym.startswith(("Shift_", "Control_", "Alt_")):
        return keysym  # bản thân phím bổ trợ thì không ghép
    if len(keysym) == 1:
        keysym = keysym.lower()
    mods = []
    if event.state & CONTROL_MASK:
        mods.append("Control")
    if event.state & ALT_MASK:
        mods.append("Alt")
    return "+".join(mods + [keysym])
