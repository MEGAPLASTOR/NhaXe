"""
Đọc lời chào khi xe vào / ra. Có 3 nguồn giọng Tiếng Việt, thử lần lượt:

1. Edge  : giọng của Microsoft Edge (thư viện edge-tts), rất tự nhiên nhưng cần mạng, tạo 1 câu mất vài giây.
2. Piper : chương trình đọc chạy trong máy (thư mục giong_doc), không cần mạng, tạo 1 câu khoảng 1 giây.
3. Windows: giọng Microsoft An của Windows (SAPI) nếu máy cài được.

Câu Edge / Piper đã tạo được lưu thành file trong data/am_thanh nên lần sau phát ngay.
Chọn Edge mà câu chưa có sẵn thì Piper đọc trước cho nhanh, Edge tải ngầm để những lần sau dùng giọng Edge.
"""

import asyncio
import base64
import ctypes
import hashlib
import importlib.util
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

AUTO_VOICE = ""  # để trống = tự chọn: Edge (có mạng) -> Piper -> giọng Windows Tiếng Việt
EDGE_VOICES = (("edge:vi-VN-HoaiMyNeural", "Nữ – HoaiMy (Edge, cần mạng)"),
               ("edge:vi-VN-NamMinhNeural", "Nam – NamMinh (Edge, cần mạng)"))
PIPER_VOICE = "piper"
PIPER_LABEL = "Piper (trong máy, không cần mạng)"
PIPER_MODEL = "vi_VN-vais1000-medium.onnx"
WIN_PREFIX = "win:"
EDGE_RETRY = 60          # giây: Edge vừa lỗi (mất mạng) thì chờ chừng này mới thử lại
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_SAY_IN = "Xin mời vào"
DEFAULT_SAY_OUT = "Phí gửi xe {tien}. Hẹn gặp lại"
PLACEHOLDERS = (("{the}", "số thẻ"), ("{tien}", "tiền gửi"), ("{thoi_gian}", "thời gian đã gửi"))

