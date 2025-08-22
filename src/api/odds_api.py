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
    
    def get_nfl_spreads(self, bookmaker: str = "DraftKings") -> List[Dict]:
        """Fetch NFL spreads from The Odds API"""
        url = f"{self.base_url}/sports/americanfootball_nfl/odds"
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
                
            logger.info(f"Successfully fetched {len(data)} games from API")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode API response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
    
    def save_sample_response(self, data: List[Dict], filepath: str) -> None:
        """Save API response for testing/development"""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved sample response to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save sample response: {str(e)}")
            raise
    def get_game_scores(self) -> List[Dict]:
        """Fetch raw game scores from The Odds API"""
        url = f"{self.base_url}/sports/americanfootball_nfl/scores"
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
            
            # Transform data to ensure consistent format
            processed_data = []
            for game in data:
                processed_data.append({
                    'home_team': game.get('home_team'),
                    'away_team': game.get('away_team'),
                    'scores_home': int(game.get('scores', {}).get('home', 0)),
                    'scores_away': int(game.get('scores', {}).get('away', 0))
                })
                
            logger.info(f"Successfully fetched {len(processed_data)} game scores from API")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching game scores: {str(e)}")
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