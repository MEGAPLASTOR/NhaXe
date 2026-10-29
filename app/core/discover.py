"""
Tự dò camera IP trong mạng nội bộ.

Quét dải địa chỉ của máy (vd 192.168.1.1 -> 192.168.1.254), thiết bị nào mở cổng 554 (RTSP)
thì gần như chắc chắn là camera. Đọc thêm địa chỉ MAC từ lệnh arp để đoán hãng,
camera Imou / Dahua được xếp lên trước.

Không dò được mật khẩu: Safety Code chỉ in trên tem dán ở thân camera.
"""

import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from .rtsp import RTSP_PORT, describe, find_stream

WEB_PORT = 80
SCAN_WORKERS = 120
# Đầu địa chỉ MAC (OUI) của Dahua - hãng sản xuất camera Imou
IMOU_OUI = {"3CEF8C", "4C11BF", "9C1463", "14A78B", "38AF29", "E0508B", "08EDED", "24526A",
            "6C1C71", "BC325F", "44D244", "F4B1C2", "C0393D", "A0BDCD", "90021B", "E45555"}
_ARP_LINE = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F:-]{14,17})")


def local_ipv4():
    """Địa chỉ IP của máy trong mạng nội bộ (None nếu không có mạng)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))  # không gửi gì, chỉ để biết card mạng nào đang dùng
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def subnet(ip=None):
    """Dải địa chỉ cần quét, vd '192.168.1'. None nếu không xác định được."""
    ip = ip or local_ipv4()
    return ip.rsplit(".", 1)[0] if ip else None


def _port_open(ip, port, timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((ip, port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def mac_table():
    """{IP: MAC} lấy từ lệnh arp của Windows."""
    extra = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10, **extra).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    table = {}
    for line in out.splitlines():
        found = _ARP_LINE.search(line)
        if found:
            table[found.group(1)] = found.group(2).upper().replace(":", "-")
    return table


def is_imou(mac):
    return bool(mac) and mac.replace("-", "")[:6].upper() in IMOU_OUI


def scan(progress=None, timeout=0.6, stop=None):
    """
    Tìm camera trong mạng. progress(đã xong, tổng) được gọi trong lúc quét.
    Trả về danh sách {"ip", "mac", "imou", "web"}, camera Imou xếp trước.
    """
    base = subnet()
    if base is None:
        return []
    hosts = [f"{base}.{i}" for i in range(1, 255)]
    found, done = [], 0
    with ThreadPoolExecutor(SCAN_WORKERS) as pool:
        for ip, opened in zip(hosts, pool.map(lambda h: _port_open(h, RTSP_PORT, timeout), hosts)):
            done += 1
            if opened:
                found.append(ip)
            if progress is not None:
                progress(done, len(hosts))
            if stop is not None and stop():
                break
    macs = mac_table()
    cams = []
    for ip in found:
        mac = macs.get(ip, "")
        hello = describe(ip)  # chào hỏi không mật khẩu, chỉ để đọc tên hãng camera trả về
        cams.append({"ip": ip, "mac": mac, "server": hello["server"],
                     "imou": is_imou(mac) or "dahua" in hello["server"].lower(),
                     "web": _port_open(ip, WEB_PORT, 0.4)})
    cams.sort(key=lambda c: (not c["imou"], [int(p) for p in c["ip"].split(".")]))
    return cams


def test_login(ip, password, user="admin", stream="0"):
    """
    Tự thử các đường dẫn RTSP của camera này. Trả về (được hay không, lời nhắn, địa chỉ RTSP dùng được).
    Hỏi thẳng camera nên biết rõ sai mật khẩu hay sai đường dẫn, thay vì chỉ "mở không được".
    """
    url, message, code = find_stream(ip, password, user, stream)
    if url:
        return True, message, url
    if code == 401:
        message = "Sai Safety Code — xem lại tem dán dưới đáy camera"
    elif code is None:
        message += " — kiểm tra camera còn cắm điện và cùng mạng không"
    elif code in (404, 501):
        message += " — vào app Imou Life bật RTSP cho camera này"
    return False, message, None
