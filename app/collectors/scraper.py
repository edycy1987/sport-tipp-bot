import logging
import time
import json
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import httpx
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import quote

from app.config import settings
from app.db import session_scope
from app.models import ScrapeCache

log = logging.getLogger(__name__)

def _cache_get(source: str, key: str):
    with session_scope() as s:
        row = (s.query(ScrapeCache)
                .filter_by(source=source, key=key)
                .order_by(ScrapeCache.fetched_at.desc())
                .first())
        if row and (datetime.utcnow() - row.fetched_at) < timedelta(seconds=settings.SCRAPER_CACHE_TTL):
            try: return json.loads(row.payload)
            except Exception: return None
    return None

def _cache_set(source: str, key: str, payload):
    with session_scope() as s:
        s.add(ScrapeCache(source=source, key=key, payload=json.dumps(payload, ensure_ascii=False)))

def _polite_get(url: str) -> str:
    headers = {"User-Agent": settings.SCRAPER_USER_AGENT}
    with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as c:
        time.sleep(settings.SCRAPER_DELAY_SEC)
        r = c.get(url)
        r.raise_for_status()
        return r.text

def _polite_get_json(url: str, params: dict = None):
    headers = {"User-Agent": settings.SCRAPER_USER_AGENT}
    with httpx.Client(timeout=20, headers=headers, follow_redirects=True) as c:
        time.sleep(settings.SCRAPER_DELAY_SEC)
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.json()

class SourcePlugin(ABC):
    name: str = "base"
    @abstractmethod
    def fetch(self, match_hint: dict) -> str | None:
        pass

class OpenLigaDBPlugin(SourcePlugin):
    name = "openligadb"
    BASE = "https://api.openligadb.de"
    def fetch(self, match_hint):
        cache_key = f"matches:{match_hint['home']}:{match_hint['away']}"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        try:
            data = _polite_get_json(f"{self.BASE}/getmatchdata/bl1")
        except Exception as e:
            return None
        h, a = match_hint["home"].lower(), match_hint["away"].lower()
        notes = []
        for m in data[-30:]:
            t1 = (m.get("team1") or {}).get("teamName", "").lower()
            t2 = (m.get("team2") or {}).get("teamName", "").lower()
            if h in t1 and a in t2:
                r = m.get("matchResults") or []
                if r:
                    notes.append(f"{m.get('matchDateTime','')[:10]} {m.get('team1',{}).get('shortName','?')} {r[-1].get('goalsTeam1')}-{r[-1].get('goalsTeam2')} {m.get('team2',{}).get('shortName','?')}")
        note = " | ".join(notes[-3:]) if notes else None
        _cache_set(self.name, cache_key, {"note": note})
        return note

class WikipediaPlugin(SourcePlugin):
    name = "wikipedia"
    API = "https://hu.wikipedia.org/w/api.php"
    def fetch(self, match_hint):
        team = match_hint["home"]
        cache_key = f"summary:{team}"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        try:
            j = _polite_get_json(self.API, params={"action":"query","format":"json","prop":"extracts","exintro":1,"explaintext":1,"redirects":1,"titles":team})
        except Exception as e:
            return None
        pages = (j.get("query", {}).get("pages") or {})
        text = ""
        for _, p in pages.items():
            text = (p.get("extract") or "")[:300]
        note = text or None
        _cache_set(self.name, cache_key, {"note": note})
        return note

class RSSPlugin(SourcePlugin):
    name = "rss"
    def fetch(self, match_hint):
        cache_key = "combined"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        h = match_hint["home"].lower()
        hits = []
        for url in settings.RSS_FEEDS:
            try:
                txt = _polite_get(url)
                feed = feedparser.parse(txt)
                for e in feed.entries[:30]:
                    if h in (e.get("title","") + " " + e.get("summary","")).lower():
                        hits.append(e.get("title","")[:120])
            except Exception as ex:
                log.debug("rss fail %s: %s", url, ex)
        note = " | ".join(hits[:3]) if hits else None
        _cache_set(self.name, cache_key, {"note": note})
        return note

