from __future__ import annotations

import asyncio

import structlog

from bot.ingest.clickhouse_client import ClickHouseClient
from bot.ingest.schema import DiscordEvent

log = structlog.get_logger()

_FLUSH_INTERVAL: float = 5.0
_BATCH_SIZE: int = 500
_MAX_QUEUE_SIZE: int = 10_000
_MAX_RETRIES: int = 3
_BASE_BACKOFF: float = 1.0


class EventEmitter:
    """In-memory async buffer that batches events into ClickHouse."""

    def __init__(self, ch_client: ClickHouseClient) -> None:
        self._ch = ch_client
        self._queue: asyncio.Queue[DiscordEvent] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        self._flush_task: asyncio.Task[None] | None = None

    def emit(self, event: DiscordEvent) -> None:
        """Put an event on the queue. Drops if the queue is full."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("emitter.queue_full", event_type=event.event_type, guild_id=event.guild_id)

    def start(self) -> None:
        """Start the background flush loop."""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop(), name="event-flush")

    async def stop(self) -> None:
        """Cancel the flush loop and drain remaining events."""
        if self._flush_task is not None and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush_once()

    async def _flush_loop(self) -> None:
        """Periodically drain the queue and insert into ClickHouse."""
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            await self._flush_once()

    async def _flush_once(self) -> None:
        """Drain up to _BATCH_SIZE events and insert them."""
        batch: list[DiscordEvent] = []
        while len(batch) < _BATCH_SIZE:
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not batch:
            return

        for attempt in range(_MAX_RETRIES):
            try:
                await self._ch.insert_events(batch)
                return
            except Exception:
                wait = _BASE_BACKOFF * (2 ** attempt)
                log.warning(
                    "emitter.flush_retry",
                    attempt=attempt + 1,
                    batch_size=len(batch),
                    backoff=wait,
                )
                await asyncio.sleep(wait)

        log.error("emitter.flush_failed", dropped=len(batch))
