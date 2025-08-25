import unittest
import pandas as pd
from datetime import datetime
from pathlib import Path
from app import (
    format_spread,
    format_game_with_spread,
    game_has_started,
    get_team_display_and_color,
    add_rank,
    load_picks,
    PICKS_FILE
)
from src.config.settings import TEAM_DISPLAY_NAMES, NFL_TEAM_COLORS
from src.utils.errors import DataError

class TestNFLPickemApp(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Sample data for ranking tests
        self.ranking_data = pd.DataFrame({
            'user': ['A', 'B', 'C', 'D'],
            'correct': [10, 8, 10, 8],
            'correct_pct': [0.8, 0.7, 0.8, 0.7]
        })

    def test_format_spread(self):
        """Test spread formatting"""
        self.assertEqual(format_spread(3.0), "+3.0")
        self.assertEqual(format_spread(-3.0), "-3.0")
        self.assertEqual(format_spread(0), "0")

    def format_game_with_spread(game: str, spread: float) -> str:
        """Format game with spread, handling both @ and vs. formats"""
        if "@" in game:
            away_team, home_team = [t.strip() for t in game.split("@")]
            display_format = "{} ({}) @ {}"
        else:
            home_team, away_team = [t.strip() for t in game.split("vs.")]
            display_format = "{} ({}) vs. {}"
        
        away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
        home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
        
        # Format spread for display
        spread_str = format_spread(spread if "@" in game else -spread)
        
        return display_format.format(
            away_display if "@" in game else home_display,
            spread_str,
            home_display if "@" in game else away_display
        )
    def test_format_game_with_vs(self):
        """Test game formatting with spread - vs. format"""
        game = "Chicago Bears vs. Minnesota Vikings"
        spread = -3.0
        expected = "Bears (-3.0) vs. Vikings"
        self.assertEqual(format_game_with_spread(game, spread), expected)

    def test_game_has_started(self):
        """Test game start time checking"""
        past_time = (datetime.now().replace(hour=0, minute=0) - pd.Timedelta(days=1)).isoformat()
        future_time = (datetime.now().replace(hour=0, minute=0) + pd.Timedelta(days=1)).isoformat()
        
        self.assertTrue(game_has_started(past_time))
        self.assertFalse(game_has_started(future_time))
        self.assertFalse(game_has_started(None))

    def test_game_has_started_invalid_time(self):
        """Test game_has_started with invalid time formats"""
        self.assertFalse(game_has_started("invalid_time"))
        self.assertFalse(game_has_started(""))
        self.assertFalse(game_has_started("2023-13-45T25:99:99Z")) 

    def test_get_team_display_and_color(self):
        """Test team display name and color retrieval"""
        team = "Minnesota Vikings"
        display_name, color = get_team_display_and_color(team)
        self.assertEqual(display_name, "Vikings")
        self.assertEqual(color, NFL_TEAM_COLORS[team])

        # Test with unknown team
        display_name, color = get_team_display_and_color("Unknown Team")
        self.assertEqual(display_name, "Unknown Team")
        self.assertEqual(color, "#000000")  # Default black

    def add_rank(df: pd.DataFrame, sort_columns: List[str]) -> pd.DataFrame:
        """Add ranking column that handles ties correctly"""
        # Sort by specified columns in descending order
        df = df.sort_values(sort_columns, ascending=[False] * len(sort_columns))
        
        # Add rank with method='min' to give same rank for ties
        df['Rank'] = df[sort_columns[0]].rank(method='min', ascending=False)
        
        # Reset index to maintain original order
        return df.reset_index(drop=True)

    def test_add_rank_with_four_people(self):
        """Test ranking with four users and ties"""
        ranked_df = add_rank(self.ranking_data, ['correct'])
        self.assertEqual(ranked_df['Rank'].tolist(), [1, 3, 1, 3])

    def test_add_rank_multiple_columns(self):
        """Test ranking with multiple sorting columns"""
        ranked_df = add_rank(self.ranking_data, ['correct', 'correct_pct'])
        self.assertEqual(ranked_df['Rank'].tolist(), [1, 3, 1, 3])

if __name__ == '__main__':
    unittest.main()