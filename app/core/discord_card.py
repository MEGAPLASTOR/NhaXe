"""
Vẽ ảnh thẻ thống kê gửi lên Discord (nền tối, ô bo góc, biểu tượng, số to) bằng Pillow.

  render_day(data)      thẻ thống kê 1 ngày: tiền thu, lưu lượng xe + biểu đồ theo giờ, bãi xe, giờ cao điểm
  render_card(data)     thẻ tra cứu 1 số thẻ: lượt gần nhất kèm ảnh vào / ra, các lượt trước
  render_list(data)     thẻ dạng bảng: lịch sử 1 ngày, xe đang gửi

Vẽ ở cỡ gấp đôi rồi thu nhỏ để chữ và nét cong mịn. Ảnh rộng 1100px (Discord hiện ~550px, màn hình nét vẫn rõ).
"""

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .. import APP_NAME, COMPANY
from ..paths import LOGO_MARK_FILE
from .pricing import money

S = 2                    # vẽ gấp đôi rồi thu nhỏ
W = 1100                 # bề rộng ảnh (px)
M, GAP = 24, 16          # lề ngoài, khoảng cách giữa các ô

BG_TOP, BG_BOTTOM = (11, 20, 44), (6, 11, 26)
PANEL, BORDER, LINE = (15, 27, 56), (36, 56, 100), (30, 46, 84)
TEXT, MUTED, DIM = (240, 244, 252), (142, 160, 198), (92, 108, 146)
BLUE, TEAL, GREEN = (59, 151, 232), (34, 197, 214), (52, 211, 153)
ORANGE, GOLD, RED, PURPLE = (251, 146, 60), (250, 204, 21), (248, 113, 113), (167, 139, 250)

FONT_FILES = {"regular": ("segoeui.ttf", "arial.ttf"), "bold": ("segoeuib.ttf", "arialbd.ttf")}
FONT_DIRS = (Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts")


@lru_cache(maxsize=64)
def font(size, bold=False):
    for name in FONT_FILES["bold" if bold else "regular"]:
        for folder in FONT_DIRS:
            if (folder / name).is_file():
                return ImageFont.truetype(str(folder / name), int(size * S))
    return ImageFont.load_default(int(size * S))


@lru_cache(maxsize=1)
def _logo():
    try:
        return Image.open(LOGO_MARK_FILE).convert("RGBA")
    except OSError:
        return None


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    """Khung vẽ: tọa độ truyền vào theo px của ảnh cuối, tự nhân S khi vẽ."""

    def __init__(self, height):
        self.h = height
        self.img = Image.new("RGB", (W * S, height * S), BG_BOTTOM)
        self.d = ImageDraw.Draw(self.img)
        for y in range(height * S):   # nền chuyển màu từ trên xuống
            self.d.line([(0, y), (W * S, y)], fill=_mix(BG_TOP, BG_BOTTOM, y / (height * S)))
        self._stripes()

    def _stripes(self):
        """Mấy vệt xanh chéo ở 2 góc cho giống thẻ game."""
        over = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(over)
        for i, alpha in enumerate((150, 90, 45)):
            o = i * 26 * S
            od.polygon([(o, 0), (o + 18 * S, 0), (0, o + 18 * S), (0, o)], fill=(*BLUE, alpha))
            w, h = W * S, self.h * S
            od.polygon([(w - o, h), (w - o - 18 * S, h), (w, h - o - 18 * S), (w, h - o)], fill=(*BLUE, alpha))
        self.img.paste(over, (0, 0), over)

    # ----- hình cơ bản -----
    def box(self, x, y, w, h, fill=PANEL, border=BORDER, r=18, width=1):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S, fill=fill,
                                 outline=border, width=width * S)

    def line(self, x1, y1, x2, y2, fill=LINE, width=1):
        self.d.line([(x1 * S, y1 * S), (x2 * S, y2 * S)], fill=fill, width=width * S)

    def text(self, x, y, s, size, bold=False, fill=TEXT, anchor="la"):
        self.d.text((x * S, y * S), str(s), font=font(size, bold), fill=fill, anchor=anchor)

    def width(self, s, size, bold=False):
        return self.d.textlength(str(s), font=font(size, bold)) / S

    def fit(self, s, size, max_w, bold=True, smallest=18):
        """Cỡ chữ lớn nhất <= size mà vẫn vừa max_w."""
        while size > smallest and self.width(s, size, bold) > max_w:
            size -= 2
        return size

    def chip(self, x, y, s, color, dot=True):
        """Nhãn bo tròn nhỏ, trả về bề rộng."""
        w = self.width(s, 15, True) + (34 if dot else 22)
        self.box(x, y, w, 30, fill=_mix(PANEL, color, 0.16), border=_mix(PANEL, color, 0.55), r=15)
        tx = x + 11
        if dot:
            self.d.ellipse([(x + 12) * S, (y + 11) * S, (x + 20) * S, (y + 19) * S], fill=color)
            tx = x + 25
        self.text(tx, y + 15, s, 15, True, fill=color, anchor="lm")
        return w

    def paste(self, im, x, y, w, h, r=12, cover=True):
        """Dán ảnh vào ô (cắt cho vừa nếu cover, không thì giữ tỉ lệ), bo góc."""
        im = im.convert("RGB")
        bw, bh = w * S, h * S
        if cover:
            scale = max(bw / im.width, bh / im.height)
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
            left, top = (im.width - bw) // 2, (im.height - bh) // 2
            im = im.crop((left, top, left + bw, top + bh))
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=r * S, fill=255)
        self.img.paste(im, (x * S, y * S), mask)

    def logo_tile(self, x, y, size):
        self.box(x, y, size, size, fill=(255, 255, 255), border=(255, 255, 255), r=16)
        logo = _logo()
        if logo is not None:
            inner = int(size * 0.8 * S)
            lg = logo.resize((inner, inner), Image.LANCZOS)
            off = int((size * S - inner) / 2)
            self.img.paste(lg, (x * S + off, y * S + off), lg)

    def panel_head(self, x, y, w, icon, title, color=BLUE):
        """Tiêu đề ô: biểu tượng + chữ + đường kẻ mảnh."""
        icon(self, x + 20, y + 16, 34, color)
        self.text(x + 66, y + 33, title, 22, True, anchor="lm")
        self.line(x + 20, y + 62, x + w - 20, y + 62)

    def footer(self, y, right_text):
        self.box(M, y, W - 2 * M, 56, r=14)
        self.logo_tile(M + 14, y + 10, 36)
        self.text(M + 62, y + 28, APP_NAME, 17, True, anchor="lm")
        x = M + 62 + self.width(APP_NAME, 17, True) + 16
        self.line(x, y + 18, x, y + 38, fill=BORDER)
        self.text(x + 16, y + 28, f"Powered by {COMPANY}", 15, fill=MUTED, anchor="lm")
        self.text(W - M - 20, y + 28, right_text, 15, fill=MUTED, anchor="rm")

    def png(self):
        out = self.img.resize((W, self.h), Image.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, "PNG", optimize=True)
        return buf.getvalue()


