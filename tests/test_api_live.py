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
        
        # Verify we got real data back
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
            # Check scores endpoint first for yesterday's preseason games
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
                
            # Save response for analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_data_dir = Path(project_root) / "test_data"
            test_data_dir.mkdir(exist_ok=True)
            
            scores_file = test_data_dir / f"scores_response_{timestamp}.json"
            with open(scores_file, "w") as f:
                json.dump(scores, f, indent=2)
                
            print(f"\nSaved scores response to: {scores_file}")
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

if __name__ == '__main__':
    unittest.main()