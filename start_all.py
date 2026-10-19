import asyncio
from aiohttp import web
from app.main import main as run_bot
from scripts.run_scheduler import main as run_scheduler
from app.db import init_db
from app.config import settings
import logging

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

async def handle(request):
    return web.Response(text="Tipp Bot is running 24/7!")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # A Render a 10000-es portot várja alapértelmezésként
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    logging.info("Web szerver fut a 10000-es porton.")

async def main():
    init_db()
    asyncio.create_task(start_web())
    asyncio.create_task(run_scheduler())
    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())
