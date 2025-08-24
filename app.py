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
    CURRENT_WEEK,
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

def render_make_picks_tab(user, picks_df, weekly_games):
    """Render the Make Picks tab content"""
    st.header(f"Week {CURRENT_WEEK} Picks — {user}")
    
    if weekly_games and len(weekly_games) > 0:
        if "last_updated" in weekly_games[0]:
            last_updated = datetime.fromisoformat(weekly_games[0]["last_updated"])
            st.caption(f"Lines last updated: {format_display_time(last_updated)}")
            
        user_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK)]
        session_picks = []
        for g in weekly_games:
            formatted_game = format_game_with_spread(g["game"], g["spread"])
            st.write(formatted_game)
            
            # Extract teams from game string
            if "@" in g["game"]:
                away_team, home_team = g["game"].split(" @ ")
            else:
                home_team, away_team = g["game"].split(" vs. ")
            
            # Get full names first
            away_full = TEAM_NAME_MAPPING.get(away_team, away_team)
            home_full = TEAM_NAME_MAPPING.get(home_team, home_team)
            
            # Convert to display names for UI
            away_display = TEAM_DISPLAY_NAMES.get(away_full, away_team)
            home_display = TEAM_DISPLAY_NAMES.get(home_full, home_team)
            
            teams_display = [away_display, home_display]  # For display in selectbox
            teams_full = [away_full, home_full]  # For storing picks
            
            commence_time_str = g.get("commence_time", None)
            locked = game_has_started(commence_time_str) if commence_time_str else False
            prev_pick = user_picks[user_picks["game"] == g["game"]]["pick"].values
            default_full = prev_pick[0] if len(prev_pick) else teams_full[0]
            default_display = TEAM_DISPLAY_NAMES.get(default_full, default_full)
            
            if locked:
                st.write(f"**{formatted_game}** — Locked (Game Started)")
                if len(prev_pick):
                    display_pick = TEAM_DISPLAY_NAMES.get(prev_pick[0], prev_pick[0])
                    st.write(f"Your pick: {display_pick}")
                else:
                    st.write("No pick submitted.")
            else:
                selected_display = st.selectbox(
                    "Make your pick:",
                    teams_display,
                    index=teams_display.index(default_display) if default_display in teams_display else 0,
                    key=f"{g['game']}_{user}"
                )
                # Convert display name back to full name for storage
                selected_full = teams_full[teams_display.index(selected_display)]
                session_picks.append({
                    "week": CURRENT_WEEK,
                    "user": user,
                    "game": g["game"],
                    "spread": g["spread"],
                    "pick": selected_full,
                    "timestamp": datetime.now().isoformat(timespec="seconds")
                })
        
        # Add Submit/Reset buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit Picks"):
                new_picks_df = pd.concat([
                    picks_df[~((picks_df["week"] == CURRENT_WEEK) & (picks_df["user"] == user))],
                    pd.DataFrame(session_picks)
                ], ignore_index=True)
                save_picks(new_picks_df)
                st.success("✅ Picks submitted successfully!")
                st.rerun()
        
        with col2:
            if not st.session_state.show_reset_confirm:
                if st.button("Reset Picks"):
                    st.session_state.show_reset_confirm = True
                    st.rerun()
            else:
                if st.button("Confirm Reset"):
                    new_picks_df = picks_df[~((picks_df["week"] == CURRENT_WEEK) & (picks_df["user"] == user))]
                    save_picks(new_picks_df)
                    st.session_state.show_reset_confirm = False
                    st.success("🔄 Picks reset successfully!")
                    st.rerun()
                if st.button("Cancel"):
                    st.session_state.show_reset_confirm = False
                    st.rerun()

    st.subheader("Your Picks This Week")
    current_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK)]
    if not current_picks.empty:
        # Create display DataFrame with formatted games
        current_picks_display = current_picks.copy()
        current_picks_display["formatted_game"] = current_picks_display.apply(
            lambda row: format_game_with_spread(row["game"], row["spread"]), 
            axis=1
        )
        # Convert pick to display name
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

