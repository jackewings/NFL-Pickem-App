import unittest
from unittest.mock import patch, MagicMock
from src.core.data import NFLData

class TestGameResults(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.nfl_data = NFLData(data_dir="test_data")
        
        # Sample game scores data
        self.sample_scores = [
            {
                'home_team': 'Philadelphia Eagles',
                'away_team': 'Dallas Cowboys',
                'scores_home': 24,  # Eagles win by 4
                'scores_away': 20,
                'completed': True
            },
            {
                'home_team': 'New York Giants',
                'away_team': 'Washington Commanders',
                'scores_home': 21,  # Giants win by 1
                'scores_away': 20,
                'completed': True
            }
        ]
        
        # Sample spreads data
        self.sample_spreads = [
            {
                'week': 1,
                'game': 'Dallas Cowboys @ Philadelphia Eagles',
                'spread': -3.0  # Eagles favored by 3
            },
            {
                'week': 1,
                'game': 'Washington Commanders @ New York Giants',
                'spread': -2.5  # Giants favored by 2.5
            }
        ]

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_favorite_covers(self, mock_get_spreads, mock_get_scores):
        """Test when favorite covers the spread"""
        mock_get_scores.return_value = [self.sample_scores[0]]
        mock_get_spreads.return_value = [self.sample_spreads[0]]
        
        results = self.nfl_data.get_game_results(week=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['covered'], 'Philadelphia Eagles')  # Won by 4, covered -3

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_favorite_doesnt_cover(self, mock_get_spreads, mock_get_scores):
        """Test when favorite wins but doesn't cover"""
        mock_scores = self.sample_scores[1]  # Giants win by 1
        mock_get_scores.return_value = [mock_scores]
        mock_get_spreads.return_value = [self.sample_spreads[1]]  # Spread is -2.5
        
        results = self.nfl_data.get_game_results(week=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['covered'], 'Washington Commanders')  # Giants didn't cover -2.5

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_push(self, mock_get_spreads, mock_get_scores):
        """Test when final score difference equals spread (push)"""
        mock_scores = self.sample_scores[0].copy()
        mock_scores['scores_home'] = 23  # Eagles win by exactly 3
        mock_get_scores.return_value = [mock_scores]
        mock_get_spreads.return_value = [self.sample_spreads[0]]  # Spread is -3
        
        results = self.nfl_data.get_game_results(week=1)
        
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]['covered'])  # Should be None for push

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_missing_data(self, mock_get_spreads, mock_get_scores):
        """Test handling of missing or invalid data"""
        mock_scores = self.sample_scores[0].copy()
        mock_scores['scores_home'] = None
        mock_get_scores.return_value = [mock_scores]
        mock_get_spreads.return_value = [self.sample_spreads[0]]
        
        results = self.nfl_data.get_game_results(week=1)
        
        self.assertEqual(len(results), 0)  # Should skip games with missing data

if __name__ == '__main__':
    unittest.main()