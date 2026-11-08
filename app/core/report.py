"""
Thống kê theo ngày, dùng chung cho tab "Theo từng ngày", báo cáo Discord lúc 00:00 và bot tra cứu Discord.

Một ngày gồm mọi xe có mặt trong bãi hôm đó: xe vào trong ngày, xe ra trong ngày và xe gửi từ hôm trước sang.
"""

import csv
import io
from datetime import date, datetime
from pathlib import Path

from .pricing import money
from .storage import record_duration

WEEKDAYS = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")
CSV_HEADER = ["Số thẻ", "Giờ vào", "Giờ ra", "Thời gian gửi", "Trạng thái", "Tiền gửi (đ)", "Ảnh vào", "Ảnh ra"]


def parse_day(text):
    """'31/10/2026', '31-10-2026', '31/10/26', '2026-10-31' -> date. Trống -> None, sai -> ValueError."""
    text = text.strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(text)


def day_label(day, today=None):
    """'Hôm nay, 31/10/2026' / 'Hôm qua, ...' / 'Thứ Sáu, ...'"""
    today = today or date.today()
    gap = (today - day).days
    name = "Hôm nay" if gap == 0 else "Hôm qua" if gap == 1 else WEEKDAYS[day.weekday()]
    return f"{name}, {day:%d/%m/%Y}"


def day_status(rec, day, today=None):
    """Trạng thái 1 lượt trong ngày day -> (chữ hiện ra, nhãn màu IN / OUT / STAY)."""
    today = today or date.today()
    if rec["gio_ra"] is not None and rec["gio_ra"][:10] == day.isoformat():
        return "Đã ra", "OUT"
    if rec["gio_ra"] is None and day == today:
        return "Đang gửi", "IN"
    return "Gửi qua đêm", "STAY"


def day_summary(rows, day, fee_of=None, today=None):
    """Đếm xe trong ngày: total, in (vào trong ngày), out (ra trong ngày), stay (còn trong bãi cuối ngày),
    money (tiền thu của xe ra trong ngày)."""
    d = day.isoformat()
    stats = dict.fromkeys(("total", "in", "out", "stay", "money"), 0)
    for r in rows:
        left = day_status(r, day, today)[1] == "OUT"
        stats["total"] += 1
        stats["in"] += r["gio_vao"][:10] == d
        stats["out"] += left
        stats["stay"] += not left
        if left and fee_of is not None:
            stats["money"] += fee_of(r)[0]
    return stats


def fee_cell(rec, fee_of):
    if fee_of is None:
        return "—"
    amount, estimate = fee_of(rec)
    return f"~ {money(amount)}" if estimate else money(amount)


def csv_text(rows, fee_of=None):
    """Danh sách lượt gửi dạng CSV (mở được bằng Excel)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_HEADER)
    for r in rows:
        fee = ""
        if fee_of is not None:
            amount, estimate = fee_of(r)
            fee = f"{amount} (tạm tính)" if estimate else amount
        writer.writerow([r["so_the"], r["gio_vao"], r["gio_ra"] or "", record_duration(r),
                         "Đang gửi" if r["gio_ra"] is None else "Đã ra", fee,
                         Path(r["anh_vao"]).name if r["anh_vao"] else "",
                         Path(r["anh_ra"]).name if r["anh_ra"] else ""])
    return out.getvalue()


def csv_bytes(rows, fee_of=None):
    """CSV có BOM để Excel đọc đúng tiếng Việt."""
    return csv_text(rows, fee_of).encode("utf-8-sig")