# SAPI có 2 kho giọng: Speech (giọng Desktop cũ) và Speech_OneCore (giọng mới, gồm cả Microsoft An tiếng Việt)
_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$v = New-Object -ComObject SAPI.SpVoice
$tokens = @{}
foreach ($p in 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices',
               'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices') {
  $c = New-Object -ComObject SAPI.SpObjectTokenCategory
  $c.SetId($p, $false)
  foreach ($t in $c.EnumerateTokens()) {
    $name = $t.GetDescription()
    if (-not $tokens.ContainsKey($name)) {
      $tokens[$name] = $t
      [Console]::Out.WriteLine('VOICE|' + $name + '|' + $t.GetAttribute('Language'))
    }
  }
}
[Console]::Out.WriteLine('END')
[Console]::Out.Flush()
function dec($s) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($s)) }
while (($line = [Console]::In.ReadLine()) -ne $null) {
  $parts = $line.Split('|')
  $name = dec $parts[0]
  if ($tokens.ContainsKey($name)) { $v.Voice = $tokens[$name] }
  $v.Volume = [int]$parts[2]
  [void]$v.Speak((dec $parts[1]), 3)   # 3 = đọc nền + cắt câu đang đọc dở
}
"""

# Gói giọng đọc Tiếng Việt là "tính năng tùy chọn" của Windows, cài bằng quyền quản trị.
# Kết quả trả về qua mã thoát: 0 = xong, 1 = tải / cài lỗi, 3 = Windows này không có gói.
_INSTALL_SCRIPT = r"""
$caps = Get-WindowsCapability -Online -Name 'Language.TextToSpeech~~~vi-VN~*'
if (-not $caps) { exit 3 }
try {
  foreach ($c in $caps) {
    if ($c.State -ne 'Installed') { Add-WindowsCapability -Online -Name $c.Name -ErrorAction Stop | Out-Null }
  }
  exit 0
} catch { exit 1 }
"""
# Chạy script trên bằng quyền quản trị (Windows hiện hộp hỏi quyền). Bấm Không thì Start-Process báo lỗi -> 2.
_ELEVATE_SCRIPT = r"""
try {
  $p = Start-Process powershell -Verb RunAs -WindowStyle Hidden -PassThru -Wait -ArgumentList `
       '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', '{payload}'
  exit $p.ExitCode
} catch { exit 2 }
"""
INSTALL_OK, INSTALL_FAILED, INSTALL_DENIED, INSTALL_MISSING = 0, 1, 2, 3


def _encode_ps(script):
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def install_vietnamese_voice():
    """Tải và cài giọng đọc Tiếng Việt của Windows. Chạy lâu (1-5 phút), gọi trong luồng riêng.
    Trả về 1 trong các mã INSTALL_*."""
    if sys.platform != "win32":
        return INSTALL_MISSING
    script = _ELEVATE_SCRIPT.replace("{payload}", _encode_ps(_INSTALL_SCRIPT))
    try:
        done = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                               "-EncodedCommand", _encode_ps(script)],
                              creationflags=_NO_WINDOW, timeout=1800,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return INSTALL_FAILED
    return done.returncode if done.returncode in (INSTALL_OK, INSTALL_DENIED, INSTALL_MISSING) else INSTALL_FAILED


_DIGITS = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")
_UNITS = ("", "nghìn", "triệu", "tỷ")


def _read_group(n, full):
    """Đọc 1 nhóm 3 chữ số. full=True: nhóm không đứng đầu nên phải đọc cả 'không trăm', 'linh'."""
    hundred, ten, unit = n // 100, n // 10 % 10, n % 10
    words = []
    if hundred or full:
        words += [_DIGITS[hundred], "trăm"]
    if ten == 0:
        if unit and words:
            words.append("linh")
    elif ten == 1:
        words.append("mười")
    else:
        words += [_DIGITS[ten], "mươi"]
    if unit:
        if unit == 1 and ten >= 2:
            words.append("mốt")
        elif unit == 5 and ten >= 1:
            words.append("lăm")
        else:
            words.append(_DIGITS[unit])
    return words


def number_words(n):
    """13500 -> 'mười ba nghìn năm trăm'"""
    n = int(n)
    if n == 0:
        return _DIGITS[0]
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words = []
    for i in range(len(groups) - 1, -1, -1):
        if groups[i] == 0:
            continue
        words += _read_group(groups[i], full=i < len(groups) - 1)
        words.append(_UNITS[min(i, 3)])
    return " ".join(w for w in words if w)


def money_words(amount):
    return f"{number_words(amount)} đồng"


def fill(template, card="", fee=None, duration=""):
    """Thay {the}, {tien}, {thoi_gian} trong lời đọc. Dùng replace để gõ sai dấu ngoặc cũng không lỗi."""
    text = template.replace("{the}", str(card)).replace("{thoi_gian}", duration)
    return text.replace("{tien}", money_words(fee) if fee is not None else "")


def is_vietnamese(voice):
    name, lang = voice
    return lang.lower().split(";")[0] == "42a" or "vietnam" in name.lower()


class _Sapi:
    """Giọng Windows: gửi câu cần đọc cho tiến trình PowerShell chạy nền."""

    def __init__(self):
        self.voices = []          # [(tên giọng, mã ngôn ngữ)]
        self.ready = threading.Event()
        self._proc = None
        self._lock = threading.Lock()
        if sys.platform == "win32":
            threading.Thread(target=self._start, daemon=True).start()
        else:
            self.ready.set()

    def _start(self):
        try:
            self._proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand",
                 _encode_ps(_SCRIPT)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=_NO_WINDOW, text=True, encoding="utf-8", errors="replace")
            for line in self._proc.stdout:
                line = line.strip()
                if line == "END":
                    break
                if line.startswith("VOICE|"):
                    _, name, lang = (line.split("|") + [""])[:3]
                    self.voices.append((name, lang))
        except (OSError, ValueError):
            self._proc = None
        finally:
            self.ready.set()

    def restart(self):
        """Khởi động lại để nạp danh sách giọng mới (vừa cài thêm giọng)."""
        self.stop()
        self._proc = None
        self.voices = []
        self.ready.clear()
        if sys.platform == "win32":
            threading.Thread(target=self._start, daemon=True).start()
        else:
            self.ready.set()

    def vietnamese_voice(self):
        return next((v[0] for v in self.voices if is_vietnamese(v)), None)

    def say(self, name, text, volume=100):
        if not self.ready.is_set() or self._proc is None or self._proc.poll() is not None:
            return False
        enc = lambda s: base64.b64encode(s.encode("utf-8")).decode("ascii")
        try:
            with self._lock:
                self._proc.stdin.write(f"{enc(name)}|{enc(text)}|{max(0, min(100, int(volume)))}\n")
                self._proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def stop(self):
        if self._proc is not None:
            try:
                self._proc.stdin.close()
                self._proc.terminate()
            except OSError:
                pass


class _Player:
    """Phát file mp3 / wav bằng MCI có sẵn của Windows. Mọi lệnh gọi từ cùng 1 luồng (luồng đọc của Speaker)."""
    ALIAS = "nhaxe_giong"

    def __init__(self):
        self._mci = ctypes.windll.winmm.mciSendStringW if sys.platform == "win32" else None
        self._open = False

    def _cmd(self, command):
        return self._mci(command, None, 0, None) if self._mci else 1

    def stop(self):
        if self._open:
            self._cmd(f"close {self.ALIAS}")
            self._open = False

    def play(self, path, volume):
        self.stop()
        if self._cmd(f'open "{path}" type mpegvideo alias {self.ALIAS}') != 0:
            return False
        self._open = True
        self._cmd(f"setaudio {self.ALIAS} volume to {max(0, min(100, int(volume))) * 10}")
        return self._cmd(f"play {self.ALIAS}") == 0


class Speaker:
    """
    Đọc câu theo giọng đã chọn. Mọi việc chạy ở luồng nền nên không làm khựng màn hình;
    lỗi gì (mất mạng, thiếu file) cũng chỉ là chuyển sang giọng khác hoặc im lặng.
    piper_dir: thư mục giong_doc (chứa piper/piper.exe và file giọng .onnx)
    cache_dir: nơi lưu file âm thanh đã tạo
    """

    def __init__(self, piper_dir, cache_dir):
        self.piper_exe = Path(piper_dir) / "piper" / "piper.exe"
        self.piper_model = Path(piper_dir) / PIPER_MODEL
        self.cache_dir = Path(cache_dir)
        self.edge_ok = importlib.util.find_spec("edge_tts") is not None
        self._edge_down_until = 0.0
        self._sapi = _Sapi()
        self._jobs = queue.Queue()      # câu cần đọc ngay
        self._fetch = queue.Queue()     # câu cần tạo sẵn / tải ngầm
        self._fetching = set()
        threading.Thread(target=self._speak_loop, daemon=True).start()
        threading.Thread(target=self._fetch_loop, daemon=True).start()

    # ----- thông tin cho màn hình Cài đặt -----
    @property
    def ready(self):
        return self._sapi.ready

    @property
    def voices(self):
        return self._sapi.voices

    def vietnamese_voice(self):
        return self._sapi.vietnamese_voice()

    def restart(self):
        self._sapi.restart()

    @property
    def piper_ok(self):
        return self.piper_exe.is_file() and self.piper_model.is_file()

    def choices(self):
        """[(mã giọng, tên hiện trong danh sách)] các giọng dùng được trên máy này."""
        items = list(EDGE_VOICES) if self.edge_ok else []
        if self.piper_ok:
            items.append((PIPER_VOICE, PIPER_LABEL))
        items += [(WIN_PREFIX + name, f"{name} (Windows)") for name, _lang in self._sapi.voices]
        return items

    def edge_pending(self, text, voice=AUTO_VOICE):
        """Giọng chọn là Edge nhưng câu chưa tải xong, nên lần này Piper đọc thay."""
        plan = self._plan(voice)
        text = " ".join(text.split())
        return (len(plan) > 1 and plan[0].startswith("edge:") and plan[1] == PIPER_VOICE
                and not self._cache_path(plan[0], text).is_file())

    def has_vietnamese(self):
        return self.edge_ok or self.piper_ok or self.vietnamese_voice() is not None

    # ----- đọc -----
    def say(self, text, voice=AUTO_VOICE, volume=100):
        """Đọc câu (câu mới cắt ngang câu đang đọc). Trả về False nếu máy không có giọng nào đọc được."""
        text = " ".join(text.split())
        if not text or not self._plan(voice):
            return False
        self._jobs.put((text, voice, volume))
        return True

    def prefetch(self, texts, voice=AUTO_VOICE):
        """Tạo sẵn file âm thanh cho các câu hay dùng (chạy ngầm), để lúc xe ra là phát được ngay."""
        plan = self._plan(voice)
        for text in dict.fromkeys(" ".join(t.split()) for t in texts):
            if not text:
                continue
            if PIPER_VOICE in plan:
                self._queue_fetch(PIPER_VOICE, text)
            if plan and plan[0].startswith("edge:"):
                self._queue_fetch(plan[0], text)

    def stop(self):
        self._jobs.put(None)
        self._fetch.put(None)
        self._sapi.stop()

    def _plan(self, voice):
        """Thứ tự giọng sẽ thử."""
        if voice.startswith(WIN_PREFIX) or (voice and not voice.startswith("edge:") and voice != PIPER_VOICE):
            name = voice[len(WIN_PREFIX):] if voice.startswith(WIN_PREFIX) else voice  # cài đặt cũ ghi tên trơn
            return [WIN_PREFIX + name]
        plan = []
        if voice.startswith("edge:") and self.edge_ok:
            plan.append(voice)
        elif voice == AUTO_VOICE and self.edge_ok:
            plan.append(EDGE_VOICES[0][0])
        if self.piper_ok:
            plan.append(PIPER_VOICE)
        vietnamese = self.vietnamese_voice()
        if vietnamese:
            plan.append(WIN_PREFIX + vietnamese)
        return plan

    def _cache_path(self, engine, text):
        key = hashlib.sha1(f"{engine}|{text}".encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"{key}.{'wav' if engine == PIPER_VOICE else 'mp3'}"

    def _speak_loop(self):
        player = _Player()
        while True:
            job = self._jobs.get()
            while job is not None and not self._jobs.empty():
                job = self._jobs.get()   # bấm liên tục thì chỉ đọc câu mới nhất
            if job is None:
                player.stop()
                return
            text, voice, volume = job
            try:
                self._speak(player, text, voice, volume)
            except Exception:   # không để lỗi đọc làm chết luồng
                pass

    def _speak(self, player, text, voice, volume):
        plan = self._plan(voice)
        for i, engine in enumerate(plan):
            if engine.startswith(WIN_PREFIX):
                player.stop()
                if self._sapi.say(engine[len(WIN_PREFIX):], text, volume):
                    return
                continue
            path = self._cache_path(engine, text)
            if not path.is_file():
                if engine.startswith("edge:") and PIPER_VOICE in plan[i + 1:]:
                    self._queue_fetch(engine, text)   # Edge chậm: lần này để Piper đọc, Edge tải ngầm cho lần sau
                    continue
                if not self._make(engine, text, path):
                    continue
            if player.play(path, volume):
                return

    def _queue_fetch(self, engine, text):
        if (engine, text) not in self._fetching and not self._cache_path(engine, text).is_file():
            self._fetching.add((engine, text))
            self._fetch.put((engine, text))

    def _fetch_loop(self):
        while True:
            job = self._fetch.get()
            if job is None:
                return
            engine, text = job
            try:
                self._make(engine, text, self._cache_path(engine, text))
            except Exception:
                pass
            finally:
                self._fetching.discard(job)

    def _make(self, engine, text, path):
        """Tạo file âm thanh cho câu. Trả về True nếu đã có file."""
        if path.is_file():
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}_{threading.get_ident()}.tmp")
        try:
            if engine == PIPER_VOICE:
                ok = self._make_piper(text, tmp)
            elif time.monotonic() < self._edge_down_until:
                ok = False
            else:
                ok = self._make_edge(engine[len("edge:"):], text, tmp)
                if not ok:
                    self._edge_down_until = time.monotonic() + EDGE_RETRY
            if ok and tmp.is_file() and tmp.stat().st_size > 0:
                tmp.replace(path)
                return True
            return False
        except OSError:
            return path.is_file()
        finally:
            tmp.unlink(missing_ok=True)

    def _make_piper(self, text, out):
        if not self.piper_ok:
            return False
        try:
            done = subprocess.run([str(self.piper_exe), "--model", str(self.piper_model), "--output_file", str(out),
                                   "--length_scale", "1.1"],
                                  input=text.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  cwd=str(self.piper_exe.parent), creationflags=_NO_WINDOW, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0

    @staticmethod
    def _make_edge(voice, text, out):
        try:
            import edge_tts
            asyncio.run(edge_tts.Communicate(text, voice, connect_timeout=5, receive_timeout=15).save(str(out)))
            return True
        except Exception:   # mất mạng, Microsoft đổi dịch vụ... -> dùng giọng khác
            return False
