"""
Gửi báo cáo lên Discord qua webhook (chỉ gửi một chiều, không cần thư viện thêm).

Tạo webhook: Discord -> chuột phải kênh -> Chỉnh sửa kênh -> Tích hợp -> Webhook -> Webhook mới -> Sao chép URL.
Mỗi ngày lúc 00:00 phần mềm gửi ảnh thẻ thống kê của ngày vừa qua.
Máy tắt lúc 00:00 thì lần mở sau gửi bù (tối đa 7 ngày gần nhất).
"""

import json
import re
import urllib.error
import urllib.request
import uuid
from datetime import date

from .. import APP_NAME, COMPANY, VERSION

WEBHOOK_RE = re.compile(r"^https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+/?$")
USER_AGENT = f"QuanLyNhaXe/{VERSION} (VIDATEX JSC)"   # Discord chặn User-Agent mặc định của Python
CATCH_UP_DAYS = 7       # máy tắt nhiều ngày thì chỉ gửi bù tối đa chừng này ngày


def valid_webhook(url):
    return bool(WEBHOOK_RE.match(url.strip()))


def png_name(day):
    return f"thong_ke_{day:%d-%m-%Y}.png"


def post(url, content="", embeds=(), files=(), timeout=20):
    """Gửi tin nhắn qua webhook. files: [(tên file, bytes)]. Lỗi thì ném RuntimeError có lời giải thích."""
    payload = {"username": APP_NAME, "content": content[:2000], "embeds": list(embeds)[:10],
               "allowed_mentions": {"parse": []}}
    boundary = uuid.uuid4().hex
    parts = [(f'Content-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n',
              json.dumps(payload, ensure_ascii=False).encode("utf-8"))]
    for i, (name, data) in enumerate(files):
        safe = name.replace('"', "")
        parts.append((f'Content-Disposition: form-data; name="files[{i}]"; filename="{safe}"\r\n'
                      f"Content-Type: application/octet-stream\r\n\r\n", data))
    body = b"".join(f"--{boundary}\r\n".encode() + head.encode("utf-8") + data + b"\r\n" for head, data in parts)
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url.strip(), data=body, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 404):
            raise RuntimeError("Webhook không còn tồn tại hoặc sai địa chỉ — tạo lại webhook trong Discord") from exc
        if exc.code == 429:
            raise RuntimeError("Discord đang giới hạn tốc độ gửi, sẽ thử lại sau") from exc
        raise RuntimeError(f"Discord từ chối (mã {exc.code})") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError("Không kết nối được Discord — kiểm tra mạng Internet") from exc


def days_to_report(last_sent, today=None):
    """Những ngày chưa gửi báo cáo, tính đến hôm qua (00:00 hôm nay là lúc chốt ngày hôm qua).
    Chưa gửi lần nào (last_sent None) thì chỉ gửi hôm qua."""
    today = today or date.today()
    yesterday = date.fromordinal(today.toordinal() - 1)
    if last_sent is None:
        return [yesterday]
    start = max(last_sent.toordinal() + 1, yesterday.toordinal() - CATCH_UP_DAYS + 1)
    return [date.fromordinal(n) for n in range(start, yesterday.toordinal() + 1)]