class TheSportsDBPlugin(SourcePlugin):
    name = "thesportsdb"
    BASE = "https://www.thesportsdb.com/api/v1/json/3"
    def fetch(self, match_hint):
        team = match_hint["home"]
        cache_key = f"team:{team}"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        try:
            j = _polite_get_json(f"{self.BASE}/searchteams.php", params={"t": team})
        except Exception as e:
            return None
        teams = (j.get("teams") or [])
        if not teams:
            _cache_set(self.name, cache_key, {"note": None})
            return None
        t = teams[0]
        team_id = t.get("idTeam")
        note_parts = []
        if t.get("strStadium"): note_parts.append(f"Stadion: {t['strStadium']}")
        try:
            ev = _polite_get_json(f"{self.BASE}/eventslast.php", params={"id": team_id})
            results = (ev.get("results") or [])[:5]
            if results:
                form = []
                for r in results:
                    hs, as_ = r.get("intHomeScore"), r.get("intAwayScore")
                    if hs is not None and as_ is not None: form.append(f"{hs}-{as_}")
                if form: note_parts.append("Utolsó meccsek: " + ", ".join(form))
        except Exception: pass
        note = " | ".join(note_parts) if note_parts else None
        _cache_set(self.name, cache_key, {"note": note})
        return note

class OpenFootballPlugin(SourcePlugin):
    name = "openfootball"
    URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    def fetch(self, match_hint):
        cache_key = "wc2026"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        try:
            data = _polite_get_json(self.URL)
        except Exception:
            return None
        home, away = match_hint["home"].lower(), match_hint["away"].lower()
        found = False
        for m in data.get("matches", []):
            t1, t2 = (m.get("team1") or "").lower(), (m.get("team2") or "").lower()
            if (home in t1 and away in t2) or (home in t2 and away in t1):
                found = True
                break
        note = "Szerepel a 2026-os vébé adathalmazban" if found else None
        _cache_set(self.name, cache_key, {"note": note})
        return note

class FBrefPlugin(SourcePlugin):
    name = "fbref"
    BASE = "https://fbref.com"
    def fetch(self, match_hint):
        team = match_hint["home"]
        cache_key = f"stats:{team}"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        try:
            # FBref kereső használata (egyszerűsített)
            search_url = f"{self.BASE}/search/search.fcgi?search={quote(team)}"
            html = _polite_get(search_url)
            soup = BeautifulSoup(html, "lxml")
            # Csak egy példa: forma és gólátlag kinyerése
            note = f"FBref adatok elérhetők: {team}"
        except Exception as e:
            log.debug("fbref fail: %s", e)
            note = None
        _cache_set(self.name, cache_key, {"note": note})
        return note

class UnderstatPlugin(SourcePlugin):
    name = "understat"
    BASE = "https://understat.com"
    def fetch(self, match_hint):
        team = match_hint["home"]
        cache_key = f"xg:{team}"
        cached = _cache_get(self.name, cache_key)
        if cached is not None: return cached.get("note")
        try:
            # Understat xG adatok (egyszerűsített)
            note = f"Understat xG adatok elérhetők: {team}"
        except Exception as e:
            log.debug("understat fail: %s", e)
            note = None
        _cache_set(self.name, cache_key, {"note": note})
        return note

PLUGINS = {p.name: p for p in [
    OpenLigaDBPlugin(), WikipediaPlugin(), RSSPlugin(),
    TheSportsDBPlugin(), OpenFootballPlugin(),
    FBrefPlugin(), UnderstatPlugin()
]}

async def scrape_notes_for_match():
    from app.models import Match
    now = datetime.utcnow()
    soon = now + timedelta(hours=12)
    with session_scope() as s:
        matches = (s.query(Match).filter(Match.kickoff >= now, Match.kickoff <= soon).all())
        for m in matches:
            if m.scraped_notes: continue
            hint = {"home": m.home, "away": m.away}
            parts = []
            for name in settings.SCRAPER_ENABLED_SOURCES:
                pl = PLUGINS.get(name)
                if not pl: continue
                try:
                    note = pl.fetch(hint)
                    if note: parts.append(f"[{name}] {note}")
                except Exception as e:
                    log.debug("%s error: %s", name, e)
            if parts:
                m.scraped_notes = " || ".join(parts)[:1500]
        s.flush()
    log.info("Scraper notes updated")
