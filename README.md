# bot

Discord bot (stats collector) for **TopServersDiscord**.

## What it does

- Joins servers when invited via OAuth2 flow.
- Listens for events (messages, voice, reactions, join/leave) — **no message content**.
- Hashes `user_id` with a per-guild salt and pushes events to Valkey Streams.
- A consumer drains Valkey → ClickHouse in batches.
- Exposes minimal slash commands: `/info`, `/stats`, `/verify`, `/settings`.

## Privacy

- **Does NOT request `message_content` intent.** We never read chat content.
- User IDs are hashed per guild with a rotatable salt.

## Stack

- Python 3.14
- discord.py 2.7.1
- ClickHouse (sink) + Valkey 8 (buffer)
- Sharded via `AutoShardedBot` from day one

## Getting started

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python -m bot
```

## Deployment

Image published to `registry.oxa.gg/tsd-bot`.
Runs as a `StatefulSet` (one pod per shard) in `top-servers-discord` namespace.
