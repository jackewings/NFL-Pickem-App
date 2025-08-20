import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz
from src import data

def update_spreads_and_results():
    try:
        spreads = data.get_weekly_spreads_from_api(save_csv=True)
        print(f"Updated spreads data at {datetime.now(pytz.UTC)}")
        return True
    except Exception as e:
        print(f"Error updating data: {e}")
        return False

if __name__ == "__main__":
    update_spreads_and_results()