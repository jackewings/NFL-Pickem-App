
import pandas as pd

def calculate_scores(picks_df, results_df):
    if picks_df.empty or results_df is None or results_df.empty:
        empty_weekly = pd.DataFrame(columns=["user", "week", "correct", "total", "correct_pct"])
        empty_total = pd.DataFrame(columns=["user", "correct", "total", "correct_pct", "favorite_team"])
        return {"weekly": empty_weekly, "total": empty_total}

    merged = picks_df.merge(
        results_df[["week", "game", "covered"]],
        on=["week", "game"],
        how="left"
    )

    merged["correct"] = (merged["pick"].str.lower() == merged["covered"].str.lower()).astype(int)

    # Weekly leaderboard
    weekly = (
        merged.groupby(["user", "week"])
        .agg(correct=("correct", "sum"), total=("pick", "count"))
        .reset_index()
    )
    weekly["correct_pct"] = (weekly["correct"] / weekly["total"] * 100).round(1)

    # Favorite team calculation for total leaderboard
    correct_picks = merged[merged["correct"] == 1]
    favorite_team = (
        correct_picks.groupby(["user", "pick"])
        .size()
        .reset_index(name="count")
        .sort_values(["user", "count", "pick"], ascending=[True, False, True])
        .drop_duplicates("user")
        .set_index("user")["pick"]
    )

    # Season total leaderboard
    total = (
        weekly.groupby("user")
        .agg(correct=("correct", "sum"), total=("total", "sum"))
        .reset_index()
    )
    total["correct_pct"] = (total["correct"] / total["total"] * 100).round(1)
    total["favorite_team"] = total["user"].map(favorite_team).fillna("N/A")

    return {"weekly": weekly, "total": total}
