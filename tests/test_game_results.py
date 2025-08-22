import unittest
from unittest.mock import patch, MagicMock
from src.core.data import NFLData

class TestGameResults(unittest.TestCase):
    def setUp(self):
        self.nfl_data = NFLData(data_dir="test_data")
        
        # Sample game data with proper score format
        self.sample_scores = [{
            'home_team': 'Philadelphia Eagles',
            'away_team': 'Dallas Cowboys',
            'scores_home': 24,  # Eagles win by 4
            'scores_away': 20
        }]
        
        # Sample spreads data
        self.sample_spreads = [{
            'week': 1,
            'game': 'Dallas Cowboys @ Philadelphia Eagles',
            'spread': -3.0  # Eagles favored by 3
        }]

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_get_game_results(self, mock_get_spreads, mock_get_scores):
        # Set up mocks
        mock_get_scores.return_value = self.sample_scores
        mock_get_spreads.return_value = self.sample_spreads
        
        # Get results
        results = self.nfl_data.get_game_results(week=1)
        
        # Verify results
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['game'], 'Dallas Cowboys @ Philadelphia Eagles')
        self.assertEqual(result['covered'], 'Philadelphia Eagles')  # Eagles covered (-3 spread, won by 4)
        self.assertEqual(result['home_score'], 24)
        self.assertEqual(result['away_score'], 20)

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_get_game_results_no_cover(self, mock_get_spreads, mock_get_scores):
        # Modify scores so Eagles don't cover
        self.sample_scores[0]['scores_home'] = 21  # Eagles win by 1, don't cover -3
        mock_get_scores.return_value = self.sample_scores
        mock_get_spreads.return_value = self.sample_spreads
        
        results = self.nfl_data.get_game_results(week=1)
        self.assertEqual(results[0]['covered'], 'Dallas Cowboys')  # Cowboys covered +3

    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_get_game_results_missing_data(self, mock_get_spreads, mock_get_scores):
        # Test with missing scores
        self.sample_scores[0]['scores_home'] = None
        mock_get_scores.return_value = self.sample_scores
        mock_get_spreads.return_value = self.sample_spreads
        
        results = self.nfl_data.get_game_results(week=1)
        self.assertEqual(len(results), 0)  # Should skip games with missing data
    
    @patch('src.api.odds_api.OddsAPI.get_game_scores')
    @patch('src.core.data.NFLData.get_weekly_spreads')
    def test_get_game_results_push(self, mock_get_spreads, mock_get_scores):
        # Modify scores so Eagles win by exactly 3 (push on -3)
        self.sample_scores[0]['scores_home'] = 23  # 23-20 = 3 point difference
        mock_get_scores.return_value = self.sample_scores
        mock_get_spreads.return_value = self.sample_spreads
        
        results = self.nfl_data.get_game_results(week=1)
        self.assertEqual(results[0]['covered'], None)  # Should be None for a push

    @patch('src.api.odds_api.OddsAPI.get_nfl_spreads')  # Note: using spreads endpoint
    def test_get_game_scores(self, mock_get_spreads):
        # Mock API response with completed game
        mock_get_spreads.return_value = [{
            'id': 'test_game',
            'home_team': 'Philadelphia Eagles',
            'away_team': 'Dallas Cowboys',
            'scores': {
                'home_score': 27,
                'away_score': 17
            },
            'completed': True
        }]
    
    api = OddsAPI()
    scores = api.get_game_scores()
    
    self.assertEqual(len(scores), 1)
    self.assertEqual(scores[0]['scores_home'], 27)
    self.assertEqual(scores[0]['scores_away'], 17)
    self.assertTrue(scores[0]['completed'])

if __name__ == '__main__':
    unittest.main()