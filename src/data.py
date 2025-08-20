import requests
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
import streamlit as st

# Example: 2025 NFL season schedule mapping (start_date, end_date) for each week
# Dates are in UTC, adjust as needed
NFL_WEEKS = {
    1: ("2025-09-05", "2025-09-11"),
    2: ("2025-09-12", "2025-09-18"),
    3: ("2025-09-19", "2025-09-25"),
    4: ("2025-09-26", "2025-10-02"),
    5: ("2025-10-03", "2025-10-09"),
    6: ("2025-10-10", "2025-10-16"),
    7: ("2025-10-17", "2025-10-23"),
    8: ("2025-10-24", "2025-10-30"),
    9: ("2025-10-31", "2025-11-06"),
    10: ("2025-11-07", "2025-11-13"),
    11: ("2025-11-14", "2025-11-20"),
    12: ("2025-11-21", "2025-11-27"),
    13: ("2025-11-28", "2025-12-04"),
    14: ("2025-12-05", "2025-12-11"),
    15: ("2025-12-12", "2025-12-18"),
    16: ("2025-12-19", "2025-12-25"),
    17: ("2025-12-26", "2026-01-01"),
    18: ("2026-01-02", "2026-01-08"),
}

def assign_week(commence_time_str):
    """
    Convert commence_time string to datetime and determine NFL week.
    """
    game_date = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00")).date()
    for week, (start_str, end_str) in NFL_WEEKS.items():
        start = datetime.fromisoformat(start_str).date()
        end = datetime.fromisoformat(end_str).date()
        if start <= game_date <= end:
            return week
    return None  # if date doesn't match any week

def get_weekly_spreads_from_api(chosen_bookmaker="DraftKings", save_csv=True):
    """
    Fetch NFL spreads from The Odds API for all available games.
    Assigns correct NFL week based on commence_time.
    Saves CSV for caching.
    """
    API_KEY = st.secrets['API_KEY']
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "spreads",
        "oddsFormat": "decimal"
    }
    
    response = requests.get(url, params=params)
    data = response.json()

    spreads_list = []

    for game in data:
        try:
            home_team = game['home_team']
            away_team = game['away_team']
            commence_time = game['commence_time']
            
            # Determine NFL week
            week = assign_week(commence_time)
            if week is None:
                continue  # skip games outside schedule
            
            # Find the chosen bookmaker
            bookmaker_data = next((b for b in game['bookmakers'] if b['title'] == chosen_bookmaker), None)
            if not bookmaker_data:
                continue  # skip if chosen bookmaker not available
            
            outcomes = bookmaker_data['markets'][0]['outcomes']
            home_spread = next((o['point'] for o in outcomes if o['name'] == home_team), None)
            if home_spread is None:
                continue
            
            spreads_list.append({
                "week": week,
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": commence_time,
                "spread": home_spread,
                "bookmaker": chosen_bookmaker,
                "game": f"{away_team} @ {home_team}",   
            })
        except (IndexError, KeyError):
            continue

    # Save CSV
    if save_csv:
        Path("data").mkdir(exist_ok=True)
        csv_file = f"data/weekly_spreads.csv"  # All weeks in one CSV
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["week","home_team","away_team","commence_time","spread","bookmaker", 'game'])
            writer.writeheader()
            writer.writerows(spreads_list)
        print(f"Saved CSV to {csv_file}")

    return spreads_list

def get_weekly_spreads(week, chosen_bookmaker="DraftKings"):
    """
    Loads spreads from CSV and filters by week.
    If CSV is empty or doesn't exist, fetches from API and saves.
    Returns a list of dicts for the given week.
    """
    csv_file = "data/weekly_spreads.csv"
    
    # Try to load from existing CSV
    try:
        df = pd.read_csv(csv_file)
        if not df.empty:
            week_df = df[df["week"] == week]
            if not week_df.empty:
                return week_df.to_dict(orient="records")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        pass  # If file doesn't exist or is empty, fall through

    # If no data found, fetch from API
    print(f"No cached data for week {week}, fetching from API...")
    spreads_list = get_weekly_spreads_from_api(chosen_bookmaker=chosen_bookmaker)
    
    if spreads_list:
        # Save to CSV and try again
        df = pd.DataFrame(spreads_list)
        df.to_csv(csv_file, index=False)
        week_df = df[df["week"] == week]
        return week_df.to_dict(orient="records")
    
    return []  # Return empty list if no data available


