from typing import List, Dict, Optional
import requests
import json
import logging
from datetime import datetime
import pytz
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OddsAPI:
    """Handles all interactions with The Odds API"""
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://api.the-odds-api.com/v4"
        
    def _get_api_key(self) -> str:
        """Get API key from environment or streamlit secrets"""
        api_key = os.getenv('API_KEY')
        if api_key:
            return api_key
            
        try:
            import streamlit as st
            return st.secrets["API_KEY"]
        except:
            raise Exception("No API key found in environment or streamlit secrets")
    
    def get_nfl_spreads(self, sport_key: str = "americanfootball_nfl") -> List[Dict]:
        """
        Fetch NFL spreads from The Odds API
        Args:
            sport_key: Either "americanfootball_nfl" or "americanfootball_nfl_preseason"
        """
        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "spreads",
            "oddsFormat": "decimal"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError(f"Unexpected API response format: {data}")
                
            logger.info(f"Successfully fetched {len(data)} {sport_key} games from API")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching {sport_key} spreads: {str(e)}")
            return []
    
    def save_sample_response(self, data: List[Dict], filepath: str) -> None:
        """Save API response for testing/development"""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved sample response to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save sample response: {str(e)}")
            raise
    def get_game_scores(self, sport_key: str = "americanfootball_nfl") -> List[Dict]:
        """
        Fetch game scores from The Odds API
        Args:
            sport_key: Either "americanfootball_nfl" or "americanfootball_nfl_preseason"
        """
        url = f"{self.base_url}/sports/{sport_key}/scores"
        params = {
            "apiKey": self.api_key,
            "daysFrom": 3
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                raise ValueError(f"Unexpected API response format: {data}")
            
            processed_data = []
            for game in data:
                if game.get('completed', False):
                    # Extract scores from the new format
                    home_score = next(int(s['score']) for s in game['scores'] 
                                    if s['name'] == game['home_team'])
                    away_score = next(int(s['score']) for s in game['scores'] 
                                    if s['name'] == game['away_team'])
                    
                    processed_data.append({
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'scores_home': home_score,
                        'scores_away': away_score,
                        'completed': True,
                        'sport_key': sport_key,
                        'commence_time': game['commence_time'],
                        'last_update': game['last_update']
                    })
            
            logger.info(f"Successfully fetched {len(processed_data)} completed {sport_key} game scores")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching {sport_key} scores: {str(e)}")
            return []
        
    def get_raw_nfl_data(self) -> dict:
        """Get raw NFL data from API for testing"""
        url = f"{self.base_url}/sports/americanfootball_nfl/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "spreads",
            "oddsFormat": "decimal"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    def get_completed_games(self, sport_key: str = "americanfootball_nfl_preseason") -> List[Dict]:
        """Fetch completed games from yesterday"""
        url = f"{self.base_url}/sports/{sport_key}/scores"
        params = {
            "apiKey": self.api_key,
            "daysFrom": 1,  # Just yesterday's games
            "completed": True  # Only completed games
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Log the raw response for debugging
            logger.debug(f"Raw API response: {json.dumps(data, indent=2)}")
            
            processed_data = []
            for game in data:
                if game.get('completed', False):
                    processed_data.append({
                        'home_team': game.get('home_team'),
                        'away_team': game.get('away_team'),
                        'scores_home': int(game.get('scores', {}).get('home', 0)),
                        'scores_away': int(game.get('scores', {}).get('away', 0)),
                        'completed': True,
                        'commence_time': game.get('commence_time'),
                        'sport_key': sport_key
                    })
            
            logger.info(f"Found {len(processed_data)} completed {sport_key} games")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching completed games: {str(e)}")
            return []

def main():
    """Development testing function"""
    api = OddsAPI()
    try:
        data = api.get_nfl_spreads()
        api.save_sample_response(data, "tests/fixtures/weekly_spreads_sample.json")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()