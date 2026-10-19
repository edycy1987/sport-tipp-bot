from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    ext_id = Column(String, unique=True, index=True, nullable=False)
    sport = Column(String, default="football")
    league = Column(String)
    home = Column(String)
    away = Column(String)
    kickoff = Column(DateTime, index=True)
    odds_home = Column(Float)
    odds_draw = Column(Float)
    odds_away = Column(Float)
    odds_over25 = Column(Float)
    odds_under25 = Column(Float)
    collected_at = Column(DateTime, default=datetime.utcnow)
    scraped_notes = Column(Text, nullable=True)
    tips = relationship("Tip", back_populates="match", cascade="all, delete-orphan")

class Tip(Base):
    __tablename__ = "tips"
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    market = Column(String)
    pick = Column(String)
    odd = Column(Float)
    confidence = Column(Float)
    value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent = Column(Boolean, default=False)
    match = relationship("Match", back_populates="tips")

class ScrapeCache(Base):
    __tablename__ = "scrape_cache"
    id = Column(Integer, primary_key=True)
    source = Column(String, index=True)
    key = Column(String, index=True)
    payload = Column(Text)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
