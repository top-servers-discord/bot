import asyncio
import sys

import structlog

from bot.client import TSDBot
from bot.config import get_settings

log = structlog.get_logger()


async def main() -> None:
    settings = get_settings()
    if not settings.discord_token:
        log.error("missing DISCORD_TOKEN")
        sys.exit(1)

    bot = TSDBot()
    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass
    asyncio.run(main())
