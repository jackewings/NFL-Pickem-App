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
        """Append new spreads to CSV file, keeping all historical games."""
        try:
            new_df = pd.DataFrame(spreads_list)
            if self.spreads_file.exists():
                old_df = pd.read_csv(self.spreads_file)
                # Combine and drop duplicates based on week+game
                combined = pd.concat([old_df, new_df]).drop_duplicates(subset=["week", "game"], keep="last")
            else:
                combined = new_df
            combined.to_csv(self.spreads_file, index=False)
            logger.info(f"Saved {len(combined)} total games to {self.spreads_file}")
        except Exception as e:
            logger.error(f"Error saving spreads to CSV: {str(e)}")
    
    def get_game_results(self, week: int, use_demo: bool = False) -> List[Dict]:
        """
        Get processed game results (final scores only).
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

            for game in scores_data:
                try:
                    # Only process games from the correct week
                    game_week = assign_week(game.get('commence_time'))
                    if game_week != week:
                        continue

                    home_team = game['home_team']
                    away_team = game['away_team']
                    home_score = game.get('scores_home')
                    away_score = game.get('scores_away')
                    game_key = f"{away_team} @ {home_team}"

                    if None in (home_score, away_score):
                        logger.warning(f"Missing scores for game: {game_key}")
                        continue

                    results_list.append({
                        "week": week,
                        "game": game_key,
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_score": home_score,
                        "away_score": away_score,
                    })

                except Exception as e:
                    logger.error(f"Error processing game result: {str(e)}")
                    continue

            # Save results to CSV if any games were processed
            if results_list:
                try:
                    df = pd.DataFrame(results_list)
                    df.to_csv(self.results_file, mode='w', header=True, index=False)
                    logger.info(f"Saved {len(results_list)} results to {self.results_file}")
                except Exception as e:
                    logger.error(f"Error saving results to CSV: {str(e)}")

            return results_list

        except Exception as e:
            logger.error(f"Error getting game results: {str(e)}")
            return []

nfl_data = NFLData()
