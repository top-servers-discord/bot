from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DiscordEvent(BaseModel):
    ts: datetime
    event_type: str
    guild_id: int
    channel_id: int
    user_hash: str
    extra: str = "{}"
