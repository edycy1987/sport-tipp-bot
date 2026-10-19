import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.config import settings
from app.bot.formatters import format_slip
from app.engine.pipeline import get_todays_slip

log = logging.getLogger(__name__)
router = Router()

def is_allowed(uid: int) -> bool:
    return uid in settings.ALLOWED_USER_IDS

@router.message(Command("start"))
async def cmd_start(m: Message):
    if not is_allowed(m.from_user.id):
        await m.answer("🔒 Privát bot.")
        return
    await m.answer(
        "<b>Szia!</b>\n"
        "/tipp – mai szelvény\n"
        "/refresh – újraszámolás\n"
        "/stats – rövid infó\n"
    )

@router.message(Command("tipp"))
async def cmd_tipp(m: Message):
    if not is_allowed(m.from_user.id):
        return
    await m.answer("⏳ Számolok…")
    legs, total = get_todays_slip()
    await m.answer(format_slip(legs, total), parse_mode="HTML", disable_web_page_preview=True)

@router.message(Command("refresh"))
async def cmd_refresh(m: Message):
    if not is_allowed(m.from_user.id):
        return
    legs, total = get_todays_slip()
    await m.answer("✅ Frissítve.\n" + format_slip(legs, total), parse_mode="HTML")

@router.message(Command("stats"))
async def cmd_stats(m: Message):
    if not is_allowed(m.from_user.id):
        return
    from app.db import session_scope
    from app.models import Match, Tip
    with session_scope() as s:
        total_m = s.query(Match).count()
        total_t = s.query(Tip).count()
        sent = s.query(Tip).filter_by(sent=True).count()
    await m.answer(f"📊 Meccsek: {total_m}\nTippek: {total_t}\nElküldve: {sent}")

@router.message(F.text)
async def fallback(m: Message):
    if is_allowed(m.from_user.id):
        await m.answer("Ismeretlen parancs. /tipp")
