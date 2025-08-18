# src/scoring.py
import pandas as pd

def calculate_scores(picks_df, results_df):
    """
    Compare picks to results and return a leaderboard.
    Currently a placeholder: just counts picks per user.
    """
    if picks_df.empty:
        return pd.DataFrame(columns=["User", "Total Picks"])
    return picks_df.groupby("User").size().reset_index(name="Total Picks").sort_values("Total Picks", ascending=False)
