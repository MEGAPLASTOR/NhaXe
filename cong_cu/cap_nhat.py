"""
Bản cập nhật Quản Lý Nhà Xe - VIDATEX JSC.

Dùng cho máy đang chạy bản cũ: tự tìm thư mục đã cài, đóng phần mềm nếu đang mở, thay chương trình mới
(kèm giọng đọc và trình gỡ cài đặt), GIỮ NGUYÊN thư mục data (xe, ảnh, tiền) và config.ini
(mật khẩu, camera, giá...). Webhook / bot Discord mặc định nằm sẵn trong chương trình mới.
Trước khi thay, config.ini được sao lưu vào data/sao_luu/truoc_cap_nhat_<ngày giờ>/.

Dùng chung giao diện và các hàm với bộ cài (trinh_cai_dat.py).
"""

import os
import shutil
import subprocess
import time
import winreg
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from trinh_cai_dat import (APP_NAME, C, DEFAULT_DIR, EXE_NAME, NO_WINDOW, REG_KEY, UNINSTALLER, VERSION, VOICE_DIR,
                           Installer, font, resource)

CLOSE_WAIT = 12      # giây chờ phần mềm tự đóng trước khi buộc tắt
COPY_RETRY = 20      # file exe vừa đóng có thể còn bị Windows giữ vài giây


def _ps(command, timeout=30):
    try:
        return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                              capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def dang_chay_trong(thu_muc):
    """[(pid, đường dẫn exe)] các tiến trình QuanLyNhaXe.exe nằm trong thư mục này."""
    out = _ps(f"Get-Process {Path(EXE_NAME).stem} -ErrorAction SilentlyContinue | "
              "ForEach-Object { \"$($_.Id)|$($_.Path)\" }")
    goc = str(Path(thu_muc).resolve()).lower()
    ket_qua = []
    for dong in out.splitlines():
        pid, _, duong_dan = dong.strip().partition("|")
        if pid.isdigit() and duong_dan and str(Path(duong_dan).resolve().parent).lower() == goc:
            ket_qua.append((int(pid), duong_dan))
    return ket_qua


def tat_cac_ban_dang_chay():
    """Thư mục của các bản QuanLyNhaXe.exe đang chạy (để tìm ra chỗ cài)."""
    out = _ps(f"Get-Process {Path(EXE_NAME).stem} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Path }}")
    return [Path(p.strip()).parent for p in out.splitlines() if p.strip()]


def phien_ban_cua(exe):
    out = _ps(f"(Get-Item -LiteralPath '{exe}').VersionInfo.ProductVersion")
    return out.strip() or "không rõ"


