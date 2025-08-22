import unittest
from unittest.mock import patch
from src.api.odds_api import OddsAPI
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

class TestSampleGames(unittest.TestCase):
    def setUp(self):
        load_dotenv()
        self.api = OddsAPI()
        
    def test_game_with_scores(self):
        """Test processing a completed game with scores"""
        # Load sample completed game data
        fixture_path = Path(__file__).parent / 'fixtures' / 'completed_game_sample.json'
        with open(fixture_path) as f:
            sample_data = json.load(f)
            
        # Process the sample data
        for game in sample_data:
            if game['completed']:
                # Extract scores from the new format
                home_score = next(int(s['score']) for s in game['scores'] 
                                if s['name'] == game['home_team'])
                away_score = next(int(s['score']) for s in game['scores'] 
                                if s['name'] == game['away_team'])
                
                print(f"\nGame Analysis:")
                print(f"Teams: {game['away_team']} @ {game['home_team']}")
                print(f"Final Score: {away_score}-{home_score}")
                print(f"Game Time: {game['commence_time']}")
                print(f"Last Updated: {game['last_update']}")
                
                # Verify score extraction
                self.assertEqual(home_score, 27)
                self.assertEqual(away_score, 20)
                self.assertEqual(game['home_team'], "Philadelphia Eagles")
                self.assertEqual(game['away_team'], "Dallas Cowboys")

    def test_game_with_spread(self):
        """Test spread calculations with completed game"""
        # Create sample game with spread
        game_data = {
            "completed": True,
            "home_team": "Philadelphia Eagles",
            "away_team": "Dallas Cowboys",
            "scores": [
                {"name": "Philadelphia Eagles", "score": "27"},
                {"name": "Dallas Cowboys", "score": "20"}
            ],
            "spread": -3.0  # Eagles favored by 3
        }
        
        # Process the game data
        home_score = next(int(s['score']) for s in game_data['scores'] 
                        if s['name'] == game_data['home_team'])
        away_score = next(int(s['score']) for s in game_data['scores'] 
                        if s['name'] == game_data['away_team'])
        
        # Calculate point differential
        score_diff = home_score - away_score
        spread = game_data['spread']
        
        print(f"\nSpread Analysis:")
        print(f"Teams: {game_data['away_team']} @ {game_data['home_team']}")
        print(f"Final Score: {away_score}-{home_score} (diff: {score_diff})")
        print(f"Spread: {spread}")
        
        # Determine cover
        if abs(score_diff) == abs(spread):
            covered = None  # Push
            print("Result: PUSH")
        else:
            if spread < 0:  # Home team favored
                covered = game_data['home_team'] if score_diff > abs(spread) else game_data['away_team']
            else:  # Home team underdog
                covered = game_data['home_team'] if score_diff > spread else game_data['away_team']
            print(f"Covered: {covered}")
        
        # Verify cover calculation
        self.assertEqual(covered, "Philadelphia Eagles")  # Eagles covered -3 with 7-point win

    def test_game_with_push(self):
        """Test spread calculations for a push"""
        # Create sample game with exact spread match
        game_data = {
            "completed": True,
            "home_team": "Philadelphia Eagles",
            "away_team": "Dallas Cowboys",
            "scores": [
                {"name": "Philadelphia Eagles", "score": "23"},
                {"name": "Dallas Cowboys", "score": "20"}
            ],
            "spread": -3.0  # Eagles favored by 3, win by exactly 3
        }
        
        # Process the game data
        home_score = next(int(s['score']) for s in game_data['scores'] 
                        if s['name'] == game_data['home_team'])
        away_score = next(int(s['score']) for s in game_data['scores'] 
                        if s['name'] == game_data['away_team'])
        
        # Calculate point differential
        score_diff = home_score - away_score
        spread = game_data['spread']
        
        print(f"\nPush Analysis:")
        print(f"Teams: {game_data['away_team']} @ {game_data['home_team']}")
        print(f"Final Score: {away_score}-{home_score} (diff: {score_diff})")
        print(f"Spread: {spread}")
        
        # Determine cover
        if abs(score_diff) == abs(spread):
            covered = None  # Push
            print("Result: PUSH")
        else:
            if spread < 0:  # Home team favored
                covered = game_data['home_team'] if score_diff > abs(spread) else game_data['away_team']
            else:  # Home team underdog
                covered = game_data['home_team'] if score_diff > spread else game_data['away_team']
            print(f"Covered: {covered}")
        
        # Verify push calculation
        self.assertIsNone(covered)  # Should be None for a push
        self.assertEqual(abs(score_diff), abs(spread))  # Verify exact spread match

if __name__ == '__main__':
    unittest.main()