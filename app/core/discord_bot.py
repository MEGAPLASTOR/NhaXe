"""
Bot Discord để tra cứu nhà xe ngay trong Discord bằng lệnh gạch chéo:

  /thongke [ngay]          thống kê 1 ngày (mặc định hôm nay)
  /lichsu  [ngay]          danh sách từng lượt xe trong ngày
  /tracuu  the [so_luot]   lịch sử của 1 số thẻ, kèm ảnh vào / ra của lượt gần nhất
  /danggui                 các xe đang gửi trong bãi

Tạo bot: discord.com/developers/applications -> New Application -> Bot -> Reset Token (chép token vào Cài đặt).
Mời bot vào server: OAuth2 -> URL Generator -> tích "bot" và "applications.commands",
quyền Send Messages, Embed Links, Attach Files -> mở link vừa tạo và chọn server.

Bot chạy ở luồng riêng. Cơ sở dữ liệu chỉ được đụng tới từ luồng giao diện, nên mọi truy vấn đi qua run_on_ui.
"""

import asyncio
import io
import re
import threading
from collections import namedtuple
from datetime import date, datetime, timedelta

from . import discord_card as card_ui
from .errors import log_error
from .pricing import money
from .report import day_card_data, day_label, day_status, day_summary, parse_day
from .storage import record_duration, vn_time

UI_TIMEOUT = 15          # giây chờ luồng giao diện trả kết quả
LIST_LIMIT = 20          # số dòng tối đa vẽ trong ảnh, còn lại xem trong phần mềm (F4)
DAY_MONTH = re.compile(r"^(\d{1,2})[/-](\d{1,2})$")
STATUS_COLOR = {"IN": card_ui.GREEN, "STAY": card_ui.PURPLE, "OUT": card_ui.ORANGE}
LIST_COLUMNS = [("Thẻ", 40), ("Vào", 170), ("Ra", 370), ("Đã gửi", 570), ("Tiền", 830)]

# Câu trả lời của bot: chữ ngắn + ảnh thẻ (vẽ ở luồng nền bằng render(data)) + file đính kèm khác
Reply = namedtuple("Reply", "content render data image_name files")


def parse_day_arg(text, today=None):
    """Ngày gõ trong Discord: trống / 'hôm nay' / 'hôm qua' / '31/10' / '31/10/2026'. Sai thì ValueError."""
    today = today or date.today()
    t = " ".join((text or "").lower().split())
    if t in ("", "hôm nay", "hom nay", "homnay", "nay"):
        return today
    if t in ("hôm qua", "hom qua", "homqua", "qua"):
        return today - timedelta(days=1)
    m = DAY_MONTH.match(t)
    if m:
        return date(today.year, int(m[2]), int(m[1]))
    return parse_day(t)


def _short(ts, day=None):
    """'2026-10-31 08:05:00' -> '08:05' nếu đúng ngày đang xem, không thì '08:05 31/10'."""
    if ts is None:
        return "—"
    if day is not None and ts[:10] == day.isoformat():
        return ts[11:16]
    return f"{ts[11:16]} {ts[8:10]}/{ts[5:7]}"


