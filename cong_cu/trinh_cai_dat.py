"""
Bộ cài đặt Quản Lý Nhà Xe - VIDATEX JSC.

Chạy bình thường          : cài đặt (chọn thư mục, tạo shortcut, ghi vào Apps & features).
Chạy với tham số /gocai   : gỡ cài đặt (chính file này được chép vào thư mục cài làm trình gỡ).

Không cần Python trên máy đích: QuanLyNhaXe.exe đã gói sẵn mọi thứ bên trong.
"""

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

APP_NAME = "Quản Lý Nhà Xe"
COMPANY = "VIDATEX JSC"
VERSION = "1.1.1"
EXE_NAME = "QuanLyNhaXe.exe"
VOICE_DIR = "giong_doc"
UNINSTALLER = "GoCaiDat.exe"
SHORTCUT = "Quan Ly Nha Xe"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\QuanLyNhaXe"
FACEBOOK = "https://www.facebook.com/MEGAPLASTORR"
DEFAULT_DIR = r"C:\QuanLyNhaXe"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

C = {"bg": "#eef2f7", "surface": "#ffffff", "surface2": "#f4f6fa", "border": "#e2e8f0",
     "text": "#0f172a", "text2": "#334155", "muted": "#64748b", "accent": "#256fa6",
     "accent_hover": "#1c5785", "accent_soft": "#e2eef8", "navy": "#0d2f54", "teal": "#1f9fb3",
     "ok": "#15803d", "ok_soft": "#dcfce7", "danger": "#dc2626"}
FONT = "Segoe UI"


def font(size, bold=False):
    return ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal")


def resource(name):
    """File nằm trong gói exe (logo, biểu tượng, file chương trình)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _shell_folder(ten, du_phong):
    """
    Hỏi Windows xem thư mục thật nằm đâu. Nhiều máy chuyển Desktop sang OneDrive
    (vd C:\\Users\\...\\OneDrive\\Máy tính) nên không ghép đường dẫn bằng tay được.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            duong_dan = Path(winreg.QueryValueEx(key, ten)[0])
            if duong_dan.is_dir():
                return duong_dan
    except OSError:
        pass
    return du_phong


def start_menu_dir():
    return _shell_folder("Programs",
                         Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs")


def desktop_dir():
    return _shell_folder("Desktop", Path(os.environ["USERPROFILE"]) / "Desktop")


def make_shortcut(link, target, work_dir, note):
    """Tạo shortcut .lnk bằng WScript.Shell của Windows."""
    lenh = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
            f"$s.TargetPath='{target}';$s.WorkingDirectory='{work_dir}';"
            f"$s.IconLocation='{target},0';$s.Description='{note}';$s.Save()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", lenh],
                       check=True, timeout=30, creationflags=NO_WINDOW)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def app_dang_chay():
    try:
        out = subprocess.run(["tasklist", "/fi", f"imagename eq {EXE_NAME}"], capture_output=True,
                             text=True, timeout=20, creationflags=NO_WINDOW).stdout
        return EXE_NAME.lower() in out.lower()
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------- cài đặt / gỡ ----------------
def cai_dat(dich, them_desktop, bao):
    """Chép chương trình vào thư mục đích, tạo shortcut và ghi vào danh sách gỡ cài đặt."""
    dich = Path(dich)
    bao(0.1, "Đang tạo thư mục...")
    dich.mkdir(parents=True, exist_ok=True)

    bao(0.3, "Đang chép chương trình...")
    shutil.copy2(resource(EXE_NAME), dich / EXE_NAME)
    giong = resource(VOICE_DIR)
    if giong.is_dir():  # giọng đọc Tiếng Việt chạy không cần mạng (Piper)
        bao(0.45, "Đang chép giọng đọc...")
        shutil.copytree(giong, dich / VOICE_DIR, dirs_exist_ok=True)

    bao(0.6, "Đang tạo trình gỡ cài đặt...")
    # trình gỡ là file riêng gọn nhẹ nằm sẵn trong bộ cài; chạy từ mã nguồn thì chép chính file này
    nguon_go = resource(UNINSTALLER)
    shutil.copy2(nguon_go if nguon_go.exists() else Path(__file__), dich / UNINSTALLER)

    bao(0.75, "Đang tạo biểu tượng...")
    dich_exe = dich / EXE_NAME
    make_shortcut(start_menu_dir() / f"{SHORTCUT}.lnk", dich_exe, dich, f"{APP_NAME} - {COMPANY}")
    if them_desktop:
        make_shortcut(desktop_dir() / f"{SHORTCUT}.lnk", dich_exe, dich, f"{APP_NAME} - {COMPANY}")

    bao(0.9, "Đang ghi thông tin...")
    co = dich_exe.stat().st_size // 1024
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
        for ten, gia_tri in (("DisplayName", f"{APP_NAME} - {COMPANY}"), ("DisplayVersion", VERSION),
                             ("Publisher", COMPANY), ("DisplayIcon", str(dich_exe)),
                             ("InstallLocation", str(dich)),
                             ("UninstallString", f'"{dich / UNINSTALLER}" /gocai')):
            winreg.SetValueEx(key, ten, 0, winreg.REG_SZ, gia_tri)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, co)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    bao(1.0, "Xong!")
    return dich_exe


