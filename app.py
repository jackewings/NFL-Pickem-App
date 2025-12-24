import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
from src.core.scoring import score_all_picks
import os

from src.core.data import nfl_data
from src.core import scoring
from src.config.settings import (
    DATA_DIR,
    get_current_week,
    USERS,
    NFL_TEAM_COLORS,
    TEAM_NAME_MAPPING,
    TEAM_DISPLAY_NAMES
)
from src.utils.time_utils import format_display_time

# Write credentials from secrets to a temp file
with open("gcp_service_account.json", "w") as f:
    json.dump(dict(st.secrets["gcp_service_account"]), f)

import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_service_account.json", scope)
client = gspread.authorize(creds)

os.remove("gcp_service_account.json")

# Initialize session state variables
if "mode" not in st.session_state:
    st.session_state.mode = None
if "user" not in st.session_state:
    st.session_state.user = None
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "show_reset_confirm" not in st.session_state:
    st.session_state.show_reset_confirm = False

# File paths
PICKS_FILE = Path(DATA_DIR) / "picks.csv"
RESULTS_FILE = Path(DATA_DIR) / "results.csv"

# Check if results are available
results_available = RESULTS_FILE.exists() and pd.read_csv(RESULTS_FILE).shape[0] > 0

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        background-color: #2E5DB5;
        color: white;
    }
    .stProgress .st-bo {
        background-color: #E31837;
    }