class Queries:
    """Các câu tra cứu bot dùng. Chạy trên luồng giao diện (gọi qua run_on_ui), trả về dữ liệu thuần (Reply)."""

    def __init__(self, storage, fee_of):
        self.storage = storage
        self.fee_of = fee_of

    def _fee_text(self, r):
        amount, estimate = self.fee_of(r)
        return f"~ {money(amount)}" if estimate else money(amount)

    def _row(self, r, day, tag):
        return (r["so_the"], _short(r["gio_vao"], day), _short(r["gio_ra"], day), record_duration(r),
                self._fee_text(r), STATUS_COLOR[tag])

    def day_report(self, day):
        today = date.today()
        rows = self.storage.day_records(day)
        parked = self.storage.stats()["parked"] if day == today else None
        data = day_card_data(rows, day, self.fee_of, parked, final=day < today)
        return Reply(f"📊 Thống kê nhà xe — {day_label(day)}", card_ui.render_day, data,
                     f"thong_ke_{day:%d-%m-%Y}.png", [])

    def day_list(self, day):
        rows = self.storage.day_records(day)
        stats = day_summary(rows, day, self.fee_of)
        groups = {"IN": [], "STAY": [], "OUT": []}
        for r in rows:
            groups[day_status(r, day)[1]].append(r)
        ordered = [(r, tag) for tag in ("IN", "STAY", "OUT") for r in groups[tag]]
        data = {"kicker": "LỊCH SỬ NHÀ XE", "title": day_label(day),
                "subtitle": f"{stats['total']} xe · vào {stats['in']} · ra {stats['out']} · thu {money(stats['money'])}",
                "chips": [(f"Đang gửi {len(groups['IN'])}", card_ui.GREEN),
                          (f"Qua đêm {len(groups['STAY'])}", card_ui.PURPLE),
                          (f"Đã ra {len(groups['OUT'])}", card_ui.ORANGE)],
                "columns": LIST_COLUMNS, "table_title": "Từng lượt xe",
                "rows": [self._row(r, day, tag) for r, tag in ordered[:LIST_LIMIT]],
                "more": max(0, len(rows) - LIST_LIMIT), "footer": f"Tạo lúc {datetime.now():%H:%M  %d/%m/%Y}"}
        return Reply(f"📋 Lịch sử nhà xe — {day_label(day)}", card_ui.render_list, data,
                     f"lich_su_{day:%d-%m-%Y}.png", [])

    def card_history(self, card, count):
        rows = self.storage.search(card=card, limit=500)
        rows = [r for r in rows if r["so_the"] == card]   # search tìm theo 1 phần số thẻ
        if not rows:
            return Reply(f"🔎 Thẻ **{card}** chưa có lượt gửi nào.", None, None, None, [])
        latest = rows[0]
        amount, estimate = self.fee_of(latest)
        photo = lambda rel: str(self.storage.abs_path(rel)) if rel else None
        t_in, t_out = latest["gio_vao"][11:16], latest["gio_ra"][11:16] if latest["gio_ra"] else None
        data = {
            "card": card, "total": len(rows),
            "latest": {"vao": vn_time(latest["gio_vao"]), "ra": vn_time(latest["gio_ra"]) if latest["gio_ra"] else "Chưa ra",
                       "duration": record_duration(latest), "fee": amount, "estimate": estimate,
                       "parked": latest["gio_ra"] is None},
            "photos": [(f"↓  Ảnh lúc vào · {t_in}", photo(latest["anh_vao"])),
                       ("↑  Ảnh lúc ra" + (f" · {t_out}" if t_out else ""), photo(latest["anh_ra"]))],
            "history": [(_short(r["gio_vao"]), _short(r["gio_ra"]) if r["gio_ra"] else "Đang gửi", record_duration(r),
                         self._fee_text(r), r["gio_ra"] is None) for r in rows[1:count + 1]],
        }
        return Reply(f"🔎 Tra cứu thẻ **{card}**", card_ui.render_card, data, f"the_{card}.png", [])

    def parked(self):
        rows = self.storage.list_parked()
        total = sum(self.fee_of(r)[0] for r in rows)
        data = {"kicker": "XE ĐANG GỬI", "title": f"{len(rows)} xe trong bãi", "icon": card_ui.icon_parking,
                "subtitle": f"Tiền tạm tính nếu tất cả ra bây giờ: {money(total)}",
                "chips": [(f"Cập nhật {datetime.now():%H:%M}", card_ui.GREEN)],
                "columns": LIST_COLUMNS, "table_title": "Xe đang gửi",
                "rows": [self._row(r, None, "IN") for r in rows[:LIST_LIMIT]],
                "more": max(0, len(rows) - LIST_LIMIT), "footer": f"Tạo lúc {datetime.now():%H:%M  %d/%m/%Y}"}
        return Reply("🅿️ Xe đang gửi trong bãi", card_ui.render_list, data, "xe_dang_gui.png", [])


