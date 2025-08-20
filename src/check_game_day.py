from datetime import datetime
import pytz
from src import data

def is_game_day():
    """Check if today has any NFL games scheduled"""
    try:
        games_data = data.get_weekly_spreads_from_api(save_csv=False)
        central = pytz.timezone('America/Chicago')
        now = datetime.now(central)
        
        for game in games_data:
            game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            game_time = game_time.astimezone(central)
            
            # Check if any game is today
            if game_time.date() == now.date():
                return True
        return False
    except Exception as e:
        print(f"Error checking game day: {e}")
        return False

if __name__ == "__main__":
    # Exit with status code 0 if it's a game day, 1 if not
    exit(0 if is_game_day() else 1)