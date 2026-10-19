import logging
from aiogram import Bot
from app.config import settings
from app.bot.formatters import format_slip

log = logging.getLogger(__name__)

async def send_slip(legs: list[dict], total: float):
    if not settings.TELEGRAM_CHANNEL_ID:
        return
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=settings.TELEGRAM_CHANNEL_ID,
            text=format_slip(legs, total),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    finally:
        await bot.session.close()
