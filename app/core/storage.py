"""
Lưu trữ lượt gửi xe.

- Ảnh: data/anh/<năm-tháng-ngày>/<SốThẻ>_<ngày-tháng-năm>_<giờ>h<phút>m<giây>_<IN|OUT>.jpg
       ví dụ: data/anh/2026-10-28/111_28-10-2026_21h44m35_IN.jpg
- Thông tin: cơ sở dữ liệu SQLite data/nhaxe.db (bảng luot_gui, mỗi dòng = 1 lượt gửi)
"""

import csv
import re
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import cv2
from PIL import Image

TIME_FMT = "%Y-%m-%d %H:%M:%S"
CARD_PATTERN = re.compile(r"^[A-Z0-9_-]{1,20}$")
# Tên ảnh kiểu cũ: <SốThẻ>_<năm-tháng-ngày>_<giờ-phút-giây>_<IN|OUT...>
OLD_PHOTO_NAME = re.compile(r"^(?P<card>.+)_(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})"
                            r"_(?P<h>\d{2})-(?P<mi>\d{2})-(?P<s>\d{2})_(?P<rest>(IN|OUT).*)$")


def photo_name(card, when, kind):
    """Tên ảnh: SốThẻ_ngày-tháng-năm_giờ-phút-giây_IN/OUT, ví dụ 111_28-10-2026_21h44m35_IN"""
    return f"{card}_{when:%d-%m-%Y}_{when:%H}h{when:%M}m{when:%S}_{kind}"


# ---------------- Định dạng thời gian ----------------
def to_text(dt):
    return dt.strftime(TIME_FMT)


def parse_time(text):
    return datetime.strptime(text, TIME_FMT) if text else None


def vn_time(text):
    dt = parse_time(text)
    return dt.strftime("%H:%M:%S  %d/%m/%Y") if dt else "—"


def short_time(text):
    """Hôm nay thì chỉ hiện giờ, ngày khác thì kèm ngày/tháng."""
    dt = parse_time(text)
    if dt is None:
        return "—"
    return dt.strftime("%H:%M:%S") if dt.date() == datetime.now().date() else dt.strftime("%d/%m %H:%M")


def format_duration(seconds):
    minutes = int(seconds // 60)
    if minutes < 1:
        return "dưới 1 phút"
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days} ngày")
    if hours:
        parts.append(f"{hours} giờ")
    if minutes:
        parts.append(f"{minutes} phút")
    return " ".join(parts)


def record_duration(rec):
    start = parse_time(rec["gio_vao"])
    end = parse_time(rec["gio_ra"]) or datetime.now()
    return format_duration((end - start).total_seconds())


def stamp(frame, lines):
    """Ghi thông tin (chỉ ký tự không dấu) lên góc dưới ảnh, cỡ chữ theo độ phân giải."""
    img = frame.copy()
    h, w = img.shape[:2]
    s = w / 900
    line_h = int(40 * s)
    thickness = max(1, round(2 * s))
    box_h = line_h * len(lines) + int(12 * s)
    cv2.rectangle(img, (0, h - box_h), (w, h), (0, 0, 0), -1)
    for i, text in enumerate(lines):
        y = h - box_h + line_h * (i + 1)
        cv2.putText(img, text, (int(12 * s), y), cv2.FONT_HERSHEY_SIMPLEX, s, (255, 255, 255), thickness)
    return img


