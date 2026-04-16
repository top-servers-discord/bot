from __future__ import annotations

import httpx
import structlog

from bot.config import get_settings
from bot.ingest.schema import DiscordEvent

log = structlog.get_logger()

_INSERT_QUERY = "INSERT INTO tsd.events FORMAT JSONEachRow"


class ClickHouseClient:
    """Async HTTP client for ClickHouse batch inserts."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.clickhouse_url
        self._auth = ("tsd", settings.clickhouse_password)
        self._client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def insert_events(self, events: list[DiscordEvent]) -> None:
        """Batch INSERT events via the HTTP interface using JSONEachRow format."""
        if not events:
            return

        if self._client is None:
            raise RuntimeError("ClickHouseClient is not open; call open() first")

        body = "\n".join(
            event.model_dump_json() for event in events
        )

        resp = await self._client.post(
            "/",
            params={"query": _INSERT_QUERY},
            content=body.encode(),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        log.debug("clickhouse.insert_ok", count=len(events))
