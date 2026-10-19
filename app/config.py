import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings:
    ODDS_PROVIDER = "theoddsapi"
    ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
    ODDS_API_BASE = "https://api.the-odds-api.com/v4"
    ODDS_SPORT_KEYS = ["soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a"]
    ODDS_REGIONS = "eu"
    ODDS_MARKETS = "h2h,totals" 

    FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "")
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ALLOWED_USER_IDS = [5525707189]
    TELEGRAM_CHANNEL_ID = str(ALLOWED_USER_IDS[0])
    DB_URL = f"sqlite:///{DATA_DIR/'sport.db'}"

    TIP_MIN_CONFIDENCE = 0.40
    TIP_MIN_EV = -0.20
    TIP_MAX_LEGS = 4
    LOG_LEVEL = "INFO"

settings = Settings()