def go_cai_dat(xoa_du_lieu):
    """Gỡ chương trình. Thư mục data được giữ lại trừ khi người dùng chọn xóa."""
    dich = Path(sys.executable).resolve().parent
    for link in (start_menu_dir() / f"{SHORTCUT}.lnk", desktop_dir() / f"{SHORTCUT}.lnk"):
        link.unlink(missing_ok=True)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    except OSError:
        pass
    (dich / EXE_NAME).unlink(missing_ok=True)
    shutil.rmtree(dich / VOICE_DIR, ignore_errors=True)
    if xoa_du_lieu:
        shutil.rmtree(dich / "data", ignore_errors=True)
        (dich / "config.ini").unlink(missing_ok=True)
    # File đang chạy thì Windows khóa, không tự xóa được. Viết một file bat chờ trình gỡ
    # thoát hẳn rồi mới xóa, cuối cùng tự xóa chính nó.
    # rmdir chỉ ăn khi thư mục đã rỗng, nên thư mục data (nếu giữ lại) vẫn còn nguyên.
    don_dep = Path(os.environ["TEMP"]) / "don_dep_quanlynhaxe.bat"
    don_dep.write_text(
        "@echo off\r\n"
        ":doi\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        f'del /q "{dich / UNINSTALLER}" 2>nul\r\n'
        f'if exist "{dich / UNINSTALLER}" goto doi\r\n'
        f'rmdir "{dich}" 2>nul\r\n'
        'del /q "%~f0"\r\n', encoding="utf-8")
    subprocess.Popen(["cmd", "/c", str(don_dep)], creationflags=NO_WINDOW)


