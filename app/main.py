import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import settings
from app.bot.handlers import router
from app.db import init_db

async def main():
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    logging.info("Bot indul…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
