"""Async HTTP client for the TopServersDiscord backend API."""

from __future__ import annotations

import hashlib
import hmac
import time

import discord
import httpx
import structlog

from bot.config import get_settings

log = structlog.get_logger()


def _sign(body: bytes, secret: str, timestamp: str) -> str:
    """HMAC-SHA256 signature of timestamp + body."""
    message = f"{timestamp}".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class BackendClient:
    """Thin async wrapper around the internal backend endpoints."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.backend_url.rstrip("/")
        self._secret = settings.backend_hmac_secret
        self._http = httpx.AsyncClient(timeout=10.0)

    # -- helpers ---------------------------------------------------------------

    async def _post(self, path: str, payload: dict) -> httpx.Response:
        import json as _json

        body = _json.dumps(payload).encode()
        timestamp = str(int(time.time()))
        signature = _sign(body, self._secret, timestamp)

        headers = {
            "Content-Type": "application/json",
            "X-TSD-Signature": signature,
            "X-TSD-Timestamp": timestamp,
        }

        url = f"{self._base_url}{path}"
        resp = await self._http.post(url, content=body, headers=headers)
        resp.raise_for_status()
        return resp

    # -- public API ------------------------------------------------------------

    async def notify_guild_joined(
        self,
        guild: discord.Guild,
        *,
        invite_code: str | None = None,
        metadata: dict | None = None,
    ) -> bool:
        """Notify the backend that the bot joined a guild. Returns True on success."""
        # Online count from presences (if available) or approximate
        online_count = 0
        try:
            online_count = sum(
                1 for m in guild.members if m.status != discord.Status.offline and not m.bot
            )
        except Exception:
            online_count = guild.approximate_presence_count or 0

        payload = {
            "guild_id": str(guild.id),
            "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else None,
            "member_count": guild.member_count,
            "online_count": online_count,
            "invite_code": invite_code,
            "metadata": metadata,
        }
        try:
            await self._post("/internal/guild-joined", payload)
            log.info("backend.guild_joined.ok", guild_id=guild.id)
            return True
        except Exception:
            log.exception("backend.guild_joined.failed", guild_id=guild.id)
            return False

    async def notify_guild_left(self, guild_id: int) -> bool:
        """Notify the backend that the bot was removed from a guild. Returns True on success."""
        payload = {"guild_id": str(guild_id)}
        try:
            await self._post("/internal/guild-left", payload)
            log.info("backend.guild_left.ok", guild_id=guild_id)
            return True
        except Exception:
            log.exception("backend.guild_left.failed", guild_id=guild_id)
            return False

    async def fetch_pending_leaves(self) -> list[int]:
        """Consume the queue of guild IDs the bot should leave."""
        try:
            resp = await self._post("/internal/pending-leaves", {})
            data = resp.json()
            return [int(g) for g in data.get("guild_ids", [])]
        except Exception:
            log.exception("backend.pending_leaves.failed")
            return []

    async def close(self) -> None:
        await self._http.aclose()
