import logging
from datetime import datetime, timedelta
from app.db import session_scope
from app.models import Match, Tip
from app.engine.scoring import evaluate_match
from app.engine.slip_builder import build_slip

log = logging.getLogger(__name__)

def refresh_tips():
    now = datetime.utcnow()
    horizon = now + timedelta(days=7) 
    with session_scope() as s:
        matches = (s.query(Match)
                    .filter(Match.kickoff >= now, Match.kickoff <= horizon)
                    .all())
        all_tips = []
        for m in matches:
            s.query(Tip).filter_by(match_id=m.id, sent=False).delete()
            for e in evaluate_match(m):
                t = Tip(match_id=m.id, market=e["market"], pick=e["pick"],
                        odd=e["odd"], confidence=e["confidence"], value=e["value"])
                s.add(t)
                # Itt adjuk át az elemzést is!
                all_tips.append(dict(match_id=m.id, market=e["market"], pick=e["pick"],
                                     odd=e["odd"], confidence=e["confidence"], value=e["value"],
                                     home=m.home, away=m.away, kickoff=m.kickoff,
                                     analysis=e.get("analysis", "")))
        s.flush()
    log.info("Generated %d raw tips", len(all_tips))
    return all_tips

def get_todays_slip():
    raw = refresh_tips()
    legs, total_odd = build_slip(raw)
    return legs, total_odd
