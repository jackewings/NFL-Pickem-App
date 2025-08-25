from pathlib import Path
from typing import Dict, Any
import pytz

API_ENDPOINTS = {
    "scores": "/sports/americanfootball_nfl/scores"
    }


# Project paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / ".cache"

# Data files
SPREADS_FILE = DATA_DIR / "weekly_spreads.csv"
PICKS_FILE = DATA_DIR / "picks.csv"
RESULTS_FILE = DATA_DIR / "results.csv"

# API Configuration
API_BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_BOOKMAKER = "DraftKings"
API_MARKETS = ["spreads"]
API_REGIONS = ["us"]
ODDS_FORMAT = "decimal"

# Time settings
TIMEZONE = "America/Chicago"
TIMEZONES = {
    "ET": pytz.timezone("US/Eastern"),
    "CT": pytz.timezone("US/Central"),
    "MT": pytz.timezone("US/Mountain"),
    "PT": pytz.timezone("US/Pacific"),
}
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %I:%M %p %Z"

# NFL Game settings
NFL_SEASON_YEAR = 2025
SEASON_START = f"{NFL_SEASON_YEAR}-09-05"
SEASON_END = f"{NFL_SEASON_YEAR + 1}-01-08"

# NFL Team Settings
NFL_TEAM_COLORS = {
    "Arizona Cardinals": "#97233F",
    "Atlanta Falcons": "#A71930",
    "Baltimore Ravens": "#241773",
    "Buffalo Bills": "#00338D",
    "Carolina Panthers": "#0085CA",
    "Chicago Bears": "#0B162A",
    "Cincinnati Bengals": "#FB4F14",
    "Cleveland Browns": "#311D00",
    "Dallas Cowboys": "#003594",
    "Denver Broncos": "#FB4F14",
    "Detroit Lions": "#0076B6",
    "Green Bay Packers": "#203731",
    "Houston Texans": "#03202F",
    "Indianapolis Colts": "#002C5F",
    "Jacksonville Jaguars": "#006778",
    "Kansas City Chiefs": "#E31837",
    "Las Vegas Raiders": "#000000",
    "Los Angeles Chargers": "#0080C6",
    "Los Angeles Rams": "#003594",
    "Miami Dolphins": "#008E97",
    "Minnesota Vikings": "#4F2683",
    "New England Patriots": "#002244",
    "New Orleans Saints": "#D3BC8D",
    "New York Giants": "#0B2265",
    "New York Jets": "#125740",
    "Philadelphia Eagles": "#004C54",
    "Pittsburgh Steelers": "#FFB612",
    "San Francisco 49ers": "#AA0000",
    "Seattle Seahawks": "#002244",
    "Tampa Bay Buccaneers": "#D50A0A",
    "Tennessee Titans": "#0C2340",
    "Washington Commanders": "#773141"
}

TEAM_NAME_MAPPING = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WSH": "Washington Commanders"
}

TEAM_DISPLAY_NAMES = {
    "Arizona Cardinals": "Cardinals",
    "Atlanta Falcons": "Falcons",
    "Baltimore Ravens": "Ravens",
    "Buffalo Bills": "Bills",
    "Carolina Panthers": "Panthers",
    "Chicago Bears": "Bears",
    "Cincinnati Bengals": "Bengals",
    "Cleveland Browns": "Browns",
    "Dallas Cowboys": "Cowboys",
    "Denver Broncos": "Broncos",
    "Detroit Lions": "Lions",
    "Green Bay Packers": "Packers",
    "Houston Texans": "Texans",
    "Indianapolis Colts": "Colts",
    "Jacksonville Jaguars": "Jaguars",
    "Kansas City Chiefs": "Chiefs",
    "Las Vegas Raiders": "Raiders",
    "Los Angeles Chargers": "Chargers",
    "Los Angeles Rams": "Rams",
    "Miami Dolphins": "Dolphins",
    "Minnesota Vikings": "Vikings",
    "New England Patriots": "Patriots",
    "New Orleans Saints": "Saints",
    "New York Giants": "Giants",
    "New York Jets": "Jets",
    "Philadelphia Eagles": "Eagles",
    "Pittsburgh Steelers": "Steelers",
    "San Francisco 49ers": "49ers",
    "Seattle Seahawks": "Seahawks",
    "Tampa Bay Buccaneers": "Buccaneers",
    "Tennessee Titans": "Titans",
    "Washington Commanders": "Commanders"
}

# Current week calculation
from datetime import datetime
def get_current_week():
    """Calculate current NFL week based on date"""
    today = datetime.now().date()
    start = datetime.strptime(SEASON_START, "%Y-%m-%d").date()
    
    if today < start:
        return 1
        
    week_delta = ((today - start).days // 7) + 1
    return min(week_delta, 18)  # Cap at week 18

CURRENT_WEEK = get_current_week()

# App settings
APP_NAME = "NFL Pick'em"
DEFAULT_WEEK = 1
PICKS_DEADLINE_HOURS = 1  # Hours before game time
MAX_PICKS_PER_WEEK = 16

# User settings
USERS = [
    "Gabe",
    "Jack",
    "Jake",
    "Trapp"
]

# Cache settings
CACHE_TIMEOUT = 3600  # 1 hour in seconds
CACHE_ENABLED = True

# Logging configuration
LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "app.log"),
            "formatter": "standard",
            "level": "INFO"
        }
    },
    "loggers": {
        "": {  
            "handlers": ["console", "file"],
            "level": "INFO",
        }
    }
}

# User interface settings
UI_THEME = "light"
DISPLAY_ITEMS_PER_PAGE = 20
REFRESH_INTERVAL = 300  # 5 minutes in seconds

# Development settings
DEBUG = False
TESTING = False

def get_env_settings():
    """Load environment-specific settings"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv(BASE_DIR / ".env")
    
    return {
        "API_KEY": os.getenv("API_KEY"),
        "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
        "TESTING": os.getenv("TESTING", "false").lower() == "true",
    }

# Update settings with environment variables
globals().update(get_env_settings())