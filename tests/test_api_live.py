import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime
import unittest

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.api.odds_api import OddsAPI
from src.core.data import NFLData

class TestNFLDataLive(unittest.TestCase):
    @unittest.skipIf(not os.getenv('API_KEY'), "No API key provided")
    def test_live_api_connection(self):
        """Test real API connection - uses one API request"""
        nfl_data = NFLData()
        spreads = nfl_data.get_weekly_spreads_from_api(save_csv=False)

        self.assertTrue(len(spreads) > 0)
        self.assertTrue(all(key in spreads[0] for key in ['home_team', 'away_team', 'spread']))
        print(f"Successfully fetched {len(spreads)} games from the API")

    def setUp(self):
        """Set up test fixtures"""
        load_dotenv()
        self.api = OddsAPI()
        self.nfl_data = NFLData()
        
    def test_live_data(self):
        """Test getting real NFL game data from The Odds API"""
        try:
            scores = self.api.get_game_scores()
            print("\nNFL Scores Analysis:")
            print(f"Games found: {len(scores)}")
            
            if scores:
                print("\nDetailed Games Analysis:")
                for game in scores:
                    print(f"\nGame: {game['away_team']} @ {game['home_team']}")
                    print(f"Score: {game['scores_home']}-{game['scores_away']}")
                    print(f"Completed: {game.get('completed', False)}")
                    if 'commence_time' in game:
                        print(f"Game Time: {game['commence_time']}")
            else:
                print("\nNo completed NFL games found.")
                print("Note: This could be because:")
                print("- Games haven't finished yet")
                print("- Preseason games aren't included")
                print("- Scores aren't available in free tier")
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_data_dir = Path(project_root) / "test_data"
            test_data_dir.mkdir(exist_ok=True)
            
            scores_file = test_data_dir / f"scores_response_{timestamp}.json"
            with open(scores_file, "w") as f:
                json.dump(scores, f, indent=2)
                
            print(f"\nSaved scores response to: {scores_file}")
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

class TestLiveAPI(unittest.TestCase):
    def setUp(self):
        self.api = OddsAPI()
        self.test_data_dir = Path("test_data")
        self.test_data_dir.mkdir(exist_ok=True)

    def test_scores_format(self):
        """Test that game scores are properly formatted"""
        scores = self.api.get_game_scores()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.test_data_dir / f"scores_response_{timestamp}.json"
        with open(filepath, "w") as f:
            json.dump(scores, f, indent=2)
            
        print(f"\nFound {len(scores)} games")
        
        if scores:
            for game in scores:
                print(f"\nGame Analysis:")
                print(f"Teams: {game['away_team']} @ {game['home_team']}")
                print(f"Score: {game['scores_away']}-{game['scores_home']}")
                print(f"Game Time: {game['commence_time']}")
                print(f"Last Updated: {game['last_update']}")
                
                self.assertIn('home_team', game)
                self.assertIn('away_team', game)
                self.assertIn('scores_home', game)
                self.assertIn('scores_away', game)
                self.assertIn('completed', game)
                self.assertIn('sport_key', game)

if __name__ == '__main__':
    unittest.main()