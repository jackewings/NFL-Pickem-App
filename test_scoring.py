import pandas as pd
from src.scoring import calculate_scores

def test_calculate_scores_basic():
    picks_df = pd.DataFrame({
        "user": ["Jack", "Louis", "Jack", "Louis"],
        "week": [1, 1, 2, 2],
        "game": ["NE@NYJ", "NE@NYJ", "DAL@PHI", "DAL@PHI"],
        "pick": ["NE", "NYJ", "DAL", "PHI"]
    })
    results_df = pd.DataFrame({
        "week": [1, 2],
        "game": ["NE@NYJ", "DAL@PHI"],
        "covered": ["NE", "DAL"]
    })

    scores = calculate_scores(picks_df, results_df)
    weekly = scores["weekly"]
    total = scores["total"]

    # Check weekly leaderboard
    assert weekly.loc[(weekly.user == "Jack") & (weekly.week == 1), "correct"].values[0] == 1
    assert weekly.loc[(weekly.user == "Louis") & (weekly.week == 1), "correct"].values[0] == 0
    assert weekly.loc[(weekly.user == "Jack") & (weekly.week == 2), "correct"].values[0] == 1
    assert weekly.loc[(weekly.user == "Louis") & (weekly.week == 2), "correct"].values[0] == 0

    # Check total leaderboard
    assert total.loc[total.user == "Jack", "correct"].values[0] == 2
    assert total.loc[total.user == "Louis", "correct"].values[0] == 0

def test_calculate_scores_empty():
    picks_df = pd.DataFrame(columns=["user", "week", "game", "pick"])
    results_df = pd.DataFrame(columns=["week", "game", "covered"])
    scores = calculate_scores(picks_df, results_df)
    assert scores["weekly"].empty
    assert scores["total"].empty