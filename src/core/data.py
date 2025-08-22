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
        self.results_file = self.data_dir / "results.csv"
        self.demo_results_file = self.data_dir / "demo_results.csv"
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
    
    def get_game_results(self, week: int, use_demo: bool = False) -> List[Dict]:
        """
        Get processed game results including cover determination.
        
        Args:
            week: NFL week number
            use_demo: Whether to use demo data instead of live API
            
        Returns:
            List of dictionaries containing game results
        """
        try:
            # Use demo data if specified
            if use_demo:
                if not self.demo_results_file.exists():
                    logger.warning("Demo results file not found")
                    return []
                try:
                    results_df = pd.read_csv(self.demo_results_file)
                    week_results = results_df[results_df['week'] == week].to_dict('records')
                    logger.info(f"Loaded {len(week_results)} demo results for week {week}")
                    return week_results
                except Exception as e:
                    logger.error(f"Error reading demo results: {str(e)}")
                    return []
            
            # Use live API data
            scores_data = self.api.get_game_scores()
            results_list = []
            
            # Get spreads for comparison
            spreads = self.get_weekly_spreads(week)
            spreads_dict = {game['game']: game['spread'] for game in spreads}
            
            for game in scores_data:
                try:
                    game_key = f"{game['away_team']} @ {game['home_team']}"
                    if game_key not in spreads_dict:
                        logger.warning(f"No spread found for game: {game_key}")
                        continue
                        
                    home_score = game.get('scores_home')
                    away_score = game.get('scores_away')
                    
                    if None in (home_score, away_score):
                        logger.warning(f"Missing scores for game: {game_key}")
                        continue
                        
                    score_diff = home_score - away_score
                    spread = spreads_dict[game_key]
                    
                    logger.info(f"""
                    Cover Determination:
                    - Game: {game_key}
                    - Score: {home_score}-{away_score} (diff: {score_diff})
                    - Spread: {spread}
                    - Home team is {'favorite' if spread < 0 else 'underdog'}
                    """)
                    
                    # Check for push
                    if abs(score_diff) == abs(spread):
                        covered = "PUSH"
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
                        "away_score": away_score,
                        "spread": spread
                    })
                        
                except Exception as e:
                    logger.error(f"Error processing game result: {str(e)}")
                    continue
                    
            # Save results to CSV if any games were processed
            if results_list:
                try:
                    df = pd.DataFrame(results_list)
                    df.to_csv(self.results_file, mode='a', header=not self.results_file.exists(), index=False)
                    logger.info(f"Saved {len(results_list)} results to {self.results_file}")
                except Exception as e:
                    logger.error(f"Error saving results to CSV: {str(e)}")
            
            return results_list
                
        except Exception as e:
            logger.error(f"Error getting game results: {str(e)}")
            return []
# Create singleton instance
nfl_data = NFLData()