# ---------------- Kho dữ liệu ----------------
class Storage:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.image_dir = self.data_dir / "anh"
        self.export_dir = self.data_dir / "xuat_file"
        self.backup_dir = self.data_dir / "sao_luu"
        self.db_path = self.data_dir / "nhaxe.db"
        self._open()
        self._rename_old_photos()

    def _open(self):
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS luot_gui (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                so_the  TEXT NOT NULL,
                gio_vao TEXT NOT NULL,
                anh_vao TEXT NOT NULL DEFAULT '',
                gio_ra  TEXT,
                anh_ra  TEXT,
                tien    INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_luot_the ON luot_gui(so_the);
            CREATE INDEX IF NOT EXISTS idx_luot_vao ON luot_gui(gio_vao);
        """)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(luot_gui)")}
        if "tien" not in columns:  # dữ liệu từ bản cũ chưa có cột tiền gửi xe
            self.db.execute("ALTER TABLE luot_gui ADD COLUMN tien INTEGER")
            self.db.commit()

    # ----- reset -----
    def summary(self):
        """Số lượt gửi, số xe đang gửi, số ảnh hiện có (hiện trong hộp xác nhận reset)."""
        one = lambda sql: self.db.execute(sql).fetchone()[0]
        return {
            "records": one("SELECT COUNT(*) FROM luot_gui"),
            "parked": one("SELECT COUNT(*) FROM luot_gui WHERE gio_ra IS NULL"),
            "photos": sum(1 for _ in self.image_dir.rglob("*.jpg")),
        }

    def reset(self, backup=True):
        """
        Xóa toàn bộ lượt gửi và ảnh, bắt đầu lại từ đầu. Cài đặt (config.ini) và file Excel đã xuất được giữ.
        backup=True: chuyển dữ liệu cũ vào data/sao_luu/truoc_reset_<ngày giờ>/ thay vì xóa hẳn.
        Trả về thư mục sao lưu (hoặc None nếu xóa hẳn).
        """
        self.db.close()
        dest = None
        if backup:
            dest = self.backup_dir / f"truoc_reset_{datetime.now():%d-%m-%Y_%Hh%Mm%S}"
            dest.mkdir(parents=True, exist_ok=True)
            # chuyển ảnh trước: nếu lỗi (ảnh đang mở ở chương trình khác) thì CSDL vẫn còn nguyên
            if self.image_dir.exists():
                shutil.move(str(self.image_dir), str(dest / self.image_dir.name))
            if self.db_path.exists():
                shutil.move(str(self.db_path), str(dest / self.db_path.name))
        else:
            self.db_path.unlink(missing_ok=True)
            shutil.rmtree(self.image_dir, ignore_errors=True)
        self._open()
        return dest

    def _rename_old_photos(self):
        """Đổi tên ảnh kiểu cũ (năm-tháng-ngày_giờ-phút-giây) sang kiểu mới và cập nhật cơ sở dữ liệu."""
        renamed = []
        for photo in self.image_dir.glob("*/*.jpg"):
            m = OLD_PHOTO_NAME.match(photo.stem)
            if not m:
                continue
            new = photo.with_name(f"{m['card']}_{m['d']}-{m['mo']}-{m['y']}_{m['h']}h{m['mi']}m{m['s']}"
                                  f"_{m['rest']}{photo.suffix}")
            if new.exists():
                continue
            try:
                photo.rename(new)
            except OSError:
                continue
            renamed.append((self._rel(new), self._rel(photo)))
        for new_rel, old_rel in renamed:
            self.db.execute("UPDATE luot_gui SET anh_vao = ? WHERE anh_vao = ?", (new_rel, old_rel))
            self.db.execute("UPDATE luot_gui SET anh_ra = ? WHERE anh_ra = ?", (new_rel, old_rel))
        if renamed:
            self.db.commit()

    def _rel(self, path):
        return path.relative_to(self.data_dir).as_posix()

    # ----- ảnh -----
    def save_photo(self, frame, card, when, kind):
        """Lưu ảnh IN / OUT, trả về đường dẫn tương đối so với thư mục data."""
        folder = self.image_dir / when.strftime("%Y-%m-%d")
        folder.mkdir(parents=True, exist_ok=True)
        base = photo_name(card, when, kind)
        path = folder / f"{base}.jpg"
        n = 2
        while path.exists():
            path = folder / f"{base}_{n}.jpg"
            n += 1
        gate = "CONG VAO" if kind == "IN" else "CONG RA"
        img = stamp(frame, [f"THE: {card}   |   {kind}   |   {gate}", when.strftime("%d/%m/%Y  %H:%M:%S") + "   |   VIDATEX"])
        Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(path, "JPEG", quality=90)
        return self._rel(path)

    def abs_path(self, rel):
        return self.data_dir / rel if rel else None

    def cleanup_photos(self, keep_days):
        """
        Xóa ảnh đã lưu quá keep_days ngày (tính theo thư mục ngày chụp). Trả về số ảnh đã xóa.
        Ảnh lúc vào của xe còn đang gửi luôn được giữ lại để đối chiếu khi xe ra.
        Thông tin lượt gửi trong cơ sở dữ liệu vẫn giữ nguyên để tra cứu lịch sử.
        """
        if keep_days <= 0:
            return 0
        cutoff = (datetime.now() - timedelta(days=keep_days)).date()
        keep = {row[0] for row in self.db.execute(
            "SELECT anh_vao FROM luot_gui WHERE gio_ra IS NULL AND anh_vao != ''")}
        removed = 0
        for folder in self.image_dir.iterdir():
            if not folder.is_dir():
                continue
            try:
                day = datetime.strptime(folder.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if day >= cutoff:
                continue
            for photo in folder.glob("*.jpg"):
                if self._rel(photo) in keep:
                    continue
                try:
                    photo.unlink()
                    removed += 1
                except OSError:
                    pass
            try:
                folder.rmdir()  # chỉ xóa được khi thư mục đã trống
            except OSError:
                pass
        return removed

    # ----- ghi -----
    def add_in(self, card, when, image):
        cur = self.db.execute("INSERT INTO luot_gui (so_the, gio_vao, anh_vao) VALUES (?, ?, ?)",
                              (card, to_text(when), image))
        self.db.commit()
        return cur.lastrowid

    def set_out(self, rid, when, image, fee=None):
        self.db.execute("UPDATE luot_gui SET gio_ra = ?, anh_ra = ?, tien = ? WHERE id = ?",
                        (to_text(when), image, fee, rid))
        self.db.commit()

    def undo_out(self, rid):
        """Hủy lượt ra (bấm nhầm thẻ). Ảnh ra được giữ lại, đổi tên thêm đuôi _HUY."""
        rec = self.get(rid)
        if rec is None or rec["gio_ra"] is None:
            return
        path = self.abs_path(rec["anh_ra"])
        if path is not None and path.exists():
            path.rename(path.with_name(f"{path.stem}_HUY{path.suffix}"))
        self.db.execute("UPDATE luot_gui SET gio_ra = NULL, anh_ra = NULL, tien = NULL WHERE id = ?", (rid,))
        self.db.commit()

    # ----- đọc -----
    def get(self, rid):
        return self.db.execute("SELECT * FROM luot_gui WHERE id = ?", (rid,)).fetchone()

    def parked(self, card):
        """Lượt gửi chưa ra của thẻ này (None nếu thẻ đang trống)."""
        return self.db.execute(
            "SELECT * FROM luot_gui WHERE so_the = ? AND gio_ra IS NULL ORDER BY id DESC LIMIT 1", (card,)
        ).fetchone()

    def list_parked(self, card=""):
        sql, params = "SELECT * FROM luot_gui WHERE gio_ra IS NULL", []
        if card:
            sql += " AND instr(so_the, ?) > 0"
            params.append(card)
        return self.db.execute(sql + " ORDER BY gio_vao", params).fetchall()

    def search(self, card="", day_from=None, day_to=None, status="all", limit=5000):
        """Tìm lượt gửi theo số thẻ (một phần), khoảng ngày (vào hoặc ra trong khoảng) và trạng thái."""
        sql, params = "SELECT * FROM luot_gui WHERE 1 = 1", []
        if card:
            sql += " AND instr(so_the, ?) > 0"
            params.append(card)
        if day_from and day_to:
            a, b = day_from.isoformat(), day_to.isoformat()
            sql += " AND (substr(gio_vao, 1, 10) BETWEEN ? AND ? OR substr(gio_ra, 1, 10) BETWEEN ? AND ?)"
            params += [a, b, a, b]
        if status == "in":
            sql += " AND gio_ra IS NULL"
        elif status == "out":
            sql += " AND gio_ra IS NOT NULL"
        sql += " ORDER BY gio_vao DESC LIMIT ?"
        params.append(limit)
        return self.db.execute(sql, params).fetchall()

    def day_records(self, day):
        """
        Các lượt có xe trong bãi vào ngày day: vào trong ngày, ra trong ngày, hoặc gửi từ hôm trước sang.
        Xe đang gửi hiện ở mọi ngày từ ngày vào đến hôm nay; xe đã ra thì chỉ hiện đến ngày ra.
        """
        if day > datetime.now().date():
            return []
        d = day.isoformat()
        return self.db.execute(
            "SELECT * FROM luot_gui WHERE substr(gio_vao, 1, 10) <= ? AND (gio_ra IS NULL OR substr(gio_ra, 1, 10) >= ?)"
            " ORDER BY gio_vao", (d, d)).fetchall()

    def recent_events(self, limit=40):
        return self.db.execute("""
            SELECT id, so_the, gio_vao AS thoi_gian, 'IN' AS loai FROM luot_gui
            UNION ALL
            SELECT id, so_the, gio_ra, 'OUT' FROM luot_gui WHERE gio_ra IS NOT NULL
            ORDER BY thoi_gian DESC LIMIT ?
        """, (limit,)).fetchall()

    def stats(self):
        today = datetime.now().strftime("%Y-%m-%d")
        one = lambda sql, *p: self.db.execute(sql, p).fetchone()[0]
        return {
            "parked": one("SELECT COUNT(*) FROM luot_gui WHERE gio_ra IS NULL"),
            "in": one("SELECT COUNT(*) FROM luot_gui WHERE substr(gio_vao, 1, 10) = ?", today),
            "out": one("SELECT COUNT(*) FROM luot_gui WHERE substr(gio_ra, 1, 10) = ?", today),
        }

    def export_csv(self, rows, fee_of=None, name="lich_su"):
        """
        Xuất danh sách lượt gửi ra file CSV (mở được bằng Excel). Trả về đường dẫn file.
        fee_of : hàm nhận 1 lượt, trả về (tiền, tạm tính hay không) để ghi cột Tiền gửi
        """
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path = self.export_dir / f"{name}_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Số thẻ", "Giờ vào", "Giờ ra", "Thời gian gửi", "Trạng thái", "Tiền gửi (đ)",
                             "Ảnh vào", "Ảnh ra"])
            for r in rows:
                fee = ""
                if fee_of is not None:
                    amount, estimate = fee_of(r)
                    fee = f"{amount} (tạm tính)" if estimate else amount
                writer.writerow([r["so_the"], r["gio_vao"], r["gio_ra"] or "", record_duration(r),
                                 "Đang gửi" if r["gio_ra"] is None else "Đã ra", fee,
                                 Path(r["anh_vao"]).name if r["anh_vao"] else "",
                                 Path(r["anh_ra"]).name if r["anh_ra"] else ""])
        return path
