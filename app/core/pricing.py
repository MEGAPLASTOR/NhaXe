"""
Tính tiền gửi xe theo khung giờ.

Mỗi khung giờ có giờ bắt đầu, giờ kết thúc và giá 1 lượt. Xe gửi chạm vào khung nào thì tính tiền khung đó;
gửi qua nhiều khung (hoặc qua ngày hôm sau) thì cộng dồn tiền của từng khung đã đi qua.
Khung có giờ kết thúc nhỏ hơn hoặc bằng giờ bắt đầu là khung qua đêm, ví dụ 18:00 → 06:00.

Ví dụ khung Ngày 06:00-18:00 = 5.000đ, Đêm 18:00-06:00 = 10.000đ:
    vào 08:00 ra 10:00                 -> Ngày                    =  5.000đ
    vào 17:00 ra 19:00                 -> Ngày + Đêm              = 15.000đ
    vào 17:00 ra 07:00 hôm sau         -> Ngày + Đêm + Ngày       = 20.000đ
"""

import re
from datetime import datetime, time, timedelta

FRAME_COUNT = 2
DEFAULT_FRAMES = [
    {"ten": "Ban ngày", "tu": "06:00", "den": "18:00", "gia": 5000},
    {"ten": "Ban đêm", "tu": "18:00", "den": "06:00", "gia": 10000},
]
_HM = re.compile(r"^(\d{1,2})(?:\s*[:hH.]\s*(\d{1,2})?)?\s*(?:p|ph|phút)?$")


def parse_hm(text):
    """'6', '06:00', '6h30', '18h' -> 'HH:MM'. Sai định dạng thì báo ValueError."""
    m = _HM.match(str(text).strip())
    if not m:
        raise ValueError(text)
    hour, minute = int(m[1]), int(m[2] or 0)
    if hour == 24 and minute == 0:
        hour = 0
    if hour > 23 or minute > 59:
        raise ValueError(text)
    return f"{hour:02d}:{minute:02d}"


def parse_money(text):
    """'5000', '5.000', '5,000đ' -> 5000. Sai định dạng thì báo ValueError."""
    digits = re.sub(r"[\s.,đ₫dD]", "", str(text))
    if not digits.isdigit():
        raise ValueError(text)
    return int(digits)


def money(amount):
    """15000 -> '15.000đ'"""
    return f"{amount:,}".replace(",", ".") + "đ"


def _to_time(hm):
    hour, minute = map(int, hm.split(":"))
    return time(hour, minute)


def fee_detail(start, end, frames):
    """Trả về (tổng tiền, [(tên khung, số lần, giá 1 lần), ...]) cho lượt gửi từ start đến end."""
    if end <= start:
        end = start + timedelta(seconds=1)  # vào ra cùng lúc vẫn tính khung đang đứng
    counts = [0] * len(frames)
    day = start.date() - timedelta(days=1)  # khung qua đêm bắt đầu từ hôm trước
    while day <= end.date():
        for i, f in enumerate(frames):
            a = datetime.combine(day, _to_time(f["tu"]))
            b = datetime.combine(day, _to_time(f["den"]))
            if b <= a:
                b += timedelta(days=1)
            if a < end and b > start:
                counts[i] += 1
        day += timedelta(days=1)
    items = [(f["ten"], n, f["gia"]) for f, n in zip(frames, counts) if n]
    return sum(n * price for _, n, price in items), items


def calc_fee(start, end, frames):
    return fee_detail(start, end, frames)[0]


def detail_text(items):
    """[('Ban ngày', 2, 5000)] -> 'Ban ngày × 2 = 10.000đ'"""
    if not items:
        return "Không đi qua khung giờ nào"
    return "   +   ".join(f"{name} × {n} = {money(n * price)}" for name, n, price in items)
