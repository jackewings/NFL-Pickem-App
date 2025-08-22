import unittest
import os
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

if __name__ == '__main__':
    unittest.main()