def render_past_picks_tab(picks_df):
    """Render the Past Picks tab content"""
    st.header("Past Picks")

# Filter controls - only show weeks prior to current week
    col1, col2 = st.columns(2)
    with col1:
        available_weeks = sorted([w for w in picks_df["week"].unique() if w < CURRENT_WEEK]) if not picks_df.empty else []
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
            scored_picks["pick"] = scored_picks["pick"].apply(
                lambda x: TEAM_DISPLAY_NAMES.get(x, x)
            )
            scored_picks["Result"] = scored_picks["result"].apply(result_to_emoji)
            st.dataframe(
                scored_picks[["formatted_game", "pick", "Result"]].rename(columns={
                    "formatted_game": "Game",
                    "pick": "Pick",
                    "Result": "Result"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write(f"No picks found for {selected_user} in Week {selected_week}.")

def render_group_picks_tab(picks_df):
    """Render the Group Picks tab content"""
    st.header("Group Picks")

    st.write("View everyone's picks for games that have already started.")

    # Get current week games and their start status
    weekly_games = nfl_data.get_weekly_spreads(CURRENT_WEEK)
    current_week_picks = picks_df[picks_df["week"] == CURRENT_WEEK]

    if weekly_games:
        for g in weekly_games:
            commence_time_str = g.get("commence_time", None)
            game_started = game_has_started(commence_time_str) if commence_time_str else False

            if game_started:
                # Show game as "Vikings @ Bears" (no spread)
                if "@" in g["game"]:
                    away_team, home_team = g["game"].split(" @ ")
                else:
                    home_team, away_team = g["game"].split(" vs. ")
                away_display = TEAM_DISPLAY_NAMES.get(away_team, away_team)
                home_display = TEAM_DISPLAY_NAMES.get(home_team, home_team)
                st.write(f"• {away_display} @ {home_display}")

                # Get all picks for this game
                game_picks = current_week_picks[current_week_picks["game"] == g["game"]]
                if not game_picks.empty:
                    results_df = pd.read_csv(RESULTS_FILE)
                    scored_picks = score_all_picks(game_picks, results_df)
                    # Format pick with spread for each user
                    scored_picks["Pick"] = scored_picks.apply(
                        lambda row: format_pick_with_spread(row["pick"], row["spread"], row["game"]), axis=1
                    )
                    scored_picks["Result"] = scored_picks["result"].apply(result_to_emoji)
                    display_df = scored_picks[["user", "Pick", "Result"]].rename(columns={"user": "User"})
                    display_df = display_df.sort_values("User")
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.write("No picks submitted for this game.")

                st.write("---")

        # Show upcoming games (not started yet)
        upcoming_games = [g for g in weekly_games if not game_has_started(g.get("commence_time", ""))]
        if upcoming_games:
            st.subheader("🔒 Upcoming Games")
            st.write("Picks will be revealed when these games start:")
            for g in upcoming_games:
                formatted_game = format_game_with_spread(g["game"], g["spread"])
                st.write(f"• {formatted_game}")

        # Summary Table for Concluded Games
        results_df = pd.read_csv(RESULTS_FILE)
        concluded_games = set(results_df["game"])
        week_picks = current_week_picks[current_week_picks["game"].isin(concluded_games)]
        if not week_picks.empty:
            scored_picks = score_all_picks(week_picks, results_df)
            summary = (
                scored_picks.groupby("user")["result"]
                .apply(lambda x: (x == "correct").sum())
                .reset_index(name="correct")
            )
            summary["total"] = scored_picks.groupby("user")["result"].count().values
            summary["correct_pct"] = summary["correct"] / summary["total"] * 100
            summary = summary.rename(columns={
                "user": "User",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "total": "Total Picks"
            })
            summary = summary.sort_values("User")
            summary["Correct Pick %"] = summary["Correct Pick %"].apply(lambda x: f"{x:.1f}%")
            st.subheader("Summary Table (Concluded Games Only)")
            st.dataframe(
                summary[["User", "Correct Picks", "Total Picks", "Correct Pick %"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("No concluded games available for this week.")
    else:
        st.write("No games available for this week.")


def render_group_data_tab(picks_df):
    """Render the Group Data tab content"""
    st.header("Group Statistics")
    
    # Overall Statistics
    if not picks_df.empty and results_available:
        st.subheader("📊 Overall Pick Trends")
        
        results_df = pd.read_csv(RESULTS_FILE)
        scored_picks = score_all_picks(picks_df, results_df)
        total_picks = scored_picks['result'].isin(['correct', 'incorrect', 'push']).sum()
        
        if total_picks > 0:  # Only show stats if we have concluded games
            # Get spreads for each pick to determine favorite/underdog
            picks_with_spreads = scored_picks.copy()
            picks_with_spreads['is_favorite'] = picks_with_spreads.apply(
                lambda row: (row['spread'] < 0 and row['pick'] in row['game'].split(' @ ')[1]) or 
                            (row['spread'] > 0 and row['pick'] in row['game'].split(' @ ')[0]),
                axis=1
            )
            
            favorites_picked = picks_with_spreads['is_favorite'].sum()
            underdogs_picked = total_picks - favorites_picked
            
            total_correct = (scored_picks['result'] == 'correct').sum()
            favorites_correct = ((scored_picks['result'] == 'correct') & picks_with_spreads['is_favorite']).sum()
            underdogs_correct = ((scored_picks['result'] == 'correct') & ~picks_with_spreads['is_favorite']).sum()
            
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
        
        if not completed_picks.empty:
            # Most commonly picked teams
            st.subheader("📈 Most Picked Teams (Completed Games)")
            team_picks = completed_picks.groupby("pick").size().reset_index(name="count")
            top_teams = team_picks.nlargest(5, "count")
            
            # Get display names and colors for teams
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
            
            # Least commonly picked teams
            st.subheader("📉 Least Picked Teams (Completed Games)")
            bottom_teams = team_picks.nsmallest(5, "count")
            
            # Get display names and colors for bottom teams
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

            # ATS Records (remains unchanged, as this is based on actual results)
            ats_records = pd.DataFrame()
            for team in NFL_TEAM_COLORS.keys():
                games_covered = len(results_df[results_df['covered'] == team])
                total_games = len(results_df[results_df['game'].str.contains(team)])
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
            
            # Get display names and colors for hot teams
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
                    tickformat=".0%",
                    range=[0, 100],
                    title="Cover %"
                ),
                dragmode=False,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Cold teams
            st.subheader("❄️ Worst Teams Against the Spread")
            cold_teams = ats_records.nsmallest(5, 'pct')
            
            # Get display names and colors for cold teams
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
                    tickformat=".0%",
                    range=[0, 100],
                    title="Cover %"
                ),
                dragmode=False,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

def render_leaderboards_tab(picks_df):
    """Render the Leaderboards tab content"""
    st.header("Leaderboards")

    if results_available:
        results_df = pd.read_csv(RESULTS_FILE)
        scored_picks = score_all_picks(picks_df, results_df)
        
        # Weekly leaderboard
        st.subheader("🏆 Weekly Leaderboard")
        weekly = (
            scored_picks.groupby(["week", "user"])["result"]
            .apply(lambda x: (x == "correct").sum())
            .reset_index(name="correct")
        )
        weekly["total"] = scored_picks.groupby(["week", "user"])["result"].count().values
        weekly["correct_pct"] = weekly["correct"] / weekly["total"] * 100
        weekly = add_rank(weekly, ["correct", "correct_pct"])
        st.table(weekly.rename(columns={
            "user": "User",
            "week": "Week",
            "correct": "Correct Picks",
            "correct_pct": "Correct Pick %",
            "Rank": "Rank"
        })[["Rank", "User", "Week", "Correct Picks", "Correct Pick %"]])

        # Season leaderboard
        st.subheader("🏆 Season Total Leaderboard")
        total = (
            scored_picks.groupby("user")["result"]
            .apply(lambda x: (x == "correct").sum())
            .reset_index(name="correct")
        )
        total["total"] = scored_picks.groupby("user")["result"].count().values
        total["correct_pct"] = total["correct"] / total["total"] * 100
        total = add_rank(total, ["correct", "correct_pct"])
        st.table(total.rename(columns={
            "user": "User",
            "correct": "Correct Picks",
            "correct_pct": "Correct Pick %",
            "Rank": "Rank"
        })[["Rank", "User", "Correct Picks", "Correct Pick %"]])
    else:
        st.info("No results available yet.")

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

    # Direct password entry without user selection first
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
    tabs = st.tabs(["Make Picks", "Past Picks", "Group Picks", "Group Data", "Leaderboards"])
    picks_df = load_picks()

    # Render each tab
    with tabs[0]:
        render_make_picks_tab(user, picks_df, nfl_data.get_weekly_spreads(CURRENT_WEEK))
    
    with tabs[1]:
        render_past_picks_tab(picks_df)
    
    with tabs[2]:
        render_group_picks_tab(picks_df)
    
    with tabs[3]:
        render_group_data_tab(picks_df)
    
    with tabs[4]:
        render_leaderboards_tab(picks_df)

def render_demo_mode():
    """Render the demo mode content"""
    st.info("Public demo — view a sample version of the app with pre-filled data.")

    demo_tabs = st.tabs(["Make Picks", "Past Picks", "Group Picks", "Group Data", "Leaderboards"])

    # Load demo data from CSVs
    demo_picks_df = pd.read_csv(Path(DATA_DIR) / "demo_picks.csv")
    demo_results_df = pd.read_csv(Path(DATA_DIR) / "demo_results.csv")

    # For demo, set CURRENT_WEEK to max week in picks
    demo_current_week = demo_picks_df["week"].max()

    # Make Picks Tab (read-only)
    with demo_tabs[0]:
        st.header("Make Picks")
        st.warning("⚠️ Picks cannot be made in demo mode.")
        st.write("Sample picks interface shown below:")

        sample_game = "Carolina Panthers @ New Orleans Saints"
        sample_spread = 1.5
        st.markdown(f"""
        Example Game:
        {format_game_with_spread(sample_game, sample_spread)} 
        """)
        team1, team2 = sample_game.split(" @ ")
        team1_display = TEAM_DISPLAY_NAMES.get(team1, team1)
        team2_display = TEAM_DISPLAY_NAMES.get(team2, team2)
        st.selectbox("Make your pick:", [team1_display, team2_display])

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
                hide_index=True
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
            st.subheader("Summary Table (Concluded Games Only)")
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
        st.subheader("📈 Most Picked Teams (Completed Games)")
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
        st.subheader("📉 Least Picked Teams (Completed Games)")
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
                tickformat=".0%",
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
                tickformat=".0%",
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
                "week": "Week",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "total": "Total Picks",
                "Rank": "Rank"
            })[["Rank", "User", "Week", "Correct Picks", "Total Picks", "Correct Pick %"]],
            use_container_width=True,
            hide_index=True
        )

        # Season leaderboard
        st.subheader("🏆 Season Total Leaderboard")
        total = (
            demo_picks_df.merge(demo_results_df, on=["week", "game"])
            .assign(correct=lambda df: df["pick"] == df["covered"])
            .groupby("user")
            .agg(correct=("correct", "sum"), total=("pick", "count"))
            .reset_index()
        )
        total["correct_pct"] = total["correct"] / total["total"] * 100
        total = add_rank(total, ["correct", "correct_pct"])
        total["correct_pct"] = total["correct_pct"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            total.rename(columns={
                "user": "User",
                "correct": "Correct Picks",
                "correct_pct": "Correct Pick %",
                "total": "Total Picks",
                "Rank": "Rank"
            })[["Rank", "User", "Correct Picks", "Total Picks", "Correct Pick %"]],
            use_container_width=True,
            hide_index=True
        )

if __name__ == "__main__":
    main()