# ---------------- biểu tượng (vẽ tay, không cần font emoji) ----------------
def _px(c, *xy):
    return [v * S for v in xy]


def icon_coin(c, x, y, s, color=GOLD):
    c.d.ellipse(_px(c, x, y, x + s, y + s), fill=(202, 138, 4))
    c.d.ellipse(_px(c, x + s * .1, y + s * .06, x + s * .94, y + s * .9), fill=color)
    c.d.ellipse(_px(c, x + s * .22, y + s * .18, x + s * .82, y + s * .78), outline=(202, 138, 4), width=max(1, int(s * .06 * S)))
    c.text(x + s * .52, y + s * .49, "đ", int(s * .5), True, fill=(146, 64, 14), anchor="mm")


def icon_car(c, x, y, s, color=BLUE):
    c.d.rounded_rectangle(_px(c, x, y + s * .42, x + s, y + s * .8), radius=s * .14 * S, fill=color)
    c.d.polygon([(v * S) for v in (x + s * .18, y + s * .44, x + s * .32, y + s * .16, x + s * .7, y + s * .16,
                                   x + s * .84, y + s * .44)], fill=color)
    c.d.polygon([(v * S) for v in (x + s * .3, y + s * .42, x + s * .38, y + s * .24, x + s * .48, y + s * .24,
                                   x + s * .48, y + s * .42)], fill=(190, 225, 255))
    c.d.polygon([(v * S) for v in (x + s * .54, y + s * .42, x + s * .54, y + s * .24, x + s * .65, y + s * .24,
                                   x + s * .72, y + s * .42)], fill=(190, 225, 255))
    for cx in (x + s * .24, x + s * .76):
        c.d.ellipse(_px(c, cx - s * .13, y + s * .68, cx + s * .13, y + s * .94), fill=(30, 41, 59))
        c.d.ellipse(_px(c, cx - s * .06, y + s * .75, cx + s * .06, y + s * .87), fill=(148, 163, 184))