class DiscordBot:
    """
    token     : token của bot
    channel   : ID kênh được phép tra cứu (chuỗi trống = mọi kênh bot thấy)
    queries   : đối tượng Queries
    run_on_ui : hàm nhận 1 hàm, chạy nó trên luồng giao diện, trả về concurrent.futures.Future
    on_status : hàm nhận (chữ, mức 'ok' / 'warn' / 'error'); được gọi trên luồng giao diện
    """

    def __init__(self, token, channel, queries, run_on_ui, on_status):
        self.token = token.strip()
        self.channel = int(channel) if str(channel).strip().isdigit() else None
        self.queries = queries
        self.run_on_ui = run_on_ui
        self._status = lambda text, level: run_on_ui(lambda: on_status(text, level))
        self._loop = None
        self._client = None
        self._stopping = False

    def start(self):
        threading.Thread(target=self._run, name="discord-bot", daemon=True).start()

    def stop(self):
        self._stopping = True
        if self._loop is not None and self._client is not None and not self._loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
            except RuntimeError:
                pass

    def _run(self):
        try:
            asyncio.run(self._main())
        except Exception as exc:  # không để lỗi bot làm hỏng phần mềm
            if not self._stopping:
                self._status(f"Bot Discord lỗi: {exc}", "error")

    async def _ask(self, fn):
        return await asyncio.wait_for(asyncio.wrap_future(self.run_on_ui(fn)), UI_TIMEOUT)

    async def _main(self):
        import discord
        from discord import app_commands

        self._loop = asyncio.get_running_loop()
        intents = discord.Intents.none()
        intents.guilds = True
        client = self._client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)
        q = self.queries

        async def send(inter, reply):
            """Vẽ ảnh thẻ ở luồng phụ (không chặn bot) rồi gửi kèm các file khác."""
            files = []
            if reply.render is not None:
                png = await asyncio.to_thread(reply.render, reply.data)
                files.append(discord.File(io.BytesIO(png), filename=reply.image_name))
            files += [discord.File(io.BytesIO(data), filename=name) for name, data in reply.files]
            await inter.followup.send(reply.content, files=files)

        async def guard(inter):
            """Chỉ trả lời trong kênh đã chọn (nếu có)."""
            if self.channel and inter.channel_id != self.channel:
                await inter.response.send_message("Lệnh nhà xe chỉ dùng trong kênh đã cài đặt.", ephemeral=True)
                return False
            await inter.response.defer(thinking=True)
            return True

        async def day_arg(inter, ngay):
            try:
                day = parse_day_arg(ngay)
            except ValueError:
                await inter.followup.send(f"Ngày **{ngay}** không hợp lệ. Gõ dạng 31/10/2026, 31/10, hôm nay, hôm qua.")
                return None
            if day > date.today():
                await inter.followup.send("Ngày này chưa tới.")
                return None
            return day

        @tree.command(name="thongke", description="Thống kê xe vào / ra và tiền thu của 1 ngày")
        @app_commands.describe(ngay="Ngày cần xem, vd 31/10/2026 hoặc hôm qua (để trống = hôm nay)")
        async def thongke(inter: discord.Interaction, ngay: str = ""):
            if await guard(inter) and (day := await day_arg(inter, ngay)):
                await send(inter, await self._ask(lambda: q.day_report(day)))

        @tree.command(name="lichsu", description="Danh sách từng lượt xe trong 1 ngày")
        @app_commands.describe(ngay="Ngày cần xem, vd 31/10/2026 hoặc hôm qua (để trống = hôm nay)")
        async def lichsu(inter: discord.Interaction, ngay: str = ""):
            if await guard(inter) and (day := await day_arg(inter, ngay)):
                await send(inter, await self._ask(lambda: q.day_list(day)))

        @tree.command(name="tracuu", description="Lịch sử gửi xe của 1 số thẻ, kèm ảnh lượt gần nhất")
        @app_commands.describe(the="Số thẻ", so_luot="Số lượt trước đó muốn xem (mặc định 5)")
        async def tracuu(inter: discord.Interaction, the: str, so_luot: app_commands.Range[int, 1, 20] = 5):
            if not await guard(inter):
                return
            card = the.strip()
            if not card.isdigit():
                await inter.followup.send("Số thẻ chỉ gồm chữ số.")
                return
            await send(inter, await self._ask(lambda: q.card_history(card, so_luot)))

        @tree.command(name="danggui", description="Các xe đang gửi trong bãi")
        async def danggui(inter: discord.Interaction):
            if await guard(inter):
                await send(inter, await self._ask(q.parked))

        @tree.error
        async def on_error(inter, error):
            log_error(type(error), error, error.__traceback__)
            text = "Tra cứu không thành công, thử lại sau."
            try:
                if inter.response.is_done():
                    await inter.followup.send(text)
                else:
                    await inter.response.send_message(text, ephemeral=True)
            except discord.HTTPException:
                pass

        async def sync(guild):
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)   # đăng ký lệnh riêng cho server: có ngay, không phải chờ

        @client.event
        async def on_ready():
            for guild in client.guilds:
                await sync(guild)
            if client.guilds:
                self._status(f"Bot Discord đã kết nối: {client.user} ({len(client.guilds)} server)", "ok")
            else:
                self._status(f"Bot {client.user} đã kết nối nhưng chưa được mời vào server nào", "warn")

        @client.event
        async def on_guild_join(guild):
            await sync(guild)

        try:
            await client.start(self.token)
        except discord.LoginFailure:
            self._status("Token bot Discord sai — lấy lại token trong Discord Developer Portal", "error")
        except (discord.GatewayNotFound, discord.ConnectionClosed, OSError):
            if not self._stopping:
                self._status("Bot Discord mất kết nối — kiểm tra mạng Internet", "error")
        finally:
            if not client.is_closed():
                await client.close()
