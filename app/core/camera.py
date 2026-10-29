"""Đọc camera Imou (RTSP) hoặc webcam ở luồng riêng, tự kết nối lại khi mất mạng."""

import os
import sys
import threading
import time
from datetime import datetime
from urllib.parse import quote

# RTSP qua TCP ổn định hơn với camera WiFi
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2
import numpy as np

SIGNAL_TIMEOUT = 3.0  # giây không có hình mới thì coi là mất tín hiệu
CONNECTED = "Đã kết nối"


def camera_source(cam):
    """Từ cài đặt 1 camera (ip, tai_khoan, mat_khau, luong, url): trả về URL RTSP, số webcam, hoặc None (chế độ thử)."""
    url = cam.get("url", "").strip()
    if url:
        return int(url) if url.isdigit() else url
    ip = cam.get("ip", "").strip()
    if not ip:
        return None
    user = cam.get("tai_khoan", "").strip() or "admin"
    password = cam.get("mat_khau", "").strip()
    stream = cam.get("luong", "").strip() or "0"
    # Địa chỉ RTSP chuẩn của camera Imou / Dahua
    return (f"rtsp://{quote(user, safe='')}:{quote(password, safe='')}@{ip}:554"
            f"/cam/realmonitor?channel=1&subtype={stream}")


def placeholder_frame(title):
    """Khung hình giả khi chưa cấu hình camera (để vẫn thử được chương trình)."""
    img = np.full((540, 960, 3), (48, 36, 28), np.uint8)
    cv2.putText(img, title, (60, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
    cv2.putText(img, "CHE DO THU - bam nut Cai dat de nhap IP camera", (60, 290),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
    cv2.putText(img, datetime.now().strftime("%d/%m/%Y  %H:%M:%S"), (60, 350),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
    return img


class CameraStream:
    def __init__(self, name, source):
        self.name = name
        self.source = source
        self.state = "Chế độ thử (chưa cấu hình camera)" if source is None else "Đang kết nối..."
        self._lock = threading.Lock()
        self._frame = None
        self._frame_time = 0.0
        self._stop = threading.Event()
        if source is not None:
            threading.Thread(target=self._run, daemon=True).start()

    @property
    def configured(self):
        return self.source is not None

    def _open(self):
        if isinstance(self.source, int):
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
            return cv2.VideoCapture(self.source, backend)
        params = []
        for prop, value in (("CAP_PROP_OPEN_TIMEOUT_MSEC", 8000), ("CAP_PROP_READ_TIMEOUT_MSEC", 5000)):
            if hasattr(cv2, prop):
                params += [getattr(cv2, prop), value]
        return cv2.VideoCapture(self.source, cv2.CAP_FFMPEG, params)

    def _run(self):
        while not self._stop.is_set():
            self.state = "Đang kết nối..."
            cap = self._open()
            if not cap.isOpened():
                cap.release()
                self.state = "Không kết nối được — kiểm tra IP / mật khẩu"
                self._stop.wait(3)
                continue
            self.state = "Đang chờ hình..."
            fails = 0
            while not self._stop.is_set() and fails < 20:
                ok, frame = cap.read()
                if ok and frame is not None:
                    fails = 0
                    self.state = CONNECTED
                    with self._lock:
                        self._frame = frame
                        self._frame_time = time.monotonic()
                else:
                    fails += 1
                    time.sleep(0.1)
            cap.release()
            if not self._stop.is_set():
                self.state = "Mất kết nối — đang kết nối lại..."
                self._stop.wait(2)

    def latest(self):
        """Khung hình mới nhất; chế độ thử thì trả ảnh giả; None nếu mất tín hiệu."""
        if not self.configured:
            return placeholder_frame(self.name)
        with self._lock:
            if self._frame is None or time.monotonic() - self._frame_time > SIGNAL_TIMEOUT:
                return None
            return self._frame

    def stop(self):
        self._stop.set()
