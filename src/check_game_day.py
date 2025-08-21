from datetime import datetime
import pytz
import data  # Changed from 'from src import data'

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
                print("true")
                return True
        print("false")
        return False
    except Exception as e:
        print(f"Error checking game day: {e}")
        print("false")
        return False

if __name__ == "__main__":
    is_game_day()