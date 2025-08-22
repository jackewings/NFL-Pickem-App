from typing import List, Dict, Optional
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import json
from src.utils.time_utils import get_current_time_ct, format_timestamp_ct
from src.utils.schedule import assign_week
from src.api.odds_api import OddsAPI

logger = logging.getLogger(__name__)

class NFLData:
    """Handles NFL data operations including API calls and data storage"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.spreads_file = self.data_dir / "weekly_spreads.csv"
        self.api = OddsAPI()

    def get_weekly_spreads_from_api(
        self, 
        chosen_bookmaker: str = "DraftKings", 
        save_csv: bool = True
    ) -> List[Dict]:
        """
        Fetch NFL spreads from The Odds API for all available games.
        
        Args:
            chosen_bookmaker: Bookmaker to use for spreads
            save_csv: Whether to save results to CSV
            
        Returns:
            List of dictionaries containing game data
        """
        try:
            games_data = self.api.get_nfl_spreads()
            spreads_list = []
            
            for game in games_data:
                try:
                    # Extract basic game info
                    home_team = game.get('home_team')
                    away_team = game.get('away_team')
                    commence_time = game.get('commence_time')
                    
                    if not all([home_team, away_team, commence_time]):
                        logger.warning(f"Skipping game with missing data: {game}")
                        continue
                    
                    # Get NFL week
                    week = assign_week(commence_time)
                    if week is None:
                        logger.warning(f"Skipping game outside schedule: {commence_time}")
                        continue
                    
                    # Get spread data
                    bookmaker_data = next(
                        (b for b in game.get('bookmakers', []) 
                         if b['title'] == chosen_bookmaker), 
                        None
                    )
                    
                    if not bookmaker_data:
                        logger.warning(f"No {chosen_bookmaker} data for {home_team} vs {away_team}")
                        continue
                    
                    markets = bookmaker_data.get('markets', [])
                    if not markets:
                        logger.warning(f"No markets for {home_team} vs {away_team}")
                        continue
                    
                    outcomes = markets[0].get('outcomes', [])
                    home_spread = next(
                        (o['point'] for o in outcomes if o['name'] == home_team), 
                        None
                    )
                    
                    if home_spread is None:
                        logger.warning(f"No spread for {home_team}")
                        continue
                    
                    # Create game record
                    spreads_list.append({
                        "week": week,
                        "home_team": home_team,
                        "away_team": away_team,
                        "commence_time": commence_time,
                        "spread": home_spread,
                        "bookmaker": chosen_bookmaker,
                        "game": f"{away_team} @ {home_team}",
                        "last_updated": format_timestamp_ct(get_current_time_ct())
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing game: {str(e)}")
                    continue

            if not spreads_list:
                logger.warning("No valid games found in API response")
                return []

            # Save to CSV if requested
            if save_csv:
                self._save_spreads_to_csv(spreads_list)

            return spreads_list
            
        except Exception as e:
            logger.error(f"Error fetching spreads: {str(e)}")
            return []

    def get_weekly_spreads(
        self, 
        week: int, 
        chosen_bookmaker: str = "DraftKings"
    ) -> List[Dict]:
        """
        Get spreads for specific week, from cache or API.
        
        Args:
            week: NFL week number
            chosen_bookmaker: Bookmaker to use for spreads
            
        Returns:
            List of dictionaries containing game data
        """
        try:
            # Try loading from cache
            if self.spreads_file.exists():
                df = pd.read_csv(self.spreads_file)
                if not df.empty:
                    week_df = df[df["week"] == week]
                    if not week_df.empty:
                        return week_df.to_dict(orient="records")
            
            # Fetch from API if cache miss
            logger.info(f"No cached data for week {week}, fetching from API...")
            spreads_list = self.get_weekly_spreads_from_api(
                chosen_bookmaker=chosen_bookmaker
            )
            
            if spreads_list:
                df = pd.DataFrame(spreads_list)
                week_df = df[df["week"] == week]
                return week_df.to_dict(orient="records")
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting spreads for week {week}: {str(e)}")
            return []

    def _save_spreads_to_csv(self, spreads_list: List[Dict]) -> None:
        """Save spreads data to CSV file"""
        try:
            df = pd.DataFrame(spreads_list)
            df.to_csv(self.spreads_file, index=False)
            logger.info(f"Saved {len(spreads_list)} games to {self.spreads_file}")
        except Exception as e:
            logger.error(f"Error saving spreads to CSV: {str(e)}")
    
    def get_game_results(self, week: int) -> List[Dict]:
        """Get processed game results including cover determination"""
        try:
            scores_data = self.api.get_game_scores()
            results_list = []
            
            # Get spreads for comparison
            spreads = self.get_weekly_spreads(week)
            spreads_dict = {game['game']: game['spread'] for game in spreads}
            
            for game in scores_data:
                try:
                    game_key = f"{game['away_team']} @ {game['home_team']}"
                    if game_key not in spreads_dict:
                        continue
                        
                    home_score = game.get('scores_home')
                    away_score = game.get('scores_away')
                    
                    if None in (home_score, away_score):
                        continue
                        
                    # Add debug logging
                    score_diff = home_score - away_score
                    spread = spreads_dict[game_key]
                    
                    logger.info(f"""
                    Cover Determination Debug:
                    - Game: {game_key}
                    - Score: {home_score}-{away_score} (diff: {score_diff})
                    - Spread: {spread}
                    - Home team is {'favorite' if spread < 0 else 'underdog'}
                    """)
                    
                    # Check for push
                    if abs(score_diff) == abs(spread):
                        covered = None
                        logger.info("Result: PUSH")
                    else:
                        if spread < 0:  # Home team is favorite
                            covered = game['home_team'] if score_diff > abs(spread) else game['away_team']
                        else:  # Home team is underdog
                            covered = game['home_team'] if score_diff > spread else game['away_team']
                        logger.info(f"Result: {covered} covered")

                    results_list.append({
                        "week": week,
                        "game": game_key,
                        "covered": covered,
                        "home_score": home_score,
                        "away_score": away_score
                    })
                        
                except Exception as e:
                    logger.error(f"Error processing game result: {str(e)}")
                    continue
                    
            return results_list
            
        except Exception as e:
            logger.error(f"Error getting game results: {str(e)}")
            return []
# Create singleton instance
nfl_data = NFLData()