# ---------------- giao diện ----------------
class Installer(ctk.CTk):
    def __init__(self, che_do_go=False):
        super().__init__(fg_color=C["bg"])
        self.che_do_go = che_do_go
        self.title(f"Gỡ cài đặt {APP_NAME}" if che_do_go else f"Cài đặt {APP_NAME}")
        icon = resource("app.ico")
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self._banner()
        self.than = ctk.CTkFrame(self, fg_color="transparent")
        self.than.grid(row=1, column=0, sticky="nsew", padx=30, pady=(18, 0))
        self.chan = ctk.CTkFrame(self, fg_color="transparent")
        self.chan.grid(row=2, column=0, sticky="ew", padx=30, pady=20)
        self.grid_rowconfigure(1, weight=1)
        self.trang_go() if che_do_go else self.trang_dau()
        self._dat_giua(660, 430 if che_do_go else 540)

    def _dat_giua(self, rong, cao):
        """Cỡ cố định cho mọi trang, đặt giữa màn hình (tính theo pixel thật, không qua CustomTkinter)."""
        self.update_idletasks()
        he_so = self.winfo_fpixels("1i") / 96
        w = max(int(rong * he_so), self.winfo_reqwidth())
        h = max(int(cao * he_so), self.winfo_reqheight())
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        self.tk.call("wm", "geometry", self._w, f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def _banner(self):
        top = ctk.CTkFrame(self, fg_color=C["navy"], corner_radius=0, height=96)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        logo = resource("logo_mark.png")
        if logo.exists():
            with Image.open(logo) as im:
                anh = ctk.CTkImage(light_image=im.convert("RGBA"), size=(56, 56))
            ctk.CTkLabel(top, text="", image=anh).pack(side="left", padx=(26, 16), pady=20)
        ten = ctk.CTkFrame(top, fg_color="transparent")
        ten.pack(side="left", pady=20)
        ctk.CTkLabel(ten, text=COMPANY, font=font(11, True), text_color=C["teal"], height=16).pack(anchor="w")
        ctk.CTkLabel(ten, text=APP_NAME, font=font(22, True), text_color="white", height=30).pack(anchor="w")
        ctk.CTkLabel(top, text=f"Phiên bản {VERSION}", font=font(12), text_color="#cbd5e1").pack(
            side="right", padx=26)

    def _xoa_than(self):
        for w in self.than.winfo_children():
            w.destroy()
        for w in self.chan.winfo_children():
            w.destroy()

    def _nut_chinh(self, text, lenh):
        return ctk.CTkButton(self.chan, text=text, command=lenh, width=180, height=46, corner_radius=10,
                             font=font(15, True), fg_color=C["accent"], hover_color=C["accent_hover"])

    def _nut_phu(self, text, lenh):
        return ctk.CTkButton(self.chan, text=text, command=lenh, width=130, height=46, corner_radius=10,
                             font=font(14, True), fg_color=C["surface2"], hover_color=C["border"],
                             text_color=C["text2"], border_width=1, border_color=C["border"])

    # ----- trang 1: chọn thư mục -----
    def trang_dau(self):
        self._xoa_than()
        ctk.CTkLabel(self.than, text="Chào mừng bạn cài đặt phần mềm", font=font(19, True),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(self.than, text="Phần mềm ghi nhận xe vào / ra bằng camera và thẻ giữ xe đánh số.\n"
                                     "Máy không cần cài Python hay thư viện gì thêm.",
                     font=font(13), text_color=C["muted"], justify="left").pack(anchor="w", pady=(6, 18))

        hop = ctk.CTkFrame(self.than, fg_color=C["surface"], corner_radius=14, border_width=1,
                           border_color=C["border"])
        hop.pack(fill="x")
        ctk.CTkLabel(hop, text="CÀI VÀO THƯ MỤC", font=font(11, True), text_color=C["muted"]).pack(
            anchor="w", padx=20, pady=(16, 4))
        dong = ctk.CTkFrame(hop, fg_color="transparent")
        dong.pack(fill="x", padx=20, pady=(0, 6))
        self.o_duong_dan = ctk.CTkEntry(dong, height=42, corner_radius=10, font=font(14),
                                        fg_color=C["surface2"], border_color=C["border"],
                                        text_color=C["text"])
        self.o_duong_dan.insert(0, DEFAULT_DIR)
        self.o_duong_dan.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dong, text="Chọn...", command=self.chon_thu_muc, width=100, height=42,
                      corner_radius=10, font=font(13, True), fg_color=C["surface2"],
                      hover_color=C["border"], text_color=C["text2"], border_width=1,
                      border_color=C["border"]).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(hop, text="Cài đặt và dữ liệu xe sẽ nằm trong thư mục này. Nên chọn ổ còn nhiều chỗ trống.",
                     font=font(12), text_color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 10))
        self.desktop = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(hop, text="Tạo biểu tượng ngoài màn hình Desktop", variable=self.desktop,
                        font=font(13), text_color=C["text2"], corner_radius=6, fg_color=C["accent"],
                        hover_color=C["accent_hover"], border_color="#cbd5e1").pack(
            anchor="w", padx=20, pady=(0, 18))

        self.loi = ctk.CTkLabel(self.than, text="", font=font(13, True), text_color=C["danger"])
        self.loi.pack(anchor="w", pady=(10, 0))
        self._nut_chinh("Cài đặt", self.bat_dau).pack(side="right")
        self._nut_phu("Thoát", self.destroy).pack(side="right", padx=10)

    def chon_thu_muc(self):
        chon = filedialog.askdirectory(title="Chọn thư mục cài đặt", parent=self)
        if chon:
            self.o_duong_dan.delete(0, "end")
            self.o_duong_dan.insert(0, str(Path(chon)))

    def bat_dau(self):
        dich = self.o_duong_dan.get().strip()
        if not dich:
            self.loi.configure(text="Chưa chọn thư mục cài đặt")
            return
        if app_dang_chay():
            self.loi.configure(text="Phần mềm đang chạy — hãy tắt nó rồi cài lại")
            return
        try:
            Path(dich).mkdir(parents=True, exist_ok=True)
            thu = Path(dich) / ".thu_ghi"
            thu.write_text("x", encoding="utf-8")
            thu.unlink()
        except OSError as loi:
            self.loi.configure(text=f"Không ghi được vào thư mục này: {loi.strerror or loi}")
            return
        self.trang_dang_cai(dich)

    # ----- trang 2: đang cài -----
    def trang_dang_cai(self, dich):
        self._xoa_than()
        ctk.CTkLabel(self.than, text="Đang cài đặt...", font=font(19, True),
                     text_color=C["text"]).pack(anchor="w")
        self.nhan = ctk.CTkLabel(self.than, text="", font=font(13), text_color=C["muted"])
        self.nhan.pack(anchor="w", pady=(8, 16))
        self.thanh = ctk.CTkProgressBar(self.than, height=14, corner_radius=7,
                                        progress_color=C["accent"], fg_color=C["surface2"])
        self.thanh.set(0)
        self.thanh.pack(fill="x")
        self.after(200, lambda: self.chay_cai(dich))

    def chay_cai(self, dich):
        def bao(phan, chu):
            self.thanh.set(phan)
            self.nhan.configure(text=chu)
            self.update()

        try:
            exe = cai_dat(dich, self.desktop.get(), bao)
        except Exception as loi:
            messagebox.showerror("Cài đặt thất bại", f"Không cài được:\n{loi}", parent=self)
            self.trang_dau()
            return
        self.after(400, lambda: self.trang_xong(exe))

    # ----- trang 3: xong -----
    def trang_xong(self, exe):
        self._xoa_than()
        ctk.CTkLabel(self.than, text="✓", width=54, height=54, corner_radius=27, fg_color=C["ok_soft"],
                     text_color=C["ok"], font=font(28, True)).pack(anchor="w")
        ctk.CTkLabel(self.than, text="Cài đặt hoàn tất", font=font(21, True),
                     text_color=C["text"]).pack(anchor="w", pady=(12, 4))
        ctk.CTkLabel(self.than, text=f"{APP_NAME} đã được cài vào:\n{exe.parent}", font=font(13),
                     text_color=C["muted"], justify="left", anchor="w", wraplength=580).pack(
            anchor="w", fill="x")

        hop = ctk.CTkFrame(self.than, fg_color=C["surface"], corner_radius=14, border_width=1,
                           border_color=C["border"])
        hop.pack(fill="x", pady=(20, 0))
        self.chay_ngay = ctk.BooleanVar(value=True)
        self.xem_tac_gia = ctk.BooleanVar(value=True)   # luôn tích sẵn
        for bien, chu in ((self.chay_ngay, f"Chạy {APP_NAME} ngay bây giờ"),
                          (self.xem_tac_gia, "Xem thông tin người tạo phần mềm")):
            ctk.CTkCheckBox(hop, text=chu, variable=bien, font=font(14), text_color=C["text2"],
                            corner_radius=6, fg_color=C["accent"], hover_color=C["accent_hover"],
                            border_color="#cbd5e1").pack(anchor="w", padx=20, pady=12)
        self.exe = exe
        self._nut_chinh("Hoàn tất", self.ket_thuc).pack(side="right")

    def ket_thuc(self):
        if self.xem_tac_gia.get():
            os.startfile(FACEBOOK)
        if self.chay_ngay.get():
            os.startfile(str(self.exe))
        self.destroy()

    # ----- gỡ cài đặt -----
    def trang_go(self):
        self._xoa_than()
        dich = Path(sys.executable).resolve().parent
        ctk.CTkLabel(self.than, text="Gỡ cài đặt phần mềm", font=font(19, True),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(self.than, text=f"Sẽ gỡ {APP_NAME} khỏi:\n{dich}", font=font(13),
                     text_color=C["muted"], justify="left", anchor="w", wraplength=580).pack(
            anchor="w", fill="x", pady=(8, 18))
        hop = ctk.CTkFrame(self.than, fg_color=C["surface"], corner_radius=14, border_width=1,
                           border_color=C["border"])
        hop.pack(fill="x")
        self.xoa_du_lieu = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(hop, text="Xóa luôn dữ liệu xe và ảnh đã lưu (không khôi phục được)",
                        variable=self.xoa_du_lieu, font=font(13), text_color=C["text2"], corner_radius=6,
                        fg_color=C["danger"], hover_color="#b91c1c", border_color="#cbd5e1").pack(
            anchor="w", padx=20, pady=16)
        ctk.CTkLabel(self.than, text="Không tích ô trên thì thư mục data và config.ini được giữ lại.",
                     font=font(12), text_color=C["muted"]).pack(anchor="w", pady=(12, 0))
        ctk.CTkButton(self.chan, text="Gỡ cài đặt", command=self.lam_go, width=180, height=46,
                      corner_radius=10, font=font(15, True), fg_color=C["danger"],
                      hover_color="#b91c1c").pack(side="right")
        self._nut_phu("Thoát", self.destroy).pack(side="right", padx=10)

    def lam_go(self):
        if app_dang_chay():
            messagebox.showwarning("Đang chạy", "Hãy tắt phần mềm rồi gỡ lại.", parent=self)
            return
        go_cai_dat(self.xoa_du_lieu.get())
        messagebox.showinfo("Đã gỡ", f"Đã gỡ {APP_NAME} khỏi máy.", parent=self)
        self.destroy()


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    Installer(che_do_go="/gocai" in [a.lower() for a in sys.argv[1:]]).mainloop()


if __name__ == "__main__":
    main()
