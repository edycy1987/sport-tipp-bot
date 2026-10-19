import logging
from datetime import datetime
import httpx
from app.config import settings
from app.db import session_scope
from app.models import Match

log = logging.getLogger(__name__)

async def fetch_odds_for_sport(sport_key: str):
    url = f"{settings.ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": settings.ODDS_API_KEY,
        "regions": settings.ODDS_REGIONS,
        "markets": settings.ODDS_MARKETS,
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.get(url, params=params)
        if r.status_code != 200:
            log.warning(f"Hiba a(z) {sport_key} lekérésekor: {r.status_code}")
            return []
        return r.json()

def _norm_odds(event: dict):
    h = d = a = o25 = u25 = None
    for bm in event.get("bookmakers", []):
        for m in bm.get("markets", []):
            if m["key"] == "h2h":
                for o in m.get("outcomes", []):
                    if o["name"] == event["home_team"]: h = o["price"]
                    elif o["name"] == event["away_team"]: a = o["price"]
                    elif o["name"].lower() == "draw": d = o["price"]
            elif m["key"] == "totals":
                for o in m.get("outcomes", []):
                    if o.get("point") == 2.5:
                        if o["name"].lower() == "over": o25 = o["price"]
                        elif o["name"].lower() == "under": u25 = o["price"]
        if h and a:
            break
    return h, d, a, o25, u25

async def collect_and_store():
    from app.collectors.scraper import scrape_notes_for_match
    all_rows = []
    
    for sport_key in settings.ODDS_SPORT_KEYS:
        raw = await fetch_odds_for_sport(sport_key)
        log.info(f"{sport_key}: {len(raw)} event")
        
        for ev in raw:
            h, d, a, o25, u25 = _norm_odds(ev)
            if not (h and a): continue
            all_rows.append(dict(
                ext_id=f"oa:{ev['id']}",
                league=ev.get("sport_title") or "",
                home=ev["home_team"], away=ev["away_team"],
                kickoff=datetime.fromisoformat(ev["commence_time"].replace("Z","+00:00")).replace(tzinfo=None),
                odds_home=h, odds_draw=d, odds_away=a,
                odds_over25=o25, odds_under25=u25
            ))

    with session_scope() as s:
        for r in all_rows:
            m = s.query(Match).filter_by(ext_id=r["ext_id"]).one_or_none()
            if m is None:
                m = Match(**r)
                s.add(m)
            else:
                for k, v in r.items():
                    setattr(m, k, v)
        s.flush()
    log.info("Összesen elmentve/frissítve: %d meccs", len(all_rows))

    try:
        await scrape_notes_for_match()
    except Exception as e:
        log.warning("Scraper notes skipped: %s", e)
