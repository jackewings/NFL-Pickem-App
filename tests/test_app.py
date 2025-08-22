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

class TestNFLPickemApp(unittest.TestCase):
    def test_format_spread(self):
        self.assertEqual(format_spread(3.0), "+3.0")
        self.assertEqual(format_spread(-3.0), "-3.0")
        self.assertEqual(format_spread(0), "0")

    def test_format_game_with_spread(self):
        game = "Minnesota Vikings @ Chicago Bears"
        spread = 3.0
        expected = "Vikings (+3.0) @ Bears"
        self.assertEqual(format_game_with_spread(game, spread), expected)

    def test_game_has_started(self):
        past_time = (datetime.now().replace(hour=0, minute=0) - pd.Timedelta(days=1)).isoformat()
        future_time = (datetime.now().replace(hour=0, minute=0) + pd.Timedelta(days=1)).isoformat()
        
        self.assertTrue(game_has_started(past_time))
        self.assertFalse(game_has_started(future_time))
        self.assertFalse(game_has_started(None))

    def test_get_team_display_and_color(self):
        team = "Minnesota Vikings"
        display_name, color = get_team_display_and_color(team)
        self.assertEqual(display_name, "Vikings")
        self.assertEqual(color, NFL_TEAM_COLORS[team])

    def test_add_rank(self):
        df = pd.DataFrame({
            'user': ['A', 'B', 'C'],
            'correct': [10, 8, 10],  # A and C are tied
            'correct_pct': [0.8, 0.7, 0.8]  # A and C are tied
        })
        ranked_df = add_rank(df, ['correct'])  # Only sort by correct column
        self.assertEqual(ranked_df['Rank'].tolist(), [1, 3, 1])

    def test_add_rank_with_four_people(self):
        df = pd.DataFrame({
            'user': ['A', 'B', 'C', 'D'],
            'correct': [10, 8, 10, 8],  # A&C tied, B&D tied
            'correct_pct': [0.8, 0.7, 0.8, 0.7]
        })
        ranked_df = add_rank(df, ['correct'])
        self.assertEqual(ranked_df['Rank'].tolist(), [1, 3, 1, 3])

    def test_load_picks_empty_file(self):
        """Test loading picks from empty or non-existent file"""
        # Ensure test runs with no existing file
        if PICKS_FILE.exists():
            PICKS_FILE.unlink()
            
        empty_df = load_picks()
        expected_columns = ["week", "user", "game", "spread", "pick", "timestamp"]
        
        self.assertTrue(all(col in empty_df.columns for col in expected_columns))
        self.assertTrue(empty_df.empty)

def test_format_game_with_vs(self):
    """Test formatting games with 'vs.' format"""
    game = "Chicago Bears vs. Minnesota Vikings"
    spread = -3.0
    expected = "Bears (-3.0) vs. Vikings"
    self.assertEqual(format_game_with_spread(game, spread), expected)

def test_game_has_started_invalid_time(self):
    """Test game_has_started with invalid time format"""
    self.assertFalse(game_has_started("invalid_time"))
    self.assertFalse(game_has_started(""))

if __name__ == '__main__':
    unittest.main()