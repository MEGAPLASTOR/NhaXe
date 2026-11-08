"""
Bot Discord để tra cứu nhà xe ngay trong Discord bằng lệnh gạch chéo:

  /thongke [ngay]          thống kê 1 ngày (mặc định hôm nay) + file CSV danh sách xe
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
from datetime import date, timedelta
from pathlib import Path

from .discord_hook import COLOR, csv_name, day_embed
from .pricing import money
from .report import csv_bytes, day_label, day_status, day_summary, parse_day
from .storage import record_duration, vn_time

UI_TIMEOUT = 15          # giây chờ luồng giao diện trả kết quả
LIST_LIMIT = 40          # số dòng tối đa hiện trong tin nhắn, còn lại xem file CSV
DAY_MONTH = re.compile(r"^(\d{1,2})[/-](\d{1,2})$")


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


def _line(r, day=None):
    """1 dòng của bảng lượt gửi (chữ đều cột trong khung code)."""
    return f"{r['so_the']:>6}  {_short(r['gio_vao'], day):<11} {_short(r['gio_ra'], day):<11} {record_duration(r)}"


def _table(lines, more=0):
    body = "\n".join(["  Thẻ  Vào         Ra          Đã gửi", *lines]) if lines else "(không có lượt nào)"
    text = f"```\n{body}\n```"
    if more:
        text += f"\n… còn **{more}** lượt nữa, xem trong file CSV đính kèm."
    return text


class Queries:
    """Các câu tra cứu bot dùng. Chạy trên luồng giao diện (gọi qua run_on_ui), trả về dữ liệu thuần."""

    def __init__(self, storage, fee_of):
        self.storage = storage
        self.fee_of = fee_of

    def day_report(self, day):
        rows = self.storage.day_records(day)
        stats = day_summary(rows, day, self.fee_of)
        parked = self.storage.stats()["parked"] if day == date.today() else None
        embed = day_embed(day, stats, parked, title=f"📊 Thống kê {day_label(day)}")
        return embed, (csv_name(day), csv_bytes(rows, self.fee_of)) if rows else None

    def day_list(self, day):
        rows = self.storage.day_records(day)
        stats = day_summary(rows, day, self.fee_of)
        groups = {"OUT": [], "IN": [], "STAY": []}
        for r in rows:
            groups[day_status(r, day)[1]].append(_line(r, day))
        shown, lines = 0, []
        for tag, title in (("IN", "Đang gửi"), ("STAY", "Gửi qua đêm"), ("OUT", "Đã ra")):
            if groups[tag] and shown < LIST_LIMIT:
                lines.append(f"— {title} ({len(groups[tag])}) —")
                take = groups[tag][:LIST_LIMIT - shown]
                lines += take
                shown += len(take)
        embed = {"title": f"📋 Lịch sử {day_label(day)}", "color": COLOR,
                 "description": _table(lines, len(rows) - shown),
                 "footer": {"text": f"{stats['total']} xe · vào {stats['in']} · ra {stats['out']} · "
                                    f"thu {money(stats['money'])}"}}
        return embed, (csv_name(day), csv_bytes(rows, self.fee_of)) if rows else None

    def card_history(self, card, count):
        rows = self.storage.search(card=card, limit=200)
        rows = [r for r in rows if r["so_the"] == card][:count]   # search tìm theo 1 phần số thẻ
        if not rows:
            return {"title": f"🔎 Thẻ {card}", "color": COLOR, "description": "Chưa có lượt gửi nào với thẻ này."}, []
        lines = []
        for r in rows:
            amount, estimate = self.fee_of(r)
            state = "ĐANG GỬI" if r["gio_ra"] is None else "đã ra"
            lines.append(f"**{vn_time(r['gio_vao'])}** → {vn_time(r['gio_ra']) if r['gio_ra'] else '—'}\n"
                         f"　{record_duration(r)} · {money(amount)}{' (tạm tính)' if estimate else ''} · {state}")
        latest = rows[0]
        photos = [(f"the{card}_vao.jpg", self.storage.abs_path(latest["anh_vao"])) if latest["anh_vao"] else None,
                  (f"the{card}_ra.jpg", self.storage.abs_path(latest["anh_ra"])) if latest["anh_ra"] else None]
        embed = {"title": f"🔎 Thẻ {card} — {len(rows)} lượt gần nhất", "color": COLOR,
                 "description": "\n".join(lines)[:4000],
                 "footer": {"text": "Ảnh đính kèm là ảnh vào / ra của lượt gần nhất"}}
        return embed, [(name, str(path)) for name, path in filter(None, photos) if Path(path).is_file()]

    def parked(self):
        rows = self.storage.list_parked()
        lines = [_line(r) for r in rows[:LIST_LIMIT]]
        total = sum(self.fee_of(r)[0] for r in rows)
        embed = {"title": f"🅿️ Đang gửi: {len(rows)} xe", "color": COLOR,
                 "description": _table(lines, max(0, len(rows) - LIST_LIMIT)),
                 "footer": {"text": f"Tiền tạm tính nếu tất cả ra bây giờ: {money(total)}"}}
        return embed, ("xe_dang_gui.csv", csv_bytes(rows, self.fee_of)) if len(rows) > LIST_LIMIT else None


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

        def to_files(attachment):
            return [discord.File(io.BytesIO(data), filename=name) for name, data in attachment]

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

        async def reply(inter, embed, files=()):
            await inter.followup.send(embed=discord.Embed.from_dict(embed), files=list(files))

        @tree.command(name="thongke", description="Thống kê xe vào / ra và tiền thu của 1 ngày")
        @app_commands.describe(ngay="Ngày cần xem, vd 31/10/2026 hoặc hôm qua (để trống = hôm nay)")
        async def thongke(inter: discord.Interaction, ngay: str = ""):
            if await guard(inter) and (day := await day_arg(inter, ngay)):
                embed, csv = await self._ask(lambda: q.day_report(day))
                await reply(inter, embed, to_files([csv] if csv else []))

        @tree.command(name="lichsu", description="Danh sách từng lượt xe trong 1 ngày")
        @app_commands.describe(ngay="Ngày cần xem, vd 31/10/2026 hoặc hôm qua (để trống = hôm nay)")
        async def lichsu(inter: discord.Interaction, ngay: str = ""):
            if await guard(inter) and (day := await day_arg(inter, ngay)):
                embed, csv = await self._ask(lambda: q.day_list(day))
                await reply(inter, embed, to_files([csv] if csv else []))

        @tree.command(name="tracuu", description="Lịch sử gửi xe của 1 số thẻ, kèm ảnh lượt gần nhất")
        @app_commands.describe(the="Số thẻ", so_luot="Số lượt gần nhất muốn xem (mặc định 5)")
        async def tracuu(inter: discord.Interaction, the: str, so_luot: app_commands.Range[int, 1, 20] = 5):
            if not await guard(inter):
                return
            card = the.strip()
            if not card.isdigit():
                await inter.followup.send("Số thẻ chỉ gồm chữ số.")
                return
            embed, photos = await self._ask(lambda: q.card_history(card, so_luot))
            await reply(inter, embed, [discord.File(path, filename=name) for name, path in photos])

        @tree.command(name="danggui", description="Các xe đang gửi trong bãi")
        async def danggui(inter: discord.Interaction):
            if await guard(inter):
                embed, csv = await self._ask(q.parked)
                await reply(inter, embed, to_files([csv] if csv else []))

        @tree.error
        async def on_error(inter, error):
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
