import time
from aiogram import Bot
from typing import Optional

class AdminAlerter:
    def __init__(self, bot: Bot, cfg):
        self.bot = bot
        self.cfg = cfg
        self._last_sent = {}  # key -> timestamp

    def _should_send(self, key: str) -> bool:
        now = time.time()
        last = self._last_sent.get(key, 0)
        if now - last >= self.cfg.ADMIN_ALERTS_DEBOUNCE_SEC:
            self._last_sent[key] = now
            return True
        return False

    def _mask_url(self, url: str) -> str:
        if not self.cfg.MASK_URLS_IN_ALERTS: return url
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            path = p.path
            if len(path) > 24:
                path = path[:24] + "..."
            return f"{p.scheme}://{p.netloc}{path}"
        except:
            return (url or "")[:28] + "..."

    async def send_error(self, error_name: str, summary: str, url: Optional[str]=None,
                         user_id: Optional[int]=None, username: Optional[str]=None,
                         trace_id: Optional[str]=None, worker: Optional[str]=None,
                         job_age: Optional[float]=None):
        if not self.cfg.ADMIN_ALERTS_ENABLED: return
        # level filtering: we treat this as "error" level
        if self.cfg.ADMIN_ALERTS_LEVEL not in ("error", "warn", "info", "critical"):
            return

        key = f"err:{error_name}:{self._mask_url(url)}"
        if not self._should_send(key):
            return

        msg = (
            f"❌ خطا | {error_name}\n"
            f"trace: {trace_id or '-'} | user: {user_id or '-'} ({('@'+username) if username else '-'})\n"
            f"url: {self._mask_url(url)}\n"
            f"علت: {summary}\n"
            f"صف: age={int(job_age) if job_age else '-'}s"
        )
        await self._send_to_admins(msg)

    async def send_critical(self, name: str, summary: str, extra: str=""):
        if not self.cfg.ADMIN_ALERTS_ENABLED: return
        if self.cfg.ADMIN_ALERTS_LEVEL not in ("critical","error","warn","info"):
            return
        key = f"crit:{name}"
        if not self._should_send(key):
            return
        msg = f"🚨 بحرانی | {name}\n{summary}\n{extra}"
        await self._send_to_admins(msg)

    async def send_warn(self, name: str, summary: str, url: Optional[str]=None):
        if not self.cfg.ADMIN_ALERTS_ENABLED: return
        allowed = self.cfg.ADMIN_ALERTS_LEVEL in ("warn","info") or self.cfg.ADMIN_ALERTS_LEVEL=="critical" or self.cfg.ADMIN_ALERTS_LEVEL=="error"
        # We only send warn if level is warn or info; for simplicity, require level to be 'warn' or 'info'
        if self.cfg.ADMIN_ALERTS_LEVEL not in ("warn","info"):
            return
        key = f"warn:{name}:{self._mask_url(url)}"
        if not self._should_send(key):
            return
        msg = f"⚠️ هشدار | {name}\n{summary}\n{self._mask_url(url) if url else ''}"
        await self._send_to_admins(msg)

    async def _send_to_admins(self, text: str):
        # destination: dm or group
        if self.cfg.ADMIN_ALERTS_DESTINATION == "group" and self.cfg.ADMIN_ALERTS_GROUP_ID:
            try:
                await self.bot.send_message(chat_id=int(self.cfg.ADMIN_ALERTS_GROUP_ID), text=text)
                return
            except Exception:
                pass
        for uid in self.cfg.admin_ids:
            try:
                await self.bot.send_message(chat_id=uid, text=text)
            except Exception:
                continue