</style>
""", unsafe_allow_html=True)

def load_picks():
    """Load picks from Google Sheet"""
    try:
        with st.spinner("Loading picks..."):
            sheet = client.open("NFL-Pickem-Picks").worksheet("Sheet1")  
            data = sheet.get_all_records()
            if not data:
                return pd.DataFrame(columns=["week", "user", "game", "spread", "pick", "timestamp"])
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading picks from Google Sheets: {e}")
        return pd.DataFrame(columns=["week", "user", "game", "spread", "pick", "timestamp"])

def save_picks(df: pd.DataFrame):
    """Save picks to Google Sheet"""
    try:
        with st.spinner("Saving picks..."):
            sheet = client.open("NFL-Pickem-Picks").worksheet("Sheet1")  
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.success("✅ Picks saved to Google Sheets!")
    except Exception as e:
        st.error(f"Error saving picks to Google Sheets: {e}")

def add_rank(df, sort_cols, rank_col="Rank"):
    """Add ranking column to DataFrame with proper sorting"""
    if df.empty:
        df[rank_col] = []
        return df
    
    # Create a copy to avoid modifying original
    df = df.copy()
    
    # Sort by specified columns in descending order
    df = df.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    
    # Create rank based on position after sorting
    df[rank_col] = range(1, len(df) + 1)
    
    # Ensure proper ordering in the final display
    df = df.sort_values(rank_col)
    
    return df

def result_to_emoji(result):
    if result == "correct":
        return "✅"
    elif result == "incorrect":
        return "❌"
    elif result == "push":
        return "➖"
    else:
        return ""

def format_pick_with_spread(pick, spread, game):
    """
    Format the pick with the correct spread sign for the picked team.
    """
    # Determine home and away teams
    if "@" in game:
        away_team, home_team = game.split(" @ ")
    else:
        home_team, away_team = game.split(" vs. ")
    away_team = away_team.strip()
    home_team = home_team.strip()

    # Map to display names
    pick_display = TEAM_DISPLAY_NAMES.get(pick, pick)
    away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
    home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)

    # Assign spread to the picked team
    if pick == away_team or pick == away_display:
        # Away team: spread as negative of the game spread
        pick_spread = -float(spread)
    elif pick == home_team or pick == home_display:
        # Home team: spread as entered
        pick_spread = float(spread)
    else:
        # Fallback: just show the pick and spread
        pick_spread = float(spread)

    sign = "+" if pick_spread > 0 else ""
    return f"{pick_display} {sign}{pick_spread:.1f}"

def game_has_started(commence_time_str):
    """Check if game has started based on commence time"""
    try:
        # Handle ISO strings ending with 'Z' (UTC)
        if commence_time_str.endswith("Z"):
            commence_time_str = commence_time_str.replace("Z", "+00:00")
        start_time = datetime.fromisoformat(commence_time_str)
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        return now >= start_time
    except Exception:
        return False
    
def get_team_display_and_color(team):
    """Helper function to get both display name and color for a team"""
    # First try to get the full name from mapping if it's an abbreviation
    full_name = TEAM_NAME_MAPPING.get(team, team)
    
    # Get the display name from the full name
    display_name = TEAM_DISPLAY_NAMES.get(full_name, team)
    
    # Get the color using the full name
    color = NFL_TEAM_COLORS.get(full_name, "#808080")
    
    # Debug print to help identify mismatches
    if color == "#808080":
        print(f"No color found for team: {team}, full_name: {full_name}")
    
    return display_name, color

def get_user_ats_records(picks_df, results_df):
    """
    Returns a DataFrame with columns: team, covered, total, pct
    For each team, counts how many times users picked them and their pick covered using their own spread.
    """
    # Merge picks with results to get scores for each pick
    merged = picks_df.merge(results_df, on=["week", "game"], how="left")
    ats = {}
    for _, row in merged.iterrows():
        pick_team = row["pick"]
        try:
            spread = float(row["spread"])
            home_team = row["home_team"]
            away_team = row["away_team"]
            home_score = float(row["home_score"])
            away_score = float(row["away_score"])
        except Exception:
            continue  # skip if any data is missing

        # Determine if pick_team is home or away
        if pick_team == home_team:
            margin = home_score - away_score + spread
        elif pick_team == away_team:
            margin = away_score - home_score - spread
        else:
            continue  # skip if pick_team doesn't match

        # Did the pick cover?
        covered = margin > 0
        push = margin == 0

        if pick_team not in ats:
            ats[pick_team] = {"covered": 0, "total": 0, "push": 0}
        ats[pick_team]["total"] += 1
        if covered:
            ats[pick_team]["covered"] += 1
        elif push:
            ats[pick_team]["push"] += 1

    # Build DataFrame
    data = []
    for team, stats in ats.items():
        total = stats["total"]
        covered = stats["covered"]
        pct = covered / total if total > 0 else 0.0
        data.append({"team": team, "covered": covered, "total": total, "pct": pct})
    return pd.DataFrame(data)

def format_spread(spread):
    """Format spread with proper + sign for positive values"""
    return f"+{spread}" if spread > 0 else str(spread)

def format_game_with_spread(game, spread):
    """Format game display with spread in consistent format"""
    if "@" in game:
        away_team, home_team = game.split(" @ ")
    else:
        home_team, away_team = game.split(" vs. ")
    
    # Get full names first
    away_team = TEAM_NAME_MAPPING.get(away_team, away_team)
    home_team = TEAM_NAME_MAPPING.get(home_team, home_team)
    
    # Then convert to display names
    away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
    home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
    
    # Fix: Negate the spread for away team
    # If spread is negative, home team is favored, so away team gets positive spread
    # If spread is positive, home team is underdog, so away team gets negative spread
    away_spread = -spread
    formatted_away_spread = format_spread(away_spread)
    
    return f"{away_display} ({formatted_away_spread}) @ {home_display}"

def format_pick_with_spread_for_past_picks(row):
    pick_team = TEAM_DISPLAY_NAMES.get(row["pick"], row["pick"])
    try:
        spread = float(row["spread"])
        # Determine if pick is home or away
        if "@" in row["game"]:
            away_team, home_team = row["game"].split(" @ ")
        else:
            home_team, away_team = row["game"].split(" vs. ")
        away_team = away_team.strip()
        home_team = home_team.strip()
        if row["pick"] == away_team:
            pick_spread = -spread
        elif row["pick"] == home_team:
            pick_spread = spread
        else:
            pick_spread = spread
        sign = "+" if pick_spread > 0 else ""
        return f"{pick_team} ({sign}{pick_spread:.1f})"
    except Exception:
        return pick_team

def render_update_results_tab():
    st.header("Update Results (Manual Entry)")

    # Select week
    current_week = get_current_week()
    week_options = list(range(1, current_week + 1))
    selected_week = st.selectbox("Select Week to Update:", week_options, index=len(week_options)-1)

    # Load weekly spreads and existing results
    weekly_spreads = pd.read_csv(Path(DATA_DIR) / "weekly_spreads.csv")
    week_games = weekly_spreads[weekly_spreads["week"] == selected_week]
    results_path = Path(DATA_DIR) / "results.csv"
    if results_path.exists():
        results_df = pd.read_csv(results_path)
    else:
        results_df = pd.DataFrame(columns=["week", "game", "home_team", "away_team", "home_score", "away_score"])

    # Build form for each game
    updated_rows = []
    with st.form("update_results_form"):
        st.write(f"Enter final scores for Week {selected_week} games. Leave blank for games not completed yet.")
        for i, row in week_games.iterrows():
            game = row["game"]
            home_team = row["home_team"]
            away_team = row["away_team"]

            # Check if result already exists
            existing = results_df[(results_df["week"] == selected_week) & (results_df["game"] == game)]
            home_score = existing["home_score"].values[0] if not existing.empty else ""
            away_score = existing["away_score"].values[0] if not existing.empty else ""

            st.subheader(f"{away_team} @ {home_team}")
            col1, col2 = st.columns(2)
            with col1:
                home_input = st.text_input(f"{home_team} Score", value=str(home_score), key=f"{game}_home")
            with col2:
                away_input = st.text_input(f"{away_team} Score", value=str(away_score), key=f"{game}_away")

            # Only add if either score is entered
            if home_input.strip() != "" or away_input.strip() != "":
                try:
                    home_val = int(home_input)
                    away_val = int(away_input)
                    updated_rows.append({
                        "week": selected_week,
                        "game": game,
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_score": home_val,
                        "away_score": away_val
                    })
                except ValueError:
                    st.warning(f"Scores for {game} must be integers.")

        submitted = st.form_submit_button("Save Results")
        if submitted:
            # Remove existing results for these games in this week
            for row in updated_rows:
                results_df = results_df[~((results_df["week"] == row["week"]) & (results_df["game"] == row["game"]))]
            # Append new/updated results
            results_df = pd.concat([results_df, pd.DataFrame(updated_rows)], ignore_index=True)
            results_df = results_df.sort_values(["week", "game"])
            results_df.to_csv(results_path, index=False)
            st.success("Results updated!")

def render_make_picks_tab(user, picks_df, weekly_games):
    current_week = get_current_week()
    st.header(f"Week {current_week} Picks — {user}")

    if weekly_games and len(weekly_games) > 0:
        if "last_updated" in weekly_games[0]:
            last_updated = datetime.fromisoformat(weekly_games[0]["last_updated"])
            st.caption(f"Lines last updated: {format_display_time(last_updated)}")

        user_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == current_week)]
        session_picks = []

        # Separate locked and unlocked games
        locked_games = []
        open_games = []
        for g in weekly_games:
            commence_time_str = g.get("commence_time", None)
            locked = game_has_started(commence_time_str) if commence_time_str else False
            if locked:
                locked_games.append(g)
            else:
                open_games.append(g)

        # Locked games section
        if locked_games:
            st.subheader("🔒 Locked Games")
            st.write("---")
            for g in locked_games:
                prev_pick = user_picks[user_picks["game"] == g["game"]]["pick"].values
                if len(prev_pick):
                    pick_row = user_picks[user_picks["game"] == g["game"]].iloc[0]
                    # Use the user's locked-in spread for display
                    formatted_game = format_game_with_spread(g["game"], float(pick_row["spread"]))
                else:
                    # Fallback to live spread if no pick
                    formatted_game = format_game_with_spread(g["game"], g["spread"])
                st.markdown(f"**{formatted_game}**")
                prev_pick = user_picks[user_picks["game"] == g["game"]]["pick"].values
                away_team, home_team = g["game"].split(" @ ") if "@" in g["game"] else g["game"].split(" vs. ")
                away_full = TEAM_NAME_MAPPING.get(away_team, away_team)
                home_full = TEAM_NAME_MAPPING.get(home_team, home_team)
                if len(prev_pick):
                    pick_row = user_picks[user_picks["game"] == g["game"]].iloc[0]
                    pick_team = pick_row["pick"]
                    pick_spread = pick_row["spread"]
                    pick_display = TEAM_DISPLAY_NAMES.get(pick_team, pick_team)
                    try:
                        spread_val = float(pick_spread)
                        if pick_team == away_full:
                            pick_spread_val = -spread_val
                        elif pick_team == home_full:
                            pick_spread_val = spread_val
                        else:
                            pick_spread_val = spread_val
                        sign = "+" if pick_spread_val > 0 else ""
                        st.write(f"Your Pick: {pick_display}")
                    except Exception:
                        st.write(f"Your Pick: {pick_display}")
                else:
                    st.write("No pick submitted.")
                st.divider()

        # Open games section (in a form)
        if open_games:
            st.subheader("🟢 Open Games")
            with st.form("make_picks_form"):
                for g in open_games:
                    formatted_game = format_game_with_spread(g["game"], g["spread"])
                    away_team, home_team = g["game"].split(" @ ") if "@" in g["game"] else g["game"].split(" vs. ")
                    away_full = TEAM_NAME_MAPPING.get(away_team, away_team)
                    home_full = TEAM_NAME_MAPPING.get(home_team, home_team)
                    away_display = TEAM_DISPLAY_NAMES.get(away_full, away_team)
                    home_display = TEAM_DISPLAY_NAMES.get(home_full, home_team)
                    teams_display = [away_display, home_display]
                    teams_full = [away_full, home_full]
                    prev_pick = user_picks[user_picks["game"] == g["game"]]["pick"].values
                    default_full = prev_pick[0] if len(prev_pick) else teams_full[0]
                    default_display = TEAM_DISPLAY_NAMES.get(default_full, default_full)

                    st.markdown(f"**{formatted_game}**")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        selected_display = st.selectbox(
                            "Make your pick:",
                            teams_display,
                            index=teams_display.index(default_display) if default_display in teams_display else 0,
                            key=f"{g['game']}_{user}"
                        )
                    with col2:
                        st.write("")  # For spacing/alignment

                    selected_full = teams_full[teams_display.index(selected_display)]
                    session_picks.append({
                        "week": current_week,
                        "user": user,
                        "game": g["game"],
                        "spread": g["spread"],
                        "pick": selected_full,
                        "timestamp": datetime.now().isoformat(timespec="seconds")
                    })
                    st.divider()

                # Submit/Reset buttons at the bottom of the form
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Submit Picks"):

                        # Get user's existing picks for the current week
                        user_week_picks = picks_df[(picks_df["week"] == current_week) & (picks_df["user"] == user)]

                        # For each locked game, keep the user's existing pick
                        locked_picks = user_week_picks[user_week_picks["game"].isin([g["game"] for g in locked_games])]

                        # For each open game, use the new pick from the form (session_picks)
                        # Remove all of this user's picks for the current week, then add back locked and new picks
                        new_picks_df = pd.concat([
                            picks_df[~((picks_df["week"] == current_week) & (picks_df["user"] == user))],
                            pd.DataFrame(session_picks),
                            locked_picks
                        ], ignore_index=True)
                        save_picks(new_picks_df)
                        st.success("✅ Picks submitted successfully!")
                        st.rerun()
                with col2:
                    if not st.session_state.show_reset_confirm:
                        if st.form_submit_button("Reset Picks"):
                            st.session_state.show_reset_confirm = True
                            st.rerun()
                    else:
                        if st.form_submit_button("Confirm Reset"):
                            new_picks_df = picks_df[~((picks_df["week"] == current_week) & (picks_df["user"] == user))]
                            save_picks(new_picks_df)
                            st.session_state.show_reset_confirm = False
                            st.success("🔄 Picks reset successfully!")
                            st.rerun()
                        if st.form_submit_button("Cancel"):
                            st.session_state.show_reset_confirm = False
                            st.rerun()

    st.subheader("Your Picks This Week")
    current_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == current_week)]
    if not current_picks.empty:
        current_picks_display = current_picks.copy()
        current_picks_display["formatted_game"] = current_picks_display.apply(
            lambda row: format_game_with_spread(row["game"], row["spread"]), 
            axis=1
        )
        current_picks_display["pick"] = current_picks_display["pick"].apply(
            lambda x: TEAM_DISPLAY_NAMES.get(x, x)
        )
        st.table(
            current_picks_display[["formatted_game", "pick"]].rename(columns={
                "formatted_game": "Game",
                "pick": "Pick"
            })
        )
    else:
        st.write("No picks submitted yet.")

def render_past_picks_tab(picks_df, user):
    """Render the Past Picks tab content"""
    st.header("Past Picks")

    # Filter controls - only show weeks prior to current week
    current_week = get_current_week()
    col1, col2 = st.columns(2)
    with col1:
        available_weeks = sorted([w for w in picks_df["week"].unique() if w < current_week]) if not picks_df.empty else []
        if available_weeks:
            selected_week = st.selectbox("Select Week:", available_weeks)
        else:
            st.info("No past weeks available yet.")
            selected_week = None
    
    with col2:
        if available_weeks:
            available_users = sorted(picks_df["user"].unique()) if not picks_df.empty else USERS
            selected_user = st.selectbox("Select User:", available_users, index=available_users.index(user) if user in available_users else 0)

    # Show filtered picks for past weeks only
    if selected_week and not picks_df.empty:
        filtered_picks = picks_df[(picks_df["week"] == selected_week) & (picks_df["user"] == selected_user)]
        if not filtered_picks.empty:
            results_df = pd.read_csv(RESULTS_FILE)
            scored_picks = score_all_picks(filtered_picks, results_df)
            scored_picks["formatted_game"] = scored_picks.apply(
                lambda row: format_game_with_spread(row["game"], row["spread"]), 
                axis=1
            )
            scored_picks["pick"] = scored_picks.apply(format_pick_with_spread_for_past_picks, axis=1)
            scored_picks["Result"] = scored_picks["result"].apply(result_to_emoji)
            st.table(
                scored_picks[["formatted_game", "pick", "Result"]].rename(columns={
                    "formatted_game": "Game",
                    "pick": "Pick",
                    "Result": "Result"
                })
            )
        else:
            st.write(f"No picks found for {selected_user} in Week {selected_week}.")

def render_group_picks_tab(picks_df):
    """Render the Group Picks tab content"""

    st.header("Group Picks")
    st.write("View everyone's picks for games that have already started or concluded.")

    # Get current week games and picks
    current_week = get_current_week()
    weekly_games = nfl_data.get_weekly_spreads(current_week)
    current_week_picks = picks_df[picks_df["week"] == current_week]
    results_df = pd.read_csv(RESULTS_FILE)
    concluded_games = set(results_df[results_df["week"] == current_week]["game"])
    scored_picks = score_all_picks(current_week_picks, results_df)

    # 1. Summary Table for Concluded Games
    week_picks = scored_picks[scored_picks["game"].isin(concluded_games)]
    if not week_picks.empty:
        summary = (
            week_picks.groupby("user")["result"]
            .apply(lambda x: (x == "correct").sum())
            .reset_index(name="correct")
        )
        summary["total"] = week_picks.groupby("user")["result"].count().values
        summary["correct_pct"] = summary["correct"] / summary["total"] * 100
        summary = summary.rename(columns={
            "user": "User",
            "correct": "Correct Picks",
            "correct_pct": "Correct Pick %",
            "total": "Total Picks"
        })
        summary = summary.sort_values("User")
        summary["Correct Pick %"] = summary["Correct Pick %"].apply(lambda x: f"{x:.1f}%")
        st.subheader("Summary Table")
        st.dataframe(
            summary[["User", "Correct Picks", "Total Picks", "Correct Pick %"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("No concluded games available for this week.")

    st.markdown("---")

    # 2. Tables for Each Game That Has Started (including in-progress and concluded)
    # Get all games that have started (not just concluded)
    started_games = set()
    # Add all games that have started (from weekly_games)
    for g in weekly_games:
        commence_time_str = g.get("commence_time", None)
        if commence_time_str and game_has_started(commence_time_str):
            started_games.add(g["game"])
    # Add all concluded games (from results.csv)
    started_games.update(concluded_games)

    # Show tables for all started games (including concluded)
    for game_name in sorted(started_games):
        # Format as "Chiefs @ Chargers"
        if "@" in game_name:
            away_team, home_team = game_name.split(" @ ")
        else:
            home_team, away_team = game_name.split(" vs. ")
        away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
        home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
        display_game = f"{away_display} @ {home_display}"

        st.markdown(f"### {display_game}")
        # Show all picks for this game
        game_picks = scored_picks[scored_picks["game"] == game_name]
        if not game_picks.empty:
            # Format the Pick column as "Team (+/-spread)"
            def format_pick(row):
                pick_team = TEAM_DISPLAY_NAMES.get(row["pick"], row["pick"])
                spread = float(row["spread"])
                # Determine if pick is home or away
                if pick_team == away_display:
                    pick_spread = -spread
                elif pick_team == home_display:
                    pick_spread = spread
                else:
                    pick_spread = spread  # fallback
                sign = "+" if pick_spread > 0 else ""
                return f"{pick_team} ({sign}{pick_spread:.1f})"

            display_df = game_picks[["user", "pick", "spread", "result"]].copy()
            display_df["Pick"] = display_df.apply(format_pick, axis=1)
            display_df = display_df.rename(columns={"user": "User"})
            display_df = display_df[["User", "Pick", "result"]].sort_values("User").reset_index(drop=True)

            # Highlight only the Pick column if game is concluded
            def highlight_pick_only(row):
                colors = ["", ""]
                if game_name in concluded_games:
                    if row["result"] == "correct":
                        colors[1] = "background-color: rgba(34,197,94,0.25);"  # green
                    elif row["result"] == "incorrect":
                        colors[1] = "background-color: rgba(239,68,68,0.25);"  # red
                    elif row["result"] == "push":
                        colors[1] = "background-color: rgba(251,191,36,0.25);"  # yellow
                return colors + [""]

            display_df = display_df.reset_index(drop=True)
            styled = display_df[["User", "Pick", "result"]].reset_index(drop=True).style.apply(highlight_pick_only, axis=1)
            st.dataframe(
                styled,
                use_container_width=True,
                column_order=["User", "Pick"]
            )
        else:
            st.write("No picks submitted for this game.")
        st.write("---")

    # 3. Upcoming Games (not started yet)
    if weekly_games:
        upcoming_games = [g for g in weekly_games if not game_has_started(g.get("commence_time", ""))]
        if upcoming_games:
            st.subheader("🔒 Upcoming Games")
            st.write("Picks will be revealed when these games start:")
            for g in upcoming_games:
                # Format as "Chiefs @ Chargers"
                if "@" in g["game"]:
                    away_team, home_team = g["game"].split(" @ ")
                else:
                    home_team, away_team = g["game"].split(" vs. ")
                away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
                home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
                display_game = f"{away_display} @ {home_display}"
                st.write(f"• {display_game}")


def render_group_data_tab(picks_df):
    """Render the Group Data tab content"""
    st.header("Group Statistics")
    
    # Overall Statistics
    if not picks_df.empty and results_available:
        st.subheader("📊 Overall Pick Trends")
        
        results_df = pd.read_csv(RESULTS_FILE)
        scored_picks = score_all_picks(picks_df, results_df)
        concluded_games = set(results_df["game"])
        completed_picks = scored_picks[scored_picks["game"].isin(concluded_games)]

        total_picks = completed_picks['result'].isin(['correct', 'incorrect', 'push']).sum()
        
        if total_picks > 0:  # Only show stats if we have concluded games
            # Get spreads for each pick to determine favorite/underdog
            picks_with_spreads = completed_picks.copy()
            picks_with_spreads['is_favorite'] = picks_with_spreads.apply(
                lambda row: (float(row['spread']) < 0 and row['pick'] in row['game'].split(' @ ')[1]) or 
                            (float(row['spread']) > 0 and row['pick'] in row['game'].split(' @ ')[0]),
                axis=1
            )

            favorites_picked = picks_with_spreads['is_favorite'].sum()
            underdogs_picked = total_picks - favorites_picked

            total_correct = (completed_picks['result'] == 'correct').sum()
            favorites_correct = ((completed_picks['result'] == 'correct') & picks_with_spreads['is_favorite']).sum()
            underdogs_correct = ((completed_picks['result'] == 'correct') & ~picks_with_spreads['is_favorite']).sum()
            
            stats_data = {
                'Metric': [
                    'Total Correct Pick %',
                    'Favorites Correct %',
                    'Underdogs Correct %',
                    'Favorites Picked %',
                    'Underdogs Picked %'
                ],
                'Value': [
                    f"{(total_correct/total_picks*100):.1f}%",
                    f"{(favorites_correct/favorites_picked*100):.1f}%" if favorites_picked else "N/A",
                    f"{(underdogs_correct/underdogs_picked*100):.1f}%" if underdogs_picked else "N/A",
                    f"{(favorites_picked/total_picks*100):.1f}%",
                    f"{(underdogs_picked/total_picks*100):.1f}%"
                ]
            }
            
            st.dataframe(
                pd.DataFrame(stats_data),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No completed games yet to show statistics.")
    else:
        st.info("No completed games yet to show statistics.")
        
    st.markdown("---")
    
    # Update the team charts to only use completed games
    if results_available:
        results_df = pd.read_csv(RESULTS_FILE)
        completed_picks = score_all_picks(picks_df, results_df)
        completed_picks = completed_picks[completed_picks['result'].isin(['correct', 'incorrect', 'push'])]
        
        # --- NEW: Find all teams that have played in completed games ---
        teams_played = set()
        for game in results_df["game"]:
            if "@" in game:
                away, home = game.split(" @ ")
            else:
                home, away = game.split(" vs. ")
            teams_played.update([away.strip(), home.strip()])

        # --- Most Picked Teams ---
        st.subheader("📈 Most Picked Teams")
        team_picks = completed_picks.groupby("pick").size().reindex(teams_played, fill_value=0).reset_index()
        team_picks.columns = ["pick", "count"]
        top_teams = team_picks.nlargest(5, "count")
        
        display_names = []
        colors = []
        for team in top_teams["pick"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)
        
        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=top_teams["count"],
                marker_color=colors,
                text=top_teams["count"],
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat="d",
                dtick=1,
                tick0=0,
                showgrid=True
            ),
            showlegend=False,
            yaxis_title="Times Picked",
            dragmode=False
        )
        st.plotly_chart(fig, use_container_width=True, key="most_picked")
        
        # --- Least Picked Teams ---
        st.subheader("📉 Least Picked Teams")
        bottom_teams = team_picks.nsmallest(5, "count")
        
        display_names = []
        colors = []
        for team in bottom_teams["pick"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)
        
        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=bottom_teams["count"],
                marker_color=colors,
                text=bottom_teams["count"],
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat="d",
                dtick=1,
                tick0=0,
                showgrid=True
            ),
            showlegend=False,
            yaxis_title="Times Picked",
            dragmode=False
        )
        st.plotly_chart(fig, use_container_width=True, key="least_picked")

        # --- ATS Records ---
        ats_records = get_user_ats_records(picks_df, results_df)

        # Hot teams
        st.subheader("🔥 Best Teams Against the Spread (User Picks)")
        hot_teams = ats_records.nlargest(5, 'pct')

        display_names = []
        colors = []
        for team in hot_teams["team"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)

        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=hot_teams["pct"].multiply(100),
                marker_color=colors,
                text=hot_teams["pct"].apply(lambda x: f"{x*100:.1f}%"),
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat=".0f",
                range=[0, 100],
                title="Cover %"
            ),
            dragmode=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="best_ats_user")

        # Cold teams
        st.subheader("❄️ Worst Teams Against the Spread (User Picks)")
        cold_teams = ats_records.nsmallest(5, 'pct')

        display_names = []
        colors = []
        for team in cold_teams["team"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)

        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=cold_teams["pct"].multiply(100),
                marker_color=colors,
                text=cold_teams["pct"].apply(lambda x: f"{x*100:.1f}%"),
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat=".0f",
                range=[0, 100],
                title="Cover %"
            ),
            dragmode=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="worst_ats_user")

def render_leaderboards_tab(picks_df):
    """Render the Leaderboards tab content"""
    st.header("Leaderboards")
    st.subheader("🏆 Weekly Leaderboard")
    if results_available:
        results_df = pd.read_csv(RESULTS_FILE)
        concluded_games = set(results_df["game"])
        scored_picks = score_all_picks(picks_df, results_df)
        completed_picks = scored_picks[scored_picks["game"].isin(concluded_games)]

        # Add week selector
        week_options = sorted(completed_picks["week"].unique(), reverse=True)
        selected_week = st.selectbox("Select Week:", week_options, key="leaderboard_week")

        # Filter by selected week
        week_picks = completed_picks[completed_picks["week"] == selected_week]

        # Only count non-pushes for correct pick %
        non_push_week_picks = week_picks[week_picks["result"] != "push"]
        weekly = (
            non_push_week_picks.groupby(["week", "user"])["result"]
            .apply(lambda x: (x == "correct").sum())
            .reset_index(name="correct")
        )
        weekly["total"] = non_push_week_picks.groupby(["week", "user"])["result"].count().values
        weekly["correct_pct"] = weekly["correct"] / weekly["total"] * 100

        # Add Pushes column
        push_counts = week_picks[week_picks["result"] == "push"].groupby("user").size().to_dict()
        weekly["Pushes"] = weekly["user"].map(lambda u: push_counts.get(u, 0))

        weekly = add_rank(weekly, ["correct", "correct_pct"])
        weekly["correct_pct"] = weekly["correct_pct"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            weekly.rename(columns={
                "user": "User",
                "week": "Week",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "Rank": "Rank",
                "Pushes": "Pushes"
            })[["Rank", "User", "Week", "Correct Picks", "Correct Pick %", "Pushes"]],
            use_container_width=True,
            hide_index=True
        )

        # Season leaderboard
    st.subheader("🏆 Season Total Leaderboard")
    if results_available:
        results_df = pd.read_csv(RESULTS_FILE)
        scored_picks = score_all_picks(picks_df, results_df)
        concluded_games = set(results_df["game"])
        completed_picks = scored_picks[scored_picks["game"].isin(concluded_games)].copy()
        completed_picks["is_correct"] = completed_picks["result"] == "correct"

        # Find best team for each user (most correct picks)
        best_team = (
            completed_picks[completed_picks["is_correct"]]
            .groupby(["user", "pick"])
            .size()
            .reset_index(name="correct_count")
            .sort_values(["user", "correct_count"], ascending=[True, False])
            .drop_duplicates("user")
            .set_index("user")["pick"]
            .to_dict()
        )

        non_push_picks = completed_picks[completed_picks["result"] != "push"]
        total = (
            non_push_picks.groupby("user")["is_correct"]
            .agg(correct="sum", total="count")
            .reset_index()
        )
        total["correct_pct"] = total["correct"] / total["total"] * 100
        total = add_rank(total, ["correct", "correct_pct"])
        total["correct_pct"] = total["correct_pct"].apply(lambda x: f"{x:.1f}%")
        total["Best Team"] = total["user"].map(lambda u: TEAM_DISPLAY_NAMES.get(best_team.get(u, ""), best_team.get(u, "")))

        # Add Pushes column
        push_counts = completed_picks[completed_picks["result"] == "push"].groupby("user").size().to_dict()
        total["Pushes"] = total["user"].map(lambda u: push_counts.get(u, 0))

        st.dataframe(
            total.rename(columns={
                "user": "User",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "Rank": "Rank",
                "Best Team": "Best Team",
                "Pushes": "Pushes"
            })[["Rank", "User", "Correct Picks", "Correct Pick %", "Pushes", "Best Team"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No results available yet.")

def render_punishment_reward_tab():
    st.header("🏆 Punishment & Reward")
    st.markdown("""
