"""
Hỏi thẳng camera bằng giao thức RTSP để biết vì sao không xem được hình.

OpenCV chỉ báo "mở không được" cho mọi lỗi, không phân biệt được sai mật khẩu hay sai đường dẫn.
Ở đây gửi lệnh DESCRIBE rồi đọc mã trả về:
    200 = vào được          401 = sai tài khoản / mật khẩu
    404 = sai đường dẫn     453 = quá nhiều máy đang xem
Nhờ vậy báo cho người dùng đúng việc cần sửa, và tự tìm ra đường dẫn đúng của từng đời camera.
"""

import hashlib
import re
import socket
from urllib.parse import quote

RTSP_PORT = 554
# Đường dẫn của các đời camera Imou / Dahua và vài hãng hay gặp, thử lần lượt từ trên xuống
PATHS = [
    "/cam/realmonitor?channel=1&subtype={stream}",
    "/cam/realmonitor?channel=1&subtype={stream}&unicast=true&proto=Onvif",
    "/live/ch{stream}",
    "/live",
    "/onvif{one}",
    "/h264Preview_01_{main_sub}",
    "/stream{one}",
    "/ch0_{stream}.h264",
    "/{one}",
    "",
]
_CODE = re.compile(r"^RTSP/\d\.\d (\d+)", re.MULTILINE)
_HEADER = re.compile(r"^([\w-]+):\s*(.*)$", re.MULTILINE)
_PAIR = re.compile(r'(\w+)="([^"]*)"')

STATUS_TEXT = {
    200: "Vào được",
    401: "Sai tài khoản hoặc mật khẩu",
    403: "Camera từ chối truy cập",
    404: "Camera không có đường dẫn này",
    453: "Camera đã hết chỗ cho máy xem (tắt bớt app đang mở)",
    455: "Camera từ chối lệnh này",
    501: "Camera không hỗ trợ RTSP",
}


def _md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _auth_header(challenge, method, url, user, password):
    """Tạo dòng Authorization trả lời yêu cầu đăng nhập của camera."""
    if challenge.lower().startswith("basic"):
        import base64
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"
    bits = dict(_PAIR.findall(challenge))
    realm, nonce = bits.get("realm", ""), bits.get("nonce", "")
    ha1 = _md5(f"{user}:{realm}:{password}")
    ha2 = _md5(f"{method}:{url}")
    parts = [f'username="{user}"', f'realm="{realm}"', f'nonce="{nonce}"', f'uri="{url}"']
    if bits.get("qop"):
        cnonce, nc = "0a4f113b", "00000001"
        response = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        parts += ['qop=auth', f'nc={nc}', f'cnonce="{cnonce}"']
    else:
        response = _md5(f"{ha1}:{nonce}:{ha2}")
    parts.append(f'response="{response}"')
    if bits.get("opaque"):
        parts.append(f'opaque="{bits["opaque"]}"')
    return "Digest " + ", ".join(parts)


def _send(sock, url, seq, auth=None):
    lines = [f"DESCRIBE {url} RTSP/1.0", f"CSeq: {seq}", "User-Agent: QuanLyNhaXe", "Accept: application/sdp"]
    if auth:
        lines.append(f"Authorization: {auth}")
    sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("utf-8"))
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", "replace")


def describe(ip, path="", user="admin", password="", port=RTSP_PORT, timeout=4.0):
    """
    Gửi lệnh DESCRIBE tới camera. Trả về {"code", "status", "server", "error"}.
    code = None nghĩa là không nói chuyện được với camera (error cho biết vì sao).
    """
    url = f"rtsp://{ip}:{port}{path}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        reply = _send(sock, url, 1)
        code = _CODE.search(reply)
        code = int(code.group(1)) if code else None
        headers = {k.lower(): v.strip() for k, v in _HEADER.findall(reply)}
        if code == 401 and password is not None:
            challenge = headers.get("www-authenticate", "")
            if challenge:
                auth = _auth_header(challenge, "DESCRIBE", url, user, password)
                reply = _send(sock, url, 2, auth)
                again = _CODE.search(reply)
                code = int(again.group(1)) if again else code
                headers.update({k.lower(): v.strip() for k, v in _HEADER.findall(reply)})
        return {"code": code, "status": STATUS_TEXT.get(code, f"Camera trả về mã {code}"),
                "server": headers.get("server", ""), "error": None}
    except socket.timeout:
        return {"code": None, "status": "Camera không trả lời", "server": "", "error": "timeout"}
    except OSError as exc:
        return {"code": None, "status": "Không kết nối được tới camera", "server": "", "error": str(exc)}
    finally:
        sock.close()


def candidate_urls(ip, user, password, stream="0", port=RTSP_PORT):
    """Danh sách địa chỉ RTSP sẽ thử, kèm phần đường dẫn để ghi vào cài đặt."""
    out = []
    for shape in PATHS:
        path = shape.format(stream=stream, one="1", main_sub="main" if stream == "0" else "sub")
        auth = f"{quote(user, safe='')}:{quote(password, safe='')}@" if user else ""
        out.append((path, f"rtsp://{auth}{ip}:{port}{path}"))
    return out


def find_stream(ip, password, user="admin", stream="0", port=RTSP_PORT, timeout=4.0):
    """
    Tự thử các đường dẫn cho tới khi camera chấp nhận.
    Trả về (địa chỉ RTSP dùng được hoặc None, lời nhắn, mã trả về cuối cùng).
    """
    first = describe(ip, "", user, password, port, timeout)
    if first["code"] is None:  # không bắt tay được thì khỏi thử tiếp
        return None, first["status"], None
    seen = set()
    last = first["code"]
    for path, url in candidate_urls(ip, user, password, stream, port):
        if path in seen:
            continue
        seen.add(path)
        answer = describe(ip, path, user, password, port, timeout)
        if answer["code"] == 200:
            return url, "Đã kết nối được camera", 200
        if answer["code"] is not None:
            last = answer["code"]
        if answer["code"] == 401:
            # sai mật khẩu thì đường dẫn nào cũng 401, không cần thử nữa
            return None, STATUS_TEXT[401], 401
    return None, STATUS_TEXT.get(last, f"Camera trả về mã {last}"), last
