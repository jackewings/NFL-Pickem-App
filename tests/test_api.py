import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
from src.core.data import NFLData

class TestNFLData(unittest.TestCase):
    def setUp(self):
        self.nfl_data = NFLData(data_dir="test_data")
        # Load real sample data from your json file
        fixtures_path = Path(__file__).parent / 'fixtures' / 'weekly_spreads_sample.json'
        with open(fixtures_path, 'r') as f:
            self.sample_game_response = json.load(f)

    @patch('src.api.odds_api.OddsAPI.get_nfl_spreads')
    def test_get_weekly_spreads_from_api(self, mock_get_spreads):
        # Mock the API response with real sample data
        mock_get_spreads.return_value = self.sample_game_response
        
        # Test with save_csv=False to avoid file operations
        spreads = self.nfl_data.get_weekly_spreads_from_api(save_csv=False)
        
        # Test first game in the list
        self.assertTrue(len(spreads) > 0)
        self.assertEqual(spreads[0]['home_team'], 'Philadelphia Eagles')
        self.assertEqual(spreads[0]['away_team'], 'Dallas Cowboys')
        self.assertEqual(spreads[0]['spread'], -7.0)

    @patch('pandas.read_csv')
    def test_get_weekly_spreads_cached(self, mock_read_csv):
        # Create mock DataFrame with all games from sample data
        mock_data = []
        for game in self.sample_game_response:
            mock_data.append({
                'week': 1,
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'spread': game['bookmakers'][0]['markets'][0]['outcomes'][1]['point']
                if game['bookmakers'][0]['markets'][0]['outcomes'][1]['name'] == game['home_team']
                else game['bookmakers'][0]['markets'][0]['outcomes'][0]['point']
            })
        
        mock_df = pd.DataFrame(mock_data)
        mock_read_csv.return_value = mock_df
        
        spreads = self.nfl_data.get_weekly_spreads(week=1)
        self.assertEqual(len(spreads), len(mock_data))
        self.assertEqual(spreads[0]['spread'], -7.0)  # Eagles spread from sample data

if __name__ == '__main__':
    unittest.main()