
from typing import Dict, Optional, Union
import pandas as pd
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ScoreResult:
    """Container for scoring results"""
    weekly: pd.DataFrame
    total: pd.DataFrame

def determine_result(row: pd.Series) -> Optional[str]:
    """
    Determine if a pick was correct, incorrect, or a push.
    
    Args:
        row: DataFrame row containing 'covered' and 'pick' columns
        
    Returns:
        str: 'correct', 'incorrect', 'push', or None if no result
    """
    if pd.isna(row["covered"]):
        return None
    
    if row["covered"] == "PUSH":
        return "push"
    elif row["pick"] == row["covered"]:
        return "correct"
    else:
        return "incorrect"

def calculate_weekly_scores(scored_games: pd.DataFrame) -> list:
    """Calculate scores for each user by week."""
    weekly_scores = []
    
    try:
        for (week, user), group in scored_games.groupby(["week", "user"]):
            correct = (group["result"] == "correct").sum()
            total = len(group)
            pct = (correct / total) * 100 if total > 0 else 0
            
            weekly_scores.append({
                "week": week,
                "user": user,
                "correct": correct,
                "total": total,
                "correct_pct": round(pct, 1)
            })
    except Exception as e:
        logger.error(f"Error calculating weekly scores: {str(e)}")
        
    return weekly_scores

def calculate_total_scores(scored_games: pd.DataFrame) -> list:
    """Calculate total scores for each user."""
    total_scores = []
    
    try:
        for user, group in scored_games.groupby("user"):
            correct = (group["result"] == "correct").sum()
            total = len(group)
            pct = (correct / total) * 100 if total > 0 else 0
            
            # Find most picked team
            best_team = (group["pick"].value_counts().index[0] 
                        if not group.empty else "N/A")
            
            total_scores.append({
                "user": user,
                "correct": correct,
                "total": total,
                "correct_pct": round(pct, 1),
                "best_team": best_team
            })
    except Exception as e:
        logger.error(f"Error calculating total scores: {str(e)}")
        
    return total_scores

def calculate_scores(picks_df: pd.DataFrame, 
                    results_df: pd.DataFrame) -> ScoreResult:
    """
    Calculate weekly and total scores for all users.
    
    Args:
        picks_df: DataFrame containing user picks
        results_df: DataFrame containing game results
        
    Returns:
        ScoreResult containing weekly and total scoring DataFrames
        
    Notes:
        - Pushes (ties) are excluded from calculations
        - Games without results are excluded
    """
    empty_result = ScoreResult(weekly=pd.DataFrame(), total=pd.DataFrame())
    
    try:
        # Validate input
        if picks_df.empty or results_df.empty:
            logger.warning("Empty input DataFrame(s)")
            return empty_result
            
        # Merge picks with results
        merged = picks_df.merge(
            results_df, 
            on=["week", "game"], 
            how="inner"
        )
        
        # Calculate results
        merged["result"] = merged.apply(determine_result, axis=1)
        
        # Filter valid games
        scored_games = merged[
            merged["result"].isin(["correct", "incorrect"])
        ]
        
        if scored_games.empty:
            logger.warning("No valid games to score")
            return empty_result
            
        # Calculate scores
        weekly_scores = calculate_weekly_scores(scored_games)
        total_scores = calculate_total_scores(scored_games)
        
        return ScoreResult(
            weekly=pd.DataFrame(weekly_scores),
            total=pd.DataFrame(total_scores)
        )
        
    except Exception as e:
        logger.error(f"Error in score calculation: {str(e)}")
        return empty_result
    
def score_user_pick(pick_row, results_df):
    """
    Given a user's pick row and the results DataFrame,
    return 'correct', 'incorrect', or 'push' based on the user's spread.
    """
    # Find the final result for this game
    result_row = results_df[
        (results_df["week"] == pick_row["week"]) &
        (results_df["game"] == pick_row["game"])
    ]
    if result_row.empty:
        return None  

    home_team = pick_row["game"].split(" @ ")[1]
    away_team = pick_row["game"].split(" @ ")[0]
    home_score = result_row.iloc[0].get("home_score")
    away_score = result_row.iloc[0].get("away_score")
    spread = float(pick_row["spread"])
    pick = pick_row["pick"]

    if home_score is None or away_score is None:
        return None

    # Calculate margin
    margin = home_score - away_score

    # Determine which team covered the spread
    if spread < 0:
        covered = home_team if margin > abs(spread) else away_team
    else:
        covered = home_team if margin > spread else away_team

    # Push logic
    if abs(margin) == abs(spread):
        return "push"
    elif pick == covered:
        return "correct"
    else:
        return "incorrect"
    
def score_all_picks(picks_df: pd.DataFrame, results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'result' column to picks_df with 'correct', 'incorrect', or 'push'
    using each user's submitted spread and the final game score.
    """
    picks_df = picks_df.copy()
    picks_df["result"] = picks_df.apply(lambda row: score_user_pick(row, results_df), axis=1)
    return picks_df