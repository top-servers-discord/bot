from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_serializer


class DiscordEvent(BaseModel):
    ts: datetime
    event_type: str
    guild_id: int
    channel_id: int
    user_hash: str
    extra: str = "{}"

    @model_serializer
    def serialize(self) -> dict:
        return {
            "ts": self.ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "event_type": self.event_type,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "user_hash": self.user_hash,
            "extra": self.extra,
        }
