"""
Nối phần mềm với Discord: tự gửi thống kê lúc 00:00 qua webhook và chạy bot tra cứu.

Việc gửi mạng chạy ở luồng nền để màn hình không bị khựng. Cơ sở dữ liệu (sqlite) chỉ được đọc trên
luồng giao diện, nên luồng nền nhờ việc qua run_on_ui(): hàng đợi được luồng giao diện lấy ra chạy liên tục.
"""

import json
import queue
import threading
import time
from concurrent.futures import Future
from datetime import date
from pathlib import Path

from ..core.discord_bot import DiscordBot, Queries
from ..core.discord_card import render_day
from ..core.discord_hook import days_to_report, png_name, post, valid_webhook
from ..core.errors import log_error
from ..core.report import day_card_data, day_label

PUMP_MS = 150           # luồng giao diện kiểm tra hàng đợi việc của luồng nền
CHECK_MS = 30 * 1000    # kiểm tra đã tới giờ gửi báo cáo chưa
RETRY_SECONDS = 300     # gửi lỗi (mất mạng...) thì 5 phút sau thử lại


class DiscordService:
    """
    win       : cửa sổ chính (dùng after() để chạy việc trên luồng giao diện)
    storage   : kho dữ liệu
    fee_of    : hàm tính tiền 1 lượt -> (tiền, tạm tính hay không)
    on_status : hàm nhận (chữ, mức) để hiện ở thanh dưới màn hình chính
    """

    def __init__(self, win, storage, fee_of, data_dir, on_status):
        self.win = win
        self.storage = storage
        self.fee_of = fee_of
        self.on_status = on_status
        self.state_file = Path(data_dir) / "discord.json"
        self.config = {"on": False, "webhook": "", "bot_on": False, "bot_token": "", "channel": ""}
        self.bot = None
        self._bot_key = None
        self.bot_status = ("Bot đang tắt", "info")
        self._jobs = queue.Queue()
        self._sending = False
        self._next_try = 0.0
        win.after(PUMP_MS, self._pump)
        win.after(5000, self._tick)

    # ----- cầu nối luồng nền -> luồng giao diện -----
    def run_on_ui(self, fn):
        future = Future()
        self._jobs.put((fn, future))
        return future

    def _pump(self):
        while True:
            try:
                fn, future = self._jobs.get_nowait()
            except queue.Empty:
                break
            if future.set_running_or_notify_cancel():
                try:
                    future.set_result(fn())
                except Exception as exc:
                    future.set_exception(exc)
        try:
            self.win.after(PUMP_MS, self._pump)
        except Exception:
            pass  # cửa sổ đã đóng

    # ----- cài đặt -----
    def apply(self, config):
        self.config = dict(config)
        self._next_try = 0.0
        key = (config["bot_on"], config["bot_token"].strip(), config["channel"].strip())
        if key == self._bot_key:
            return
        self._bot_key = key
        if self.bot is not None:
            self.bot.stop()
            self.bot = None
        if config["bot_on"] and config["bot_token"].strip():
            self.bot_status = ("Bot đang kết nối Discord...", "info")
            self.bot = DiscordBot(config["bot_token"], config["channel"], Queries(self.storage, self.fee_of),
                                  self.run_on_ui, self._bot_changed)
            self.bot.start()
        else:
            self.bot_status = ("Bot đang tắt" if not config["bot_on"] else "Chưa nhập token bot", "info")

    def _bot_changed(self, text, level):
        self.bot_status = (text, level)
        self.on_status(text, level)

    def stop(self):
        if self.bot is not None:
            self.bot.stop()

    # ----- báo cáo hằng ngày -----
    def _last_sent(self):
        try:
            return date.fromisoformat(json.loads(self.state_file.read_text(encoding="utf-8"))["last_report"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _mark_sent(self, day):
        last = self._last_sent()
        if last is None or day > last:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps({"last_report": day.isoformat()}), encoding="utf-8")

    def _tick(self):
        try:
            cfg = self.config
            if (cfg["on"] and valid_webhook(cfg["webhook"]) and not self._sending
                    and time.monotonic() >= self._next_try):
                days = days_to_report(self._last_sent())
                if days:
                    self._send([self._payload(d) for d in days], cfg["webhook"], days)
        except Exception as exc:  # không để lỗi báo cáo làm hỏng phần mềm
            log_error(type(exc), exc, exc.__traceback__)
        finally:
            try:
                self.win.after(CHECK_MS, self._tick)
            except Exception:
                pass

    def _payload(self, day, content=None):
        """Nội dung báo cáo 1 ngày: (chữ, số liệu để vẽ ảnh thẻ). Chạy trên luồng giao diện;
        ảnh vẽ sau ở luồng nền để màn hình không khựng. Chỉ gửi ảnh, không kèm file danh sách."""
        rows = self.storage.day_records(day)
        data = day_card_data(rows, day, self.fee_of, self.storage.stats()["parked"], final=day < date.today())
        return content or f"📊 **Báo cáo nhà xe — {day_label(day)}**", data

    def _send(self, payloads, url, days):
        self._sending = True

        def work():
            sent, error = [], None
            for (content, data), day in zip(payloads, days):
                try:
                    post(url, content, files=[(png_name(day), render_day(data))])
                    sent.append(day)
                except RuntimeError as exc:
                    error = str(exc)
                    break
                except Exception as exc:  # lỗi vẽ ảnh...: ghi lại, không để luồng chết mà kẹt cờ đang gửi
                    log_error(type(exc), exc, exc.__traceback__)
                    error = "lỗi tạo báo cáo (chi tiết trong data/loi.log)"
                    break
            self.run_on_ui(lambda: self._sent(sent, error))

        threading.Thread(target=work, name="discord-report", daemon=True).start()

    def _sent(self, sent, error):
        self._sending = False
        for day in sent:
            self._mark_sent(day)
        if sent:
            names = ", ".join(f"{d:%d/%m}" for d in sent)
            self.on_status(f"Đã gửi thống kê ngày {names} lên Discord", "ok")
        if error:
            self._next_try = time.monotonic() + RETRY_SECONDS
            self.on_status(f"Chưa gửi được thống kê lên Discord: {error}", "warn")

    def send_test(self, url, done):
        """Nút Gửi thử trong Cài đặt: gửi thống kê hôm nay (tới giờ này). done(ok, chữ) chạy trên luồng giao diện."""
        if not valid_webhook(url):
            done(False, "Địa chỉ webhook không đúng dạng https://discord.com/api/webhooks/...")
            return
        today = date.today()
        content, data = self._payload(today, "🧪 **Gửi thử** — thống kê hôm nay tới giờ này")

        def work():
            try:
                post(url, content, files=[(png_name(today), render_day(data))])
                result = (True, "Đã gửi thử — xem tin nhắn trong kênh Discord")
            except RuntimeError as exc:
                result = (False, str(exc))
            except Exception as exc:
                log_error(type(exc), exc, exc.__traceback__)
                result = (False, "Lỗi tạo báo cáo — chi tiết trong data/loi.log")
            self.run_on_ui(lambda: done(*result))

        threading.Thread(target=work, name="discord-test", daemon=True).start()
