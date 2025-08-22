import requests
from datetime import datetime
import pytz
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_game_day() -> bool:
    """Check if there are any NFL games today"""
    try:
        api_key = os.getenv('API_KEY')
        if not api_key:
            logger.error("No API key found")
            return False

        # Get current date in ET (NFL's timezone)
        et_tz = pytz.timezone('America/New_York')
        today = datetime.now(et_tz).date()
        
        # Query the API for today's games
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores"
        params = {
            "apiKey": api_key,
            "daysFrom": 0,
            "daysTo": 0
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        games = response.json()
        
        # Check if any games start today
        has_games = any(
            datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            .astimezone(et_tz)
            .date() == today
            for game in games
        )
        
        logger.info(f"Game day check: {'Yes' if has_games else 'No'} games today")
        # Print 'true' or 'false' for GitHub Actions
        print('true' if has_games else 'false')
        return has_games
        
    except Exception as e:
        logger.error(f"Error checking game day: {str(e)}")
        print('false')  # Default to false on error
        return False

if __name__ == "__main__":
    is_game_day()