def doc_dang_ky():
    """(thư mục cài, phiên bản) ghi trong Apps & features, hoặc (None, None)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
            return Path(winreg.QueryValueEx(key, "InstallLocation")[0]), winreg.QueryValueEx(key, "DisplayVersion")[0]
    except OSError:
        return None, None


def tim_cho_cai():
    """Đoán thư mục đang cài: Apps & features -> bản đang chạy -> thư mục mặc định."""
    noi_dang_ky, _ = doc_dang_ky()
    ung_vien = [noi_dang_ky, *tat_cac_ban_dang_chay(), Path(DEFAULT_DIR)]
    for thu_muc in ung_vien:
        if thu_muc and (thu_muc / EXE_NAME).is_file():
            return thu_muc
    return None


def dong_phan_mem(thu_muc, bao=lambda chu: None):
    """Đóng phần mềm đang chạy trong thư mục này: nhờ tự đóng (lưu dữ liệu, tắt camera) rồi mới buộc tắt."""
    pids = [pid for pid, _ in dang_chay_trong(thu_muc)]
    if not pids:
        return True
    bao("Đang đóng phần mềm...")
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
    het_han = time.monotonic() + CLOSE_WAIT
    while time.monotonic() < het_han:
        if not dang_chay_trong(thu_muc):
            return True
        time.sleep(0.5)
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
    time.sleep(1)
    return not dang_chay_trong(thu_muc)


def _chep_lai(nguon, dich):
    """Chép đè, thử lại vài lần nếu file còn bị khóa."""
    for lan in range(COPY_RETRY):
        try:
            shutil.copy2(nguon, dich)
            return
        except PermissionError:
            if lan == COPY_RETRY - 1:
                raise
            time.sleep(0.5)


def cap_nhat(thu_muc, bao):
    """Thay chương trình trong thư mục đã cài, giữ nguyên data và config.ini. Trả về đường dẫn exe."""
    thu_muc = Path(thu_muc)
    exe = thu_muc / EXE_NAME
    bao(0.1, "Đang sao lưu cài đặt...")
    if (thu_muc / "config.ini").is_file():
        sao_luu = thu_muc / "data" / "sao_luu" / f"truoc_cap_nhat_{datetime.now():%d-%m-%Y_%Hh%Mm%S}"
        sao_luu.mkdir(parents=True, exist_ok=True)
        shutil.copy2(thu_muc / "config.ini", sao_luu / "config.ini")

    bao(0.25, "Đang thay chương trình...")
    # chép ra file tạm rồi đổi tên: lỡ hỏng giữa chừng thì bản cũ vẫn còn
    tam = thu_muc / (EXE_NAME + ".moi")
    _chep_lai(resource(EXE_NAME), tam)
    for lan in range(COPY_RETRY):
        try:
            os.replace(tam, exe)
            break
        except PermissionError:
            if lan == COPY_RETRY - 1:
                raise
            time.sleep(0.5)

    giong = resource(VOICE_DIR)
    if giong.is_dir():
        bao(0.5, "Đang chép giọng đọc...")
        shutil.copytree(giong, thu_muc / VOICE_DIR, dirs_exist_ok=True)

    bao(0.8, "Đang cập nhật trình gỡ cài đặt...")
    go = resource(UNINSTALLER)
    if go.is_file():
        _chep_lai(go, thu_muc / UNINSTALLER)

    # chỉ sửa Apps & features nếu đúng là bản cài ở thư mục này (bản chạy thẳng thì không đụng tới)
    noi_dang_ky, _ = doc_dang_ky()
    if noi_dang_ky and noi_dang_ky.resolve() == thu_muc.resolve():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
                winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, exe.stat().st_size // 1024)
        except OSError:
            pass
    bao(1.0, "Xong!")
    return exe


class Updater(Installer):
    """Cửa sổ cập nhật: dùng lại khung, màu, nút của bộ cài, chỉ thay các trang."""

    def __init__(self):
        super().__init__()
        self.title(f"Cập nhật {APP_NAME}")

    # ----- trang 1: tìm chỗ cài -----
    def trang_dau(self):
        self._xoa_than()
        ctk.CTkLabel(self.than, text=f"Cập nhật lên phiên bản {VERSION}", font=font(19, True),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(self.than, text="Thay chương trình mới, GIỮ NGUYÊN dữ liệu xe, ảnh, tiền và cài đặt\n"
                                     "(mật khẩu, camera, giá gửi xe). Không cần gỡ bản cũ.",
                     font=font(13), text_color=C["muted"], justify="left").pack(anchor="w", pady=(6, 18))

        hop = ctk.CTkFrame(self.than, fg_color=C["surface"], corner_radius=14, border_width=1,
                           border_color=C["border"])
        hop.pack(fill="x")
        ctk.CTkLabel(hop, text="THƯ MỤC ĐANG CÀI PHẦN MỀM", font=font(11, True), text_color=C["muted"]).pack(
            anchor="w", padx=20, pady=(16, 4))
        dong = ctk.CTkFrame(hop, fg_color="transparent")
        dong.pack(fill="x", padx=20, pady=(0, 6))
        self.o_duong_dan = ctk.CTkEntry(dong, height=42, corner_radius=10, font=font(14),
                                        fg_color=C["surface2"], border_color=C["border"], text_color=C["text"])
        self.o_duong_dan.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dong, text="Chọn...", command=self.chon_thu_muc, width=100, height=42,
                      corner_radius=10, font=font(13, True), fg_color=C["surface2"],
                      hover_color=C["border"], text_color=C["text2"], border_width=1,
                      border_color=C["border"]).pack(side="left", padx=(10, 0))
        self.thong_tin = ctk.CTkLabel(hop, text="Đang tìm phần mềm trên máy...", font=font(12),
                                      text_color=C["muted"], justify="left")
        self.thong_tin.pack(anchor="w", padx=20, pady=(0, 16))

        self.loi = ctk.CTkLabel(self.than, text="", font=font(13, True), text_color=C["danger"],
                                justify="left", wraplength=580)
        self.loi.pack(anchor="w", pady=(10, 0))
        self._nut_chinh("Cập nhật", self.bat_dau).pack(side="right")
        self._nut_phu("Thoát", self.destroy).pack(side="right", padx=10)
        self.after(150, self._tu_tim)

    def _tu_tim(self):
        thu_muc = tim_cho_cai()
        if thu_muc is None:
            self.thong_tin.configure(text="Không tự tìm thấy phần mềm — bấm Chọn... và trỏ tới thư mục\n"
                                          f"có file {EXE_NAME}.", text_color=C["danger"])
            return
        self.o_duong_dan.delete(0, "end")
        self.o_duong_dan.insert(0, str(thu_muc))
        self._hien_thong_tin(thu_muc)

    def _hien_thong_tin(self, thu_muc):
        exe = Path(thu_muc) / EXE_NAME
        if not exe.is_file():
            self.thong_tin.configure(text=f"Thư mục này không có {EXE_NAME}.", text_color=C["danger"])
            return
        chay = " · đang mở (sẽ được đóng để cập nhật)" if dang_chay_trong(thu_muc) else ""
        self.thong_tin.configure(text=f"Đã tìm thấy: phiên bản hiện tại {phien_ban_cua(exe)} → {VERSION}{chay}",
                                 text_color=C["ok"])

    def chon_thu_muc(self):
        chon = filedialog.askdirectory(title="Chọn thư mục đang cài phần mềm", parent=self)
        if chon:
            self.o_duong_dan.delete(0, "end")
            self.o_duong_dan.insert(0, str(Path(chon)))
            self._hien_thong_tin(Path(chon))

    def bat_dau(self):
        thu_muc = Path(self.o_duong_dan.get().strip() or ".")
        if not (thu_muc / EXE_NAME).is_file():
            self.loi.configure(text=f"Thư mục này không có {EXE_NAME}. Bấm Chọn... để chỉ đúng chỗ đã cài.")
            return
        if dang_chay_trong(thu_muc):
            if not messagebox.askyesno("Phần mềm đang mở",
                                       f"{APP_NAME} đang mở. Đóng phần mềm để cập nhật?\n"
                                       "Dữ liệu đã ghi nhận không bị mất.", parent=self):
                return
            self.loi.configure(text="Đang đóng phần mềm...", text_color=C["muted"])
            self.update()
            if not dong_phan_mem(thu_muc):
                self.loi.configure(text="Không đóng được phần mềm — hãy tự tắt nó rồi bấm Cập nhật lại.",
                                   text_color=C["danger"])
                return
        try:
            thu = thu_muc / ".thu_ghi"
            thu.write_text("x", encoding="utf-8")
            thu.unlink()
        except OSError as loi:
            self.loi.configure(text=f"Không ghi được vào thư mục này: {loi.strerror or loi}", text_color=C["danger"])
            return
        self.trang_dang_cap_nhat(thu_muc)

    # ----- trang 2: đang cập nhật -----
    def trang_dang_cap_nhat(self, thu_muc):
        self._xoa_than()
        ctk.CTkLabel(self.than, text="Đang cập nhật...", font=font(19, True), text_color=C["text"]).pack(anchor="w")
        self.nhan = ctk.CTkLabel(self.than, text="", font=font(13), text_color=C["muted"])
        self.nhan.pack(anchor="w", pady=(8, 16))
        self.thanh = ctk.CTkProgressBar(self.than, height=14, corner_radius=7,
                                        progress_color=C["accent"], fg_color=C["surface2"])
        self.thanh.set(0)
        self.thanh.pack(fill="x")
        self.after(200, lambda: self.chay_cap_nhat(thu_muc))

    def chay_cap_nhat(self, thu_muc):
        def bao(phan, chu):
            self.thanh.set(phan)
            self.nhan.configure(text=chu)
            self.update()

        try:
            exe = cap_nhat(thu_muc, bao)
        except Exception as loi:
            messagebox.showerror("Cập nhật thất bại", f"Không cập nhật được:\n{loi}\n\nBản cũ vẫn dùng được.",
                                 parent=self)
            self.trang_dau()
            return
        self.after(400, lambda: self.trang_xong_cap_nhat(exe))

    # ----- trang 3: xong -----
    def trang_xong_cap_nhat(self, exe):
        self._xoa_than()
        ctk.CTkLabel(self.than, text="✓", width=54, height=54, corner_radius=27, fg_color=C["ok_soft"],
                     text_color=C["ok"], font=font(28, True)).pack(anchor="w")
        ctk.CTkLabel(self.than, text=f"Đã cập nhật lên phiên bản {VERSION}", font=font(21, True),
                     text_color=C["text"]).pack(anchor="w", pady=(12, 4))
        ctk.CTkLabel(self.than, text=f"Dữ liệu xe, ảnh và cài đặt được giữ nguyên.\nThư mục: {exe.parent}",
                     font=font(13), text_color=C["muted"], justify="left", anchor="w", wraplength=580).pack(
            anchor="w", fill="x")
        hop = ctk.CTkFrame(self.than, fg_color=C["surface"], corner_radius=14, border_width=1,
                           border_color=C["border"])
        hop.pack(fill="x", pady=(20, 0))
        self.chay_ngay = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(hop, text=f"Mở {APP_NAME} ngay bây giờ", variable=self.chay_ngay, font=font(14),
                        text_color=C["text2"], corner_radius=6, fg_color=C["accent"], hover_color=C["accent_hover"],
                        border_color="#cbd5e1").pack(anchor="w", padx=20, pady=12)
        self.exe = exe
        self._nut_chinh("Hoàn tất", self.ket_thuc_cap_nhat).pack(side="right")

    def ket_thuc_cap_nhat(self):
        if self.chay_ngay.get():
            subprocess.Popen([str(self.exe)], cwd=str(self.exe.parent))
        self.destroy()


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    Updater().mainloop()


if __name__ == "__main__":
    main()