**End-of-Season Golf & Bar Challenge**

After the NFL season, all four players will go out and play 9 holes of golf together.

- **Punishment:**  
  - The player with the lowest season win percentage ("the loser") must drink **9 drinks in 9 holes**.
  - For every **3 strokes over par** the loser shoots, they must buy a round for the other 3 members.

- **Reward:**  
  - After golf, everyone will go to a bar.
  - The **season winner** (best win percentage) gets their entire bill (all food and drinks from the bar and during golf) **paid for by the other 3 players** (split evenly).

**Good luck! 🍻⛳**
""")

def main():
    st.title("🏈 NFL Pick'em Tracker")
    st.caption("For entertainment purposes only. Tracks friendly picks, does not involve betting or money.")

    # Mode selection
    if "mode" not in st.session_state:
        st.session_state.mode = None

    if st.session_state.mode is None:
        mode = st.radio("Choose mode:", ["Live Mode (Password Required)", "Public Demo"])
        if st.button("Continue"):
            st.session_state.mode = mode
            st.rerun()
    else:
        if st.button("Switch Mode"):
            st.session_state.mode = None
            st.rerun()

        if st.session_state.mode == "Live Mode (Password Required)":
            render_live_mode()
        else:
            render_demo_mode()

def render_live_mode():
    """Render the live mode content"""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_authenticated" not in st.session_state:
        st.session_state.user_authenticated = False

    if not st.session_state.user_authenticated:
        pw = st.text_input("Enter your user password:", type="password")
        if st.button("Login"):
            # Check password against all users
            for username, password in st.secrets["users"].items():
                if pw == password:
                    st.session_state.user = username
                    st.session_state.user_authenticated = True
                    st.rerun()
                    break
            else:  # No matching password found
                st.error("❌ Invalid password")
                st.stop()
        st.stop()

    # Only shown after successful authentication
    user = st.session_state.user
    tabs = st.tabs([
        "Make Picks", "Past Picks", "Group Picks", "Group Data", 
        "Leaderboards", "Update Results", "Punishment & Reward"
    ])
    picks_df = load_picks()

    # Render each tab
    with tabs[0]:
        current_week = get_current_week()
        render_make_picks_tab(user, picks_df, nfl_data.get_weekly_spreads(current_week))
    
    with tabs[1]:
        render_past_picks_tab(picks_df, user)
    
    with tabs[2]:
        render_group_picks_tab(picks_df)
    
    with tabs[3]:
        render_group_data_tab(picks_df)
    
    with tabs[4]:
        render_leaderboards_tab(picks_df)
    with tabs[5]:
        render_update_results_tab()
    with tabs[6]:
        render_punishment_reward_tab()

def render_demo_mode():
    """Render the demo mode content"""
    st.info("Public demo — view a sample version of the app with pre-filled data.")

    demo_tabs = st.tabs(["Make Picks", "Past Picks", "Group Picks", "Group Data", "Leaderboards"])

    # Load demo data from CSVs
    demo_picks_df = pd.read_csv(Path(DATA_DIR) / "demo_picks.csv")
    demo_results_df = pd.read_csv(Path(DATA_DIR) / "demo_results.csv")

    # For demo, set CURRENT_WEEK to max week in picks
    demo_current_week = demo_picks_df["week"].max()

    # Make Picks Tab 
    with demo_tabs[0]:
        st.header("Make Picks (Demo)")
        st.warning("This is a demo. Picks are not saved and do not affect any leaderboard.")

        # Load mock Week 4 schedule
        demo_make_picks_df = pd.read_csv(Path(DATA_DIR) / "demo_make_picks.csv")
        demo_week = 4
        demo_user = "DemoUser"

        # Use session state to store demo picks
        if "demo_picks_this_week" not in st.session_state:
            st.session_state.demo_picks_this_week = []

        # Show a success message if picks were "submitted"
        if st.session_state.get("demo_picks_submitted", False):
            st.success("✅ Demo picks submitted!")

        # Build pick form (always visible)
        demo_picks = []
        for i, row in demo_make_picks_df.iterrows():
            formatted_game = format_game_with_spread(row["game"], row["spread"])
            if "@" in row["game"]:
                away_team, home_team = row["game"].split(" @ ")
            else:
                home_team, away_team = row["game"].split(" vs. ")
            away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
            home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
            teams_display = [away_display, home_display]
            # Use previous pick if available, else default to first team
            prev_pick = None
            for pick_row in st.session_state.demo_picks_this_week:
                if pick_row["game"] == row["game"]:
                    prev_pick = pick_row["pick"]
                    break
            default_display = TEAM_DISPLAY_NAMES.get(prev_pick, teams_display[0]) if prev_pick else teams_display[0]
            pick = st.selectbox(
                formatted_game,
                teams_display,
                key=f"demo_pick_{i}",
                index=teams_display.index(default_display) if default_display in teams_display else 0
            )
            # Store full name for pick
            pick_full = away_team if pick == away_display else home_team
            demo_picks.append({
                "week": demo_week,
                "user": demo_user,
                "game": row["game"],
                "spread": row["spread"],
                "pick": pick_full,
                "timestamp": datetime.now().isoformat(timespec="seconds")
            })

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit Picks"):
                st.session_state.demo_picks_this_week = demo_picks
                st.session_state.demo_picks_submitted = True
                st.success("✅ Demo picks submitted!")
                st.rerun()
        with col2:
            if st.button("Reset Picks"):
                st.session_state.demo_picks_this_week = []
                st.session_state.demo_picks_submitted = False
                # Also reset all selectboxes
                for i in range(len(demo_make_picks_df)):
                    st.session_state.pop(f"demo_pick_{i}", None)
                st.rerun()

        # Show "Your Picks This Week" table if picks exist
        if st.session_state.demo_picks_this_week:
            picks_df = pd.DataFrame(st.session_state.demo_picks_this_week)
            picks_df["formatted_game"] = picks_df.apply(
                lambda row: format_game_with_spread(row["game"], row["spread"]), axis=1
            )
            picks_df["pick"] = picks_df["pick"].apply(lambda x: TEAM_DISPLAY_NAMES.get(x, x))
            st.subheader("Your Picks This Week")
            st.table(
                picks_df[["formatted_game", "pick"]].rename(columns={
                    "formatted_game": "Game",
                    "pick": "Pick"
                })
            )

    # Past Picks Tab
    with demo_tabs[1]:
        st.header("Past Picks")
        col1, col2 = st.columns(2)
        with col1:
            week_options = sorted(demo_picks_df["week"].unique(), reverse=True)
            selected_week = st.selectbox("Select Week (Demo):", week_options)
        with col2:
            user_options = sorted(demo_picks_df["user"].unique())
            selected_user = st.selectbox("Select User (Demo):", user_options)

        filtered_picks = demo_picks_df[
            (demo_picks_df["week"] == selected_week) & 
            (demo_picks_df["user"] == selected_user)
        ]
        if not filtered_picks.empty:
            display_df = filtered_picks.merge(
                demo_results_df[["week", "game", "covered"]], 
                on=["week", "game"]
            )
            display_df["formatted_game"] = display_df.apply(
                lambda row: format_game_with_spread(row["game"], row["spread"]), 
                axis=1
            )
            display_df["pick"] = display_df["pick"].apply(
                lambda x: TEAM_DISPLAY_NAMES.get(x, x)
            )
            display_df["covered"] = display_df["covered"].apply(
                lambda x: TEAM_DISPLAY_NAMES.get(x, x)
            )
            display_df["Result"] = display_df.apply(
                lambda row: result_to_emoji("correct" if row["pick"] == row["covered"] else "incorrect"), axis=1
            )
            st.dataframe(
                display_df[["formatted_game", "pick", "Result"]].rename(columns={
                    "formatted_game": "Game",
                    "pick": "Pick",
                    "Result": "Result"
                }),
                use_container_width=True,
                hide_index=True,
                height=598
            )
        else:
            st.write(f"No picks found for {selected_user} in Week {selected_week}.")

    # Group Picks Tab
    with demo_tabs[2]:
        st.header("Group Picks")
        st.write("View everyone's picks for games that have started:")

        # Week selector for demo group picks (reverse order)
        week_options = sorted(demo_picks_df["week"].unique(), reverse=True)
        selected_week = st.selectbox("Select Week (Demo):", week_options, key="demo_group_picks_week")
        st.caption("Note: In live mode, the Group Picks tab always shows the current week only.")

        week_games = demo_picks_df[demo_picks_df["week"] == selected_week]["game"].unique()
        week_results = demo_results_df[demo_results_df["week"] == selected_week]

        for game in week_games:
            if "@" in game:
                away_team, home_team = game.split(" @ ")
            else:
                home_team, away_team = game.split(" vs. ")
            away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
            home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
            st.write(f"### {away_display} @ {home_display}")

            game_picks = demo_picks_df[(demo_picks_df["week"] == selected_week) & (demo_picks_df["game"] == game)]
            if not game_picks.empty:
                merged = game_picks.merge(
                    week_results[["week", "game", "covered"]],
                    on=["week", "game"]
                )
                merged["Pick"] = merged.apply(
                    lambda row: format_pick_with_spread(row["pick"], row["spread"], row["game"]), axis=1
                )
                merged["Result"] = merged.apply(
                    lambda row: result_to_emoji("correct" if row["pick"] == row["covered"] else "incorrect"),
                    axis=1
                )
                display_df = merged[["user", "Pick", "Result"]].rename(columns={"user": "User"})
                display_df = display_df.sort_values("User")
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
        st.write("---")
        concluded_games = set(week_results["game"])
        week_picks = demo_picks_df[(demo_picks_df["week"] == selected_week) & (demo_picks_df["game"].isin(concluded_games))]
        if not week_picks.empty:
            merged = week_picks.merge(
                week_results[["week", "game", "covered"]],
                on=["week", "game"]
            )
            summary = (
                merged.groupby("user")
                .apply(lambda df: (df["pick"] == df["covered"]).sum())
                .reset_index(name="correct")
            )
            summary["total"] = merged.groupby("user")["pick"].count().values
            summary["correct_pct"] = summary["correct"] / summary["total"] * 100
            summary = summary.rename(columns={
                "user": "User",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "total": "Total Picks"
            })
            summary = summary.sort_values("User")
            summary["Correct Pick %"] = summary["Correct Pick %"].apply(lambda x: f"{x:.1f}%")
            st.subheader("Group Scoreboard")
            st.dataframe(
                summary[["User", "Correct Picks", "Total Picks", "Correct Pick %"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("No concluded games available for this week.")
            
    # Group Data Tab
    with demo_tabs[3]:
        st.header("Group Statistics")

        # Calculate statistics from demo data
        demo_merged = demo_picks_df.merge(demo_results_df, on=['week', 'game'])
        total_picks = len(demo_merged)

        # Get spreads for each pick to determine favorite/underdog
        picks_with_spreads = demo_merged.copy()
        picks_with_spreads['is_favorite'] = picks_with_spreads.apply(
            lambda row: (row['spread'] < 0 and row['pick'] in row['game'].split(' @ ')[1]) or 
                        (row['spread'] > 0 and row['pick'] in row['game'].split(' @ ')[0]),
            axis=1
        )

        # Calculate statistics
        favorites_picked = picks_with_spreads['is_favorite'].sum()
        underdogs_picked = total_picks - favorites_picked
        total_correct = (demo_merged['pick'] == demo_merged['covered']).sum()
        favorites_correct = ((demo_merged['pick'] == demo_merged['covered']) & picks_with_spreads['is_favorite']).sum()
        underdogs_correct = ((demo_merged['pick'] == demo_merged['covered']) & ~picks_with_spreads['is_favorite']).sum()

        # Create metrics DataFrame with calculated values
        metrics_data = {
            'Metric': [
                'Total Correct Pick %',
                'Favorites Correct %',
                'Underdogs Correct %',
                'Favorites Picked %',
                'Underdogs Picked %'
            ],
            'Value': [
                f"{(total_correct/total_picks*100):.1f}%",
                f"{(favorites_correct/favorites_picked*100):.1f}%" if favorites_picked else "N/A",
                f"{(underdogs_correct/underdogs_picked*100):.1f}%" if underdogs_picked else "N/A",
                f"{(favorites_picked/total_picks*100):.1f}%",
                f"{(underdogs_picked/total_picks*100):.1f}%"
            ]
        }
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        # Most Picked Teams graph
        st.subheader("📈 Most Picked Teams")
        team_picks = demo_merged.groupby("pick").size().reset_index(name="count")
        top_teams = team_picks.nlargest(5, "count")
        display_names = []
        colors = []
        for team in top_teams["pick"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)
        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=top_teams["count"],
                marker_color=colors,
                text=top_teams["count"],
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat="d",
                dtick=1,
                tick0=0,
                showgrid=True
            ),
            showlegend=False,
            yaxis_title="Times Picked",
            dragmode=False
        )
        st.plotly_chart(fig, use_container_width=True, key="demo_most_picked")

        # Least Picked Teams graph
        st.subheader("📉 Least Picked Teams")
        bottom_teams = team_picks.nsmallest(5, "count")
        display_names = []
        colors = []
        for team in bottom_teams["pick"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)
        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=bottom_teams["count"],
                marker_color=colors,
                text=bottom_teams["count"],
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat="d",
                dtick=1,
                tick0=0,
                showgrid=True
            ),
            showlegend=False,
            yaxis_title="Times Picked",
            dragmode=False
        )
        st.plotly_chart(fig, use_container_width=True, key="demo_least_picked")

        # ATS Records (based on demo results)
        ats_records = pd.DataFrame()
        for team in NFL_TEAM_COLORS.keys():
            games_covered = len(demo_results_df[demo_results_df['covered'] == team])
            total_games = len(demo_results_df[demo_results_df['game'].str.contains(team)])
            if total_games > 0:
                ats_records = pd.concat([ats_records, pd.DataFrame({
                    'team': [team],
                    'covered': [games_covered],
                    'total': [total_games],
                    'pct': [games_covered/total_games]
                })])

        # Hot teams
        st.subheader("🔥 Best Teams Against the Spread")
        hot_teams = ats_records.nlargest(5, 'pct')
        display_names = []
        colors = []
        for team in hot_teams["team"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)
        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=hot_teams["pct"].multiply(100),
                marker_color=colors,
                text=hot_teams["pct"].apply(lambda x: f"{x*100:.1f}%"),
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat=".0f",
                range=[0, 100], 
                title="Cover %"
            ),
            dragmode=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="demo_hot_teams")

        # Cold teams
        st.subheader("❄️ Worst Teams Against the Spread")
        cold_teams = ats_records.nsmallest(5, 'pct')
        display_names = []
        colors = []
        for team in cold_teams["team"]:
            display_name, color = get_team_display_and_color(team)
            display_names.append(display_name)
            colors.append(color)
        fig = go.Figure(data=[
            go.Bar(
                x=display_names,
                y=cold_teams["pct"].multiply(100),
                marker_color=colors,
                text=cold_teams["pct"].apply(lambda x: f"{x*100:.1f}%"),
                textposition='auto',
            )
        ])
        fig.update_layout(
            yaxis=dict(
                tickformat=".0f",
                range=[0, 100],  
                title="Cover %"
            ),
            dragmode=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, key="demo_cold_teams")

    # Leaderboards Tab
    with demo_tabs[4]:
        st.header("Leaderboards")

        # Weekly Leaderboard
        st.subheader("🏆 Weekly Leaderboard")
        week_options = sorted(demo_picks_df["week"].unique(), reverse=True)
        selected_week = st.selectbox("Select Week (Demo):", week_options, key="demo_leaderboard_week")

        weekly = (
            demo_picks_df.merge(demo_results_df, on=["week", "game"])
            .assign(correct=lambda df: df["pick"] == df["covered"])
            .query("week == @selected_week")
            .groupby(["week", "user"])
            .agg(correct=("correct", "sum"), total=("pick", "count"))
            .reset_index()
        )
        weekly["correct_pct"] = weekly["correct"] / weekly["total"] * 100
        weekly = add_rank(weekly, ["correct", "correct_pct"])
        weekly["correct_pct"] = weekly["correct_pct"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            weekly.rename(columns={
                "user": "User",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "Rank": "Rank"
            })[["Rank", "User", "Correct Picks", "Correct Pick %"]],
            use_container_width=True,
            hide_index=True
        )

        # Season leaderboard
        st.subheader("🏆 Season Total Leaderboard")
        merged = demo_picks_df.merge(demo_results_df, on=["week", "game"])
        merged["is_correct"] = merged["pick"] == merged["covered"]

        # Find best team for each user
        best_team = (
            merged[merged["is_correct"]]
            .groupby(["user", "pick"])
            .size()
            .reset_index(name="correct_count")
            .sort_values(["user", "correct_count"], ascending=[True, False])
            .drop_duplicates("user")
            .set_index("user")["pick"]
            .to_dict()
        )

        total = (
            merged.groupby("user")["is_correct"]
            .agg(correct="sum", total="count")
            .reset_index()
        )
        total["correct_pct"] = total["correct"] / total["total"] * 100
        total = add_rank(total, ["correct", "correct_pct"])
        total["correct_pct"] = total["correct_pct"].apply(lambda x: f"{x:.1f}%")
        total["Best Team"] = total["user"].map(lambda u: TEAM_DISPLAY_NAMES.get(best_team.get(u, ""), best_team.get(u, "")))
        st.dataframe(
            total.rename(columns={
                "user": "User",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "Rank": "Rank",
                "Best Team": "Best Team"
            })[["Rank", "User", "Correct Picks", "Correct Pick %", "Best Team"]],
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
    """
    <hr style="margin-top:2em;margin-bottom:1em;">
    <div style="text-align:center; font-size: 1.1em;">
        🔗 Questions or feedback? Connect with me:<br>
        <a href="https://github.com/jackewings" target="_blank">GitHub</a> |
        <a href="https://www.linkedin.com/in/jack-ewings-profile/" target="_blank">LinkedIn</a>
    </div>
    """,
    unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()