def _arrow(c, x, y, s, color, down):
    c.d.ellipse(_px(c, x, y, x + s, y + s), fill=_mix(PANEL, color, 0.25), outline=color, width=max(1, int(s * .06 * S)))
    m, t = x + s / 2, s * .14
    if down:
        pts = (m - t, y + s * .24, m + t, y + s * .24, m + t, y + s * .5, m + s * .27, y + s * .5, m, y + s * .78,
               m - s * .27, y + s * .5, m - t, y + s * .5)
    else:
        pts = (m - t, y + s * .76, m + t, y + s * .76, m + t, y + s * .5, m + s * .27, y + s * .5, m, y + s * .22,
               m - s * .27, y + s * .5, m - t, y + s * .5)
    c.d.polygon([v * S for v in pts], fill=color)


def icon_in(c, x, y, s, color=GREEN):
    _arrow(c, x, y, s, color, True)


def icon_out(c, x, y, s, color=ORANGE):
    _arrow(c, x, y, s, color, False)


def icon_parking(c, x, y, s, color=BLUE):
    c.d.rounded_rectangle(_px(c, x, y, x + s, y + s), radius=s * .22 * S, fill=color)
    c.text(x + s * .52, y + s * .5, "P", int(s * .7), True, fill=(255, 255, 255), anchor="mm")


def icon_clock(c, x, y, s, color=PURPLE):
    c.d.ellipse(_px(c, x, y, x + s, y + s), outline=color, width=max(2, int(s * .1 * S)))
    m = (x + s / 2, y + s / 2)
    c.d.line([(m[0] * S, m[1] * S), (m[0] * S, (y + s * .22) * S)], fill=color, width=max(2, int(s * .09 * S)))
    c.d.line([(m[0] * S, m[1] * S), ((x + s * .72) * S, (y + s * .62) * S)], fill=color, width=max(2, int(s * .09 * S)))


def icon_chart(c, x, y, s, color=TEAL):
    for i, h in enumerate((.45, .75, .3, 1.0)):
        bx = x + s * (.05 + i * .24)
        c.d.rounded_rectangle(_px(c, bx, y + s * (1 - h), bx + s * .17, y + s), radius=s * .04 * S, fill=color)


def icon_card(c, x, y, s, color=BLUE):
    c.d.rounded_rectangle(_px(c, x, y + s * .14, x + s, y + s * .86), radius=s * .12 * S, fill=color)
    c.d.rectangle(_px(c, x, y + s * .3, x + s, y + s * .42), fill=(30, 58, 110))
    c.d.rounded_rectangle(_px(c, x + s * .12, y + s * .56, x + s * .5, y + s * .7), radius=s * .04 * S, fill=(210, 230, 255))


def icon_list(c, x, y, s, color=TEAL):
    for i in range(3):
        yy = y + s * (.16 + i * .3)
        c.d.ellipse(_px(c, x, yy, x + s * .18, yy + s * .18), fill=color)
        c.d.rounded_rectangle(_px(c, x + s * .3, yy + s * .03, x + s, yy + s * .15), radius=s * .05 * S, fill=color)


def icon_photo(c, x, y, s, color=TEAL):
    c.d.rounded_rectangle(_px(c, x, y + s * .12, x + s, y + s * .88), radius=s * .1 * S, outline=color,
                          width=max(2, int(s * .08 * S)))
    c.d.polygon([v * S for v in (x + s * .14, y + s * .76, x + s * .4, y + s * .42, x + s * .6, y + s * .64,
                                 x + s * .72, y + s * .52, x + s * .88, y + s * .76)], fill=color)
    c.d.ellipse(_px(c, x + s * .62, y + s * .24, x + s * .78, y + s * .4), fill=color)


def _stat(c, x, y, icon, color, label, value, value_size=32):
    """1 chỉ số kiểu ngang: biểu tượng bên trái, chữ nhỏ + số to bên phải."""
    icon(c, x, y + 8, 40, color)
    c.text(x + 54, y + 2, label, 15, fill=MUTED)
    c.text(x + 54, y + 22, value, value_size, True)


# ---------------- thẻ thống kê 1 ngày ----------------
def render_day(data):
    st = data["stats"]
    c = Canvas(644)
    left_w = 640
    rx, rw = M + left_w + GAP, W - 2 * M - left_w - GAP

    # -- đầu thẻ --
    c.box(M, M, left_w, 180)
    c.logo_tile(M + 22, M + 24, 132)
    tx = M + 178
    c.text(tx, M + 34, "BÁO CÁO NHÀ XE", 15, True, fill=TEAL)
    c.text(tx, M + 76, data["label"], c.fit(data["label"], 38, left_w - 200), True, anchor="lm")
    c.text(tx, M + 112, "Thống kê xe vào / ra và tiền thu", 17, fill=MUTED, anchor="lm")
    if data["final"]:
        cx = tx + c.chip(tx, M + 134, "Đã chốt sổ", GREEN) + 10
    else:
        cx = tx + c.chip(tx, M + 134, f"Tạm tính tới {data['now']:%H:%M}", ORANGE) + 10
    c.chip(cx, M + 134, COMPANY, BLUE, dot=False)

    # -- tiền thu --
    c.box(rx, M, rw, 180)
    icon_coin(c, rx + 22, M + 22, 40)
    c.text(rx + 74, M + 42, "Tiền thu", 18, fill=MUTED, anchor="lm")
    amount = money(st["money"])
    c.text(rx + 22, M + 112, amount, c.fit(amount, 54, rw - 44), True, anchor="lm")
    c.text(rx + 22, M + 156, f"từ {st['out']} lượt xe đã ra", 16, fill=MUTED, anchor="lm")

    # -- lưu lượng xe + biểu đồ --
    y2 = M + 180 + GAP
    c.box(M, y2, left_w, 320)
    c.panel_head(M, y2, left_w, icon_car, "Lưu lượng xe")
    col = (left_w - 40) / 3
    for i, (icon, color, label, value) in enumerate((
            (icon_parking, BLUE, "Xe trong ngày", st["total"]),
            (icon_in, GREEN, "Xe vào", st["in"]),
            (icon_out, ORANGE, "Xe ra", st["out"]))):
        x = M + 20 + i * col
        if i:
            c.line(x - 8, y2 + 82, x - 8, y2 + 138)
        _stat(c, x + 6, y2 + 80, icon, color, label, value)
    _hour_chart(c, M + 24, y2 + 186, left_w - 48, 118, data["hourly_in"], data["hourly_out"])

    # -- bãi xe --
    c.box(rx, y2, rw, 152)
    c.panel_head(rx, y2, rw, icon_parking, "Bãi xe")
    half = (rw - 40) / 2
    c.text(rx + 22, y2 + 86, "Còn trong bãi cuối ngày" if data["final"] else "Còn trong bãi", 15, fill=MUTED)
    c.text(rx + 22, y2 + 108, st["stay"], 32, True)
    if data["parked_now"] is not None:
        c.line(rx + 20 + half, y2 + 84, rx + 20 + half, y2 + 140)
        c.text(rx + 34 + half, y2 + 86, "Đang gửi lúc này", 15, fill=MUTED)
        c.text(rx + 34 + half, y2 + 108, data["parked_now"], 32, True)

    # -- giờ cao điểm --
    y3 = y2 + 152 + GAP
    c.box(rx, y3, rw, 152)
    c.panel_head(rx, y3, rw, icon_clock, "Giờ cao điểm", PURPLE)
    if data["peak"]:
        h, n = data["peak"]
        c.text(rx + 22, y3 + 86, f"{n} lượt vào / ra", 15, fill=MUTED)
        c.text(rx + 22, y3 + 108, f"{h:02d}:00–{(h + 1) % 24:02d}:00", 26, True)
    else:
        c.text(rx + 22, y3 + 86, "Chưa có lượt nào", 15, fill=MUTED)
        c.text(rx + 22, y3 + 108, "—", 26, True)
    c.line(rx + 20 + half, y3 + 84, rx + 20 + half, y3 + 140)
    c.text(rx + 34 + half, y3 + 86, "Gửi trung bình", 15, fill=MUTED)
    c.text(rx + 34 + half, y3 + 108, data["avg_stay"], c.fit(data["avg_stay"], 22, half - 20), True)

    c.footer(644 - M - 56, f"Tạo lúc {data['now']:%H:%M  %d/%m/%Y}")
    return c.png()


def _hour_chart(c, x, y, w, h, hourly_in, hourly_out):
    """Cột xe vào (xanh) và xe ra (cam) theo từng giờ trong ngày."""
    top = max(1, max(hourly_in), max(hourly_out))
    slot = w / 24
    bar = slot * 0.34
    c.text(x, y - 10, "Xe theo giờ", 15, True, fill=MUTED, anchor="ls")
    lx = x + w
    for color, name in ((ORANGE, "ra"), (GREEN, "vào")):
        tw = c.width(name, 14)
        c.text(lx - tw, y - 10, name, 14, fill=MUTED, anchor="ls")
        c.d.rounded_rectangle(_px(c, lx - tw - 18, y - 22, lx - tw - 6, y - 10), radius=3 * S, fill=color)
        lx -= tw + 34
    base = y + h - 20
    c.line(x, base, x + w, base)
    for i in range(24):
        bx = x + i * slot + slot * 0.14
        for j, (vals, color) in enumerate(((hourly_in, GREEN), (hourly_out, ORANGE))):
            if vals[i]:
                bh = max(4, (h - 30) * vals[i] / top)
                left = bx + j * (bar + 2)
                c.d.rounded_rectangle(_px(c, left, base - bh, left + bar, base), radius=2 * S, fill=color)
        if i % 3 == 0:
            c.text(x + i * slot + slot / 2, base + 14, f"{i}h", 12, fill=DIM, anchor="mm")


# ---------------- thẻ tra cứu 1 số thẻ ----------------
def render_card(data):
    """data: card, latest {vao, ra, duration, fee, estimate, parked}, photos [(nhãn, đường dẫn hoặc None)],
    history [(vào, ra, đã gửi, tiền, đang gửi?)], total"""
    hist = data["history"]
    hist_h = 116 + 44 * max(1, len(hist))
    height = M + 160 + GAP + 300 + GAP + hist_h + GAP + 56 + M
    c = Canvas(height)
    lt = data["latest"]

    # -- đầu thẻ --
    c.box(M, M, W - 2 * M, 160)
    c.box(M + 22, M + 22, 116, 116, fill=_mix(PANEL, BLUE, 0.2), border=_mix(PANEL, BLUE, 0.6), r=18)
    icon_card(c, M + 42, M + 42, 76)
    tx = M + 162
    c.text(tx, M + 36, "TRA CỨU SỐ THẺ", 15, True, fill=TEAL)
    c.text(tx, M + 86, f"Thẻ {data['card']}", c.fit(f"Thẻ {data['card']}", 46, 460), True, anchor="lm")
    cx = tx + c.chip(tx, M + 114, "Đang gửi" if lt["parked"] else "Đã ra", GREEN if lt["parked"] else ORANGE) + 10
    c.chip(cx, M + 114, f"{data['total']} lượt đã ghi", BLUE, dot=False)
    fx = W - M - 22
    c.text(fx, M + 52, "Tiền tạm tính" if lt["estimate"] else "Tiền lượt gần nhất", 17, fill=MUTED, anchor="rm")
    c.text(fx, M + 104, money(lt["fee"]), 50, True, anchor="rm")
    icon_coin(c, fx - c.width(money(lt["fee"]), 50, True) - 56, M + 84, 40)

    # -- ảnh vào / ra --
    y2 = M + 160 + GAP
    left_w = 640
    c.box(M, y2, left_w, 300)
    c.panel_head(M, y2, left_w, icon_photo, "Ảnh lượt gần nhất", TEAL)
    pw = (left_w - 60) / 2
    for i, ((label, path), color) in enumerate(zip(data["photos"], (GREEN, ORANGE))):
        px = int(M + 20 + i * (pw + 20))
        py = y2 + 82
        img = None
        if path:
            try:
                img = Image.open(path)
            except OSError:
                img = None
        if img is not None:
            c.paste(img, px, py, int(pw), 168)
        else:
            c.box(px, py, int(pw), 168, fill=(10, 18, 38), border=LINE, r=12)
            c.text(px + pw / 2, py + 84, "Chưa có ảnh" if i else "Không có ảnh", 16, fill=DIM, anchor="mm")
        c.text(px + 2, py + 194, label, 15, True, fill=color, anchor="lm")

    # -- chi tiết --
    rx, rw = M + left_w + GAP, W - 2 * M - left_w - GAP
    c.box(rx, y2, rw, 300)
    c.panel_head(rx, y2, rw, icon_clock, "Chi tiết", PURPLE)
    for i, (label, value) in enumerate((("Giờ vào", lt["vao"]), ("Giờ ra", lt["ra"]),
                                        ("Thời gian gửi", lt["duration"]))):
        yy = y2 + 92 + i * 66
        c.text(rx + 22, yy, label, 15, fill=MUTED)
        c.text(rx + 22, yy + 22, value, c.fit(value, 24, rw - 44), True)

    # -- các lượt gần đây --
    y3 = y2 + 300 + GAP
    c.box(M, y3, W - 2 * M, hist_h)
    c.panel_head(M, y3, W - 2 * M, icon_list, "Các lượt gần đây", TEAL)
    cols = (M + 30, M + 330, M + 630, M + 860)
    for i, name in enumerate(("Giờ vào", "Giờ ra", "Đã gửi", "Tiền")):
        c.text(cols[i], y3 + 86, name, 14, True, fill=DIM, anchor="lm")
    if not hist:
        c.text(cols[0], y3 + 120, "Chưa có lượt nào khác", 16, fill=MUTED, anchor="lm")
    for j, (t_in, t_out, dur, fee, parked) in enumerate(hist):
        yy = y3 + 120 + j * 44
        if j % 2 == 0:
            c.box(M + 16, yy - 18, W - 2 * M - 32, 38, fill=(19, 33, 66), border=(19, 33, 66), r=10)
        c.text(cols[0], yy, t_in, 17, anchor="lm")
        c.text(cols[1], yy, t_out, 17, fill=GREEN if parked else TEXT, anchor="lm")
        c.text(cols[2], yy, dur, 17, fill=MUTED, anchor="lm")
        c.text(cols[3], yy, fee, 17, True, anchor="lm")

    c.footer(height - M - 56, "Ảnh có thể đã tự xóa sau số ngày lưu trữ")
    return c.png()


