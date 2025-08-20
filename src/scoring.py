
import pandas as pd

def calculate_scores(picks_df, results_df):
    """
    Calculate weekly and total scores for all users.
    Pushes (ties) are excluded from calculations.
    """
    if picks_df.empty or results_df.empty:
        return {"weekly": pd.DataFrame(), "total": pd.DataFrame()}
    
    # Merge picks with results
    merged = picks_df.merge(results_df, on=["week", "game"], how="inner")
    
    # Determine if each pick was correct, incorrect, or a push
    def determine_result(row):
        if pd.isna(row["covered"]):
            return None  # No result yet
        
        # Check if it's a push (exact spread match)
        # This would need actual game scores to calculate, but for now
        # we'll assume "covered" tells us the winner against the spread
        if row["covered"] == "PUSH":
            return "push"
        elif row["pick"] == row["covered"]:
            return "correct"
        else:
            return "incorrect"
    
    merged["result"] = merged.apply(determine_result, axis=1)
    
    # Filter out pushes and games without results for scoring
    scored_games = merged[merged["result"].isin(["correct", "incorrect"])]
    
    # Calculate weekly scores (excluding pushes)
    weekly_scores = []
    for (week, user), group in scored_games.groupby(["week", "user"]):
        correct = (group["result"] == "correct").sum()
        total = len(group)  # Only games that aren't pushes
        pct = (correct / total) * 100 if total > 0 else 0
        
        weekly_scores.append({
            "week": week,
            "user": user,
            "correct": correct,
            "total": total,
            "correct_pct": round(pct, 1)
        })
    
    # Calculate total scores (excluding pushes)
    total_scores = []
    for user, group in scored_games.groupby("user"):
        correct = (group["result"] == "correct").sum()
        total = len(group)  # Only games that aren't pushes
        pct = (correct / total) * 100 if total > 0 else 0
        
        # Find most picked team (optional)
        best_team = group["pick"].value_counts().index[0] if not group.empty else "N/A"
        
        total_scores.append({
            "user": user,
            "correct": correct,
            "total": total,
            "correct_pct": round(pct, 1),
            "best_team": best_team
        })
    
    return {
        "weekly": pd.DataFrame(weekly_scores),
        "total": pd.DataFrame(total_scores)
    }
