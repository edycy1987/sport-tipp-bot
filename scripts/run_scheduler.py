import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.db import init_db, session_scope
from app.collectors.odds_api import collect_and_store
from app.models import Match, Tip
from app.engine.scoring import evaluate_match
from app.bot.notifier import send_slip

log = logging.getLogger(__name__)

async def job_collect():
    try:
        log.info("Háttér adatgyűjtés indul...")
        await collect_and_store()
    except Exception as e:
        log.exception("Hiba a gyűjtéskor: %s", e)

async def job_tips():
    now = datetime.utcnow()
    soon = now + timedelta(minutes=55)
    later = now + timedelta(minutes=65)
    
    with session_scope() as s:
        matches = s.query(Match).filter(
            Match.kickoff >= soon, Match.kickoff <= later
        ).all()

        for m in matches:
            existing_sent = s.query(Tip).filter_by(match_id=m.id, sent=True).first()
            if existing_sent:
                continue

            tips_data = evaluate_match(m)
            if not tips_data: continue

            best_tip = max(tips_data, key=lambda x: x["value"])
            
            if best_tip["confidence"] >= settings.TIP_MIN_CONFIDENCE and best_tip["value"] >= settings.TIP_MIN_EV:
                leg = dict(
                    match_id=m.id, market=best_tip["market"], pick=best_tip["pick"],
                    odd=best_tip["odd"], confidence=best_tip["confidence"], value=best_tip["value"],
                    home=m.home, away=m.away, kickoff=m.kickoff,
                    reason=best_tip.get("reason", "")
                )
                
                log.info(f"1 órán belül kezdődő meccs tippje elküldve: {m.home} - {m.away}")
                await send_slip([leg], leg["odd"])
                
                t = Tip(match_id=m.id, market=best_tip["market"], pick=best_tip["pick"],
                        odd=best_tip["odd"], confidence=best_tip["confidence"], value=best_tip["value"], sent=True)
                s.add(t)
                s.commit()

async def main():
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    sch = AsyncIOScheduler()
    
    sch.add_job(job_collect, "interval", hours=6, next_run_time=datetime.now())
    sch.add_job(job_tips, "interval", minutes=15)
    
    sch.start()
    log.info("Scheduler fut. 6 óránként gyűjt, és 1 órával meccs előtt tippel.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