# ---------------- thẻ dạng bảng ----------------
def render_list(data):
    """data: kicker, title, subtitle, chips [(chữ, màu)], columns [(tên, x tương đối)],
    rows [(ô1, ô2, ..., màu chấm hoặc None)], more (số dòng không hiện), footer"""
    rows = data["rows"]
    table_h = 116 + 42 * max(1, len(rows)) + (34 if data.get("more") else 0)
    height = M + 150 + GAP + table_h + GAP + 56 + M
    c = Canvas(height)

    c.box(M, M, W - 2 * M, 150)
    c.box(M + 22, M + 22, 106, 106, fill=_mix(PANEL, TEAL, 0.18), border=_mix(PANEL, TEAL, 0.55), r=18)
    data.get("icon", icon_list)(c, M + 43, M + 43, 64, TEAL)
    tx = M + 152
    c.text(tx, M + 34, data["kicker"], 15, True, fill=TEAL)
    c.text(tx, M + 78, data["title"], c.fit(data["title"], 38, W - 2 * M - 180), True, anchor="lm")
    c.text(tx, M + 112, data["subtitle"], 16, fill=MUTED, anchor="lm")
    cx = W - M - 22
    for text, color in reversed(data.get("chips", [])):
        w = c.width(text, 15, True) + 34
        cx -= w
        c.chip(cx, M + 22, text, color)
        cx -= 10

    y2 = M + 150 + GAP
    c.box(M, y2, W - 2 * M, table_h)
    c.panel_head(M, y2, W - 2 * M, icon_list, data.get("table_title", "Danh sách"), TEAL)
    for name, x in data["columns"]:
        c.text(M + x, y2 + 86, name, 14, True, fill=DIM, anchor="lm")
    if not rows:
        c.text(M + data["columns"][0][1], y2 + 120, "Không có lượt nào", 16, fill=MUTED, anchor="lm")
    for j, row in enumerate(rows):
        yy = y2 + 120 + j * 42
        if j % 2 == 0:
            c.box(M + 16, yy - 18, W - 2 * M - 32, 38, fill=(19, 33, 66), border=(19, 33, 66), r=10)
        *cells, dot = row
        for k, ((_, x), value) in enumerate(zip(data["columns"], cells)):
            if k == 0 and dot:
                c.d.ellipse(_px(c, M + x - 16, yy - 5, M + x - 6, yy + 5), fill=dot)
            c.text(M + x, yy, value, 17, k == 0 or k == len(cells) - 1, fill=TEXT if k != 3 else MUTED, anchor="lm")
    if data.get("more"):
        c.text(M + 30, y2 + table_h - 26, f"… còn {data['more']} lượt nữa — xem đủ trong phần mềm (F4)", 15,
               fill=MUTED, anchor="lm")

    c.footer(height - M - 56, data.get("footer", ""))
    return c.png()
