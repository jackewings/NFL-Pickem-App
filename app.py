import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from src import data, scoring, config
import plotly.graph_objects as go

# Add custom theme colors
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

DATA_FILE = Path(config.DATA_FILE)
RESULTS_FILE = Path("data/results.csv")
CURRENT_WEEK = config.CURRENT_WEEK
USERS = ["Gabe", "Jack", "Jake", "Trapp"]

NFL_TEAM_COLORS = {
    "Cardinals": "#97233F",
    "Falcons": "#A71930",
    "Ravens": "#241773",
    "Bills": "#00338D",
    "Panthers": "#0085CA",
    "Bears": "#0B162A",
    "Bengals": "#FB4F14",
    "Browns": "#311D00",
    "Cowboys": "#003594",
    "Broncos": "#FB4F14",
    "Lions": "#0076B6",
    "Packers": "#203731",
    "Texans": "#03202F",
    "Colts": "#002C5F",
    "Jaguars": "#006778",
    "Chiefs": "#E31837",
    "Raiders": "#000000",
    "Chargers": "#0080C6",
    "Rams": "#003594",
    "Dolphins": "#008E97",
    "Vikings": "#4F2683",
    "Patriots": "#002244",
    "Saints": "#D3BC8D",
    "Giants": "#0B2265",
    "Jets": "#125740",
    "Eagles": "#004C54",
    "Steelers": "#FFB612",
    "49ers": "#AA0000",
    "Seahawks": "#002244",
    "Buccaneers": "#D50A0A",
    "Titans": "#0C2340",
    "Commanders": "#773141"
}

def load_picks():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE)
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=["week", "user", "game", "spread", "pick", "timestamp"])
    return pd.DataFrame(columns=["week", "user", "game", "spread", "pick", "timestamp"])

def save_picks(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)

def add_rank(df, sort_cols, rank_col="Rank"):
    if df.empty:
        df[rank_col] = []
        return df
    df = df.sort_values(sort_cols, ascending=[False, False]).reset_index(drop=True)
    df[rank_col] = df.reset_index().index + 1
    return df

def game_has_started(commence_time_str):
    try:
        start_time = datetime.fromisoformat(commence_time_str)
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        return now >= start_time
    except Exception:
        return False

def format_spread(spread):
    """Format spread with proper + sign for positive values"""
    if spread > 0:
        return f"+{spread}"
    return str(spread)

def format_game_with_spread(game, spread):
    """Format game display with spread in consistent format"""
    if "@" in game:
        away_team, home_team = game.split(" @ ")
    else:
        home_team, away_team = game.split(" vs. ")
    
    # Convert to short names if full names are used
    away_team = TEAM_NAME_MAPPING.get(away_team, away_team)
    home_team = TEAM_NAME_MAPPING.get(home_team, home_team)
    
    # For away team display, flip the spread since we're showing from away team perspective
    away_spread = -spread  # Flip the sign for away team perspective
    formatted_spread = format_spread(away_spread)
    
    # Display as "Away (spread) @ Home"
    return f"{away_team} ({formatted_spread}) @ {home_team}"

TEAM_NAME_MAPPING = {
    "Minnesota Vikings": "Vikings",
    "Detroit Lions": "Lions",
    "Green Bay Packers": "Packers",
    "Chicago Bears": "Bears",
    "Dallas Cowboys": "Cowboys",
    "Philadelphia Eagles": "Eagles",
    "New York Giants": "Giants",
    "Washington Commanders": "Commanders",
    "San Francisco 49ers": "49ers",
    "Los Angeles Rams": "Rams",
    "Seattle Seahawks": "Seahawks",
    "Arizona Cardinals": "Cardinals",
    "Tampa Bay Buccaneers": "Buccaneers",
    "New Orleans Saints": "Saints",
    "Carolina Panthers": "Panthers",
    "Atlanta Falcons": "Falcons",
    "New England Patriots": "Patriots",
    "Buffalo Bills": "Bills",
    "Miami Dolphins": "Dolphins",
    "New York Jets": "Jets",
    "Pittsburgh Steelers": "Steelers",
    "Baltimore Ravens": "Ravens",
    "Cleveland Browns": "Browns",
    "Cincinnati Bengals": "Bengals",
    "Kansas City Chiefs": "Chiefs",
    "Las Vegas Raiders": "Raiders",
    "Los Angeles Chargers": "Chargers",
    "Denver Broncos": "Broncos",
    "Tennessee Titans": "Titans",
    "Indianapolis Colts": "Colts",
    "Houston Texans": "Texans",
    "Jacksonville Jaguars": "Jaguars"
}

st.title("🏈 NFL Pick'em Tracker")
st.caption("For entertainment purposes only. Tracks friendly picks, does not involve betting or money.")

# --- Mode selection with session state ---
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

    # Use the value from session state!
    if st.session_state.mode == "Live Mode (Password Required)":
        # User selection and authentication
        if "user" not in st.session_state:
            st.session_state.user = None
        if "user_authenticated" not in st.session_state:
            st.session_state.user_authenticated = False

        if not st.session_state.user:
            user = st.selectbox("Select your name:", USERS)
            if st.button("Next"):
                st.session_state.user = user
                st.rerun()
            st.stop()

        user = st.session_state.user

        if not st.session_state.user_authenticated:
            pw = st.text_input(f"Enter password for {user}:", type="password")
            if st.button("Unlock My Picks"):
                if pw == st.secrets["users"][user]:
                    st.session_state.user_authenticated = True
                    st.rerun()
                else:
                    st.warning("❌ Incorrect password")
                    st.stop()
            st.stop()

        # Only shown after successful authentication
        tabs = st.tabs(["Make Picks", "Past Picks", "Group Picks", "Group Data", "Leaderboards"])
        picks_df = load_picks()
        results_available = RESULTS_FILE.exists() and pd.read_csv(RESULTS_FILE).shape[0] > 0

        with tabs[0]:
            st.header(f"Week {CURRENT_WEEK} Picks — {user}")
            weekly_games = data.get_weekly_spreads(CURRENT_WEEK)

            if weekly_games and len(weekly_games) > 0:
                if "last_updated" in weekly_games[0]:
                    last_updated = datetime.fromisoformat(weekly_games[0]["last_updated"])
                    st.caption(f"Lines last updated: {last_updated.strftime('%Y-%m-%d %I:%M %p CT')}")

            user_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK)]
            session_picks = []
            for g in weekly_games:
                formatted_game = format_game_with_spread(g["game"], g["spread"])
                st.write(formatted_game)
                
                # Extract teams from game string
                teams = g["game"].split(" @ ") if "@" in g["game"] else g["game"].split(" vs. ")

                if "@" in g["game"]:
                    away_team, home_team = g["game"].split(" @ ")
                else:
                    home_team, away_team = g["game"].split(" vs. ")

                teams = [
                    TEAM_NAME_MAPPING.get(away_team, away_team),
                    TEAM_NAME_MAPPING.get(home_team, home_team)
                ]
                
                commence_time_str = g.get("commence_time", None)
                locked = game_has_started(commence_time_str) if commence_time_str else False
                prev_pick = user_picks[user_picks["game"] == g["game"]]["pick"].values
                default = prev_pick[0] if len(prev_pick) else teams[0]
                
                if locked:
                    st.write(f"**{formatted_game}** — Locked (Game Started)")
                    if len(prev_pick):
                        st.write(f"Your pick: {prev_pick[0]}")
                    else:
                        st.write("No pick submitted.")
                else:
                    pick = st.selectbox(
                        "Make your pick:",
                        teams,
                        index=teams.index(default) if default in teams else 0,
                        key=f"{g['game']}_{user}"
                    )
                    session_picks.append({
                        "week": CURRENT_WEEK,
                        "user": user,
                        "game": g["game"],
                        "spread": g["spread"],
                        "pick": pick,
                        "timestamp": datetime.now().isoformat(timespec="seconds")
                    })

            # Submit and Reset buttons side by side
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Submit Picks"):
                    unlocked_games = [g["game"] for g in weekly_games if not game_has_started(g.get("commence_time", ""))]
                    picks_df = picks_df[~((picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK) & (picks_df["game"].isin(unlocked_games)))]
                    if session_picks:
                        picks_df = pd.concat([picks_df, pd.DataFrame(session_picks)], ignore_index=True)
                        save_picks(picks_df)
                        st.success("Picks submitted!")

            with col2:
                if st.button("Reset Picks"):
                    st.session_state.show_reset_confirm = True

            # Reset confirmation
            if st.session_state.get("show_reset_confirm", False):
                st.warning("⚠️ Are you sure you want to reset all your picks for this week? This cannot be undone.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, Reset"):
                        unlocked_games = [g["game"] for g in weekly_games if not game_has_started(g.get("commence_time", ""))]
                        picks_df = picks_df[~((picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK) & (picks_df["game"].isin(unlocked_games)))]
                        save_picks(picks_df)
                        st.session_state.show_reset_confirm = False
                        st.success("Picks reset!")
                        st.rerun()
                with col2:
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
                # Convert pick to short name
                current_picks_display["pick"] = current_picks_display["pick"].map(lambda x: TEAM_NAME_MAPPING.get(x, x))
                
                st.table(
                    current_picks_display[["formatted_game", "pick"]].rename(columns={
                        "formatted_game": "Game",
                        "pick": "Pick"
                    })
                )
            else:
                st.write("No picks submitted yet.")

        with tabs[1]:
            st.header("Past Picks")
            
            # Filter controls - only show weeks prior to current week
            col1, col2 = st.columns(2)
            with col1:
                available_weeks = sorted([w for w in picks_df["week"].unique() if w < CURRENT_WEEK]) if not picks_df.empty else []
                if available_weeks:
                    selected_week = st.selectbox("Select Week:", available_weeks)
                else:
                    st.write("No past weeks available yet.")
                    selected_week = None
            
            with col2:
                if available_weeks:
                    available_users = sorted(picks_df["user"].unique()) if not picks_df.empty else USERS
                    selected_user = st.selectbox("Select User:", available_users, index=available_users.index(user) if user in available_users else 0)

            # Show filtered picks for past weeks only
            if selected_week and not picks_df.empty:
                filtered_picks = picks_df[(picks_df["week"] == selected_week) & (picks_df["user"] == selected_user)]
                if not filtered_picks.empty:
                    # Format spreads with + for positive values
                    filtered_picks_display = filtered_picks.copy()
                    filtered_picks_display["formatted_game"] = filtered_picks_display.apply(
                        lambda row: format_game_with_spread(row["game"], row["spread"]), 
                        axis=1
                  )
                    st.dataframe(
                        filtered_picks_display[["formatted_game", "pick"]].rename(columns={
                            "formatted_game": "Game",
                            "pick": "Pick"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.write(f"No picks found for {selected_user} in Week {selected_week}.")

        with tabs[2]:
            st.header("Group Picks")
            st.write("View everyone's picks for games that have already started.")
            
            # Get current week games and their start status
            weekly_games = data.get_weekly_spreads(CURRENT_WEEK)
            current_week_picks = picks_df[picks_df["week"] == CURRENT_WEEK]
            
            if weekly_games:
                for g in weekly_games:
                    commence_time_str = g.get("commence_time", None)
                    game_started = game_has_started(commence_time_str) if commence_time_str else False
                    
                    if game_started:
                        # Format the game title with spreads
                        formatted_game = format_game_with_spread(g["game"], g["spread"])
                        st.write(f"• {formatted_game}")
                        
                        # Get all picks for this game
                        game_picks = current_week_picks[current_week_picks["game"] == g["game"]]
                        
                        if not game_picks.empty:
                            # Format the display nicely
                            game_picks_display = game_picks[["user", "pick"]].copy()
                            game_picks_display = game_picks_display.sort_values("user")
                            
                            # Display as a nice table
                            st.dataframe(
                                game_picks_display.rename(columns={
                                    "user": "User", 
                                    "pick": "Pick"
                                }),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.write("No picks submitted for this game.")
                        
                        st.write("---")  # Separator between games
                
                # Show upcoming games (not started yet)
                upcoming_games = [g for g in weekly_games if not game_has_started(g.get("commence_time", ""))]
                if upcoming_games:
                    st.subheader("🔒 Upcoming Games")
                    st.write("Picks will be revealed when these games start:")
                    for g in upcoming_games:
                        formatted_game = format_game_with_spread(g["game"], g["spread"])
                        st.write(f"• {formatted_game}")
            else:
                st.write("No games available for this week.")

        with tabs[3]:
            st.header("Group Statistics")
            
            # Overall Statistics
            if not picks_df.empty and results_available:
                st.subheader("📊 Overall Picking Trends")
                
                results_df = pd.read_csv(RESULTS_FILE)
                # Only include picks that have results
                merged_picks = picks_df.merge(results_df, on=['week', 'game'])
                total_picks = len(merged_picks)
                
                if total_picks > 0:  # Only show stats if we have concluded games
                    # Get spreads for each pick to determine favorite/underdog
                    picks_with_spreads = merged_picks.copy()
                    picks_with_spreads['is_favorite'] = picks_with_spreads.apply(
                        lambda row: (row['spread'] < 0 and row['pick'] in row['game'].split(' @ ')[1]) or 
                                  (row['spread'] > 0 and row['pick'] in row['game'].split(' @ ')[0]),
                        axis=1
                    )
                    
                    favorites_picked = picks_with_spreads['is_favorite'].sum()
                    underdogs_picked = total_picks - favorites_picked
                    
                    total_correct = (merged_picks['pick'] == merged_picks['covered']).sum()
                    favorites_correct = ((merged_picks['pick'] == merged_picks['covered']) & 
                                      picks_with_spreads['is_favorite']).sum()
                    underdogs_correct = ((merged_picks['pick'] == merged_picks['covered']) & 
                                       ~picks_with_spreads['is_favorite']).sum()
                    
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
                            f"{(favorites_correct/favorites_picked*100):.1f}%",
                            f"{(underdogs_correct/underdogs_picked*100):.1f}%",
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
                
                st.markdown("---")
            
            # Update the team charts to only use completed games
            if results_available:
                results_df = pd.read_csv(RESULTS_FILE)
                completed_picks = picks_df.merge(results_df, on=['week', 'game'])
                
                if not completed_picks.empty:
                    # Most commonly picked teams
                    st.subheader("📈 Most Picked Teams (Completed Games)")
                    team_picks = completed_picks.groupby("pick").size().reset_index(name="count")
                    top_teams = team_picks.nlargest(5, "count")
                    fig = go.Figure(data=[
                        go.Bar(
                            x=top_teams["pick"],
                            y=top_teams["count"],
                            marker_color=[NFL_TEAM_COLORS.get(team, "#808080") for team in top_teams["pick"]],
                            text=top_teams["count"],
                            textposition='auto',
                        )
                    ])
                    fig.update_layout(
                    yaxis=dict(
                        tickformat="d",  # Use whole numbers
                        dtick=1,  # Force tick interval of 1
                        tick0=0,  # Start ticks at 0
                        showgrid=True  # Show gridlines
                    ),
                    showlegend=False,
                    yaxis_title="Times Picked",
                    dragmode=False
                )
                    st.plotly_chart(fig, use_container_width=True, key="most_picked")
                    
                    # Least commonly picked teams
                    st.subheader("📉 Least Picked Teams (Completed Games)")
                    bottom_teams = team_picks.nsmallest(5, "count")
                    fig = go.Figure(data=[
                        go.Bar(
                            x=bottom_teams["pick"],
                            y=bottom_teams["count"],
                            marker_color=[NFL_TEAM_COLORS.get(team, "#808080") for team in bottom_teams["pick"]],
                            text=bottom_teams["count"],
                            textposition='auto',
                        )
                    ])
                    fig.update_layout(
                    yaxis=dict(
                        tickformat="d",  # Use whole numbers
                        dtick=1,  # Force tick interval of 1
                        tick0=0,  # Start ticks at 0
                        showgrid=True  # Show gridlines
                    ),
                    showlegend=False,
                    yaxis_title="Times Picked",
                    dragmode=False
                )
                    st.plotly_chart(fig, use_container_width=True, key="least_picked")

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
                    fig = go.Figure(data=[
                        go.Bar(
                            x=hot_teams["team"],
                            y=hot_teams["pct"].multiply(100),
                            marker_color=[NFL_TEAM_COLORS.get(team, "#808080") for team in hot_teams["team"]],
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
                    fig = go.Figure(data=[
                        go.Bar(
                            x=cold_teams["team"],
                            y=cold_teams["pct"].multiply(100),
                            marker_color=[NFL_TEAM_COLORS.get(team, "#808080") for team in cold_teams["team"]],
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

        with tabs[4]:
            st.header("Leaderboards")
            
            # Always show weekly leaderboard structure
            st.subheader("🏆 Weekly Leaderboard")
            empty_weekly = pd.DataFrame(columns=["Rank", "User", "Week", "Correct Picks", "Correct Pick %"])
            st.table(empty_weekly)
            
            # Always show season total structure
            st.subheader("🏆 Season Total Leaderboard")
            empty_total = pd.DataFrame(columns=["Rank", "User", "Correct Picks", "Correct Pick %", "Best Team"])
            st.table(empty_total)
            
            if results_available:
                # Your existing leaderboard code here
                results_df = pd.read_csv(RESULTS_FILE)
                scores = scoring.calculate_scores(picks_df, results_df)
                
                # Handle weekly leaderboard
                weekly = scores["weekly"]
                if not weekly.empty:
                    week_options = sorted(weekly["week"].unique())
                    selected_week = st.selectbox("Filter weekly leaderboard by week:", week_options)
                    
                    weekly_filtered = weekly[weekly["week"] == selected_week] if selected_week else weekly
                    weekly_ranked = add_rank(weekly_filtered, ["correct", "correct_pct"])
                    
                    st.subheader("🏆 Weekly Leaderboard")
                    st.table(
                        weekly_ranked.rename(columns={
                            "user": "User",
                            "week": "Week",
                            "correct": "Correct Picks",
                            "correct_pct": "Correct Pick %",
                            "Rank": "Rank"
                        })[["Rank", "User", "Week", "Correct Picks", "Correct Pick %"]]
                    )
                
                # Handle total leaderboard
                total = scores["total"]
                if not total.empty:
                    total_ranked = add_rank(total, ["correct", "correct_pct"])
                    
                    if "best_team" not in total_ranked.columns:
                        total_ranked["best_team"] = "N/A"
                    
                    st.subheader("🏆 Season Total Leaderboard")
                    st.table(
                        total_ranked.sort_values("Rank").rename(columns={
                            "user": "User",
                            "correct": "Correct Picks",
                            "correct_pct": "Correct Pick %",
                            "best_team": "Best Team",
                            "Rank": "Rank"
                        })[["Rank", "User", "Correct Picks", "Correct Pick %", "Best Team"]]
                    )

    else:
        # Demo mode
        st.info("Public demo — view a sample version of the app with pre-filled data.")
        demo_tabs = st.tabs(["Make Picks", "Past Picks", "Group Picks", "Group Data", "Leaderboards"])
        demo_picks = [
            # Week 1
            {"week": 1, "user": "Jack", "game": "Vikings @ Bears", "spread": 3.0, "pick": "Bears", "timestamp": "2025-08-01 12:00"},
            {"week": 1, "user": "Louis", "game": "Vikings @ Bears", "spread": 3.0, "pick": "Vikings", "timestamp": "2025-08-01 12:01"},
            {"week": 1, "user": "Miles", "game": "Vikings @ Bears", "spread": 3.0, "pick": "Vikings", "timestamp": "2025-08-01 12:02"},
            {"week": 1, "user": "Jack", "game": "Patriots @ Jets", "spread": 1.5, "pick": "Jets", "timestamp": "2025-08-01 12:03"},
            {"week": 1, "user": "Louis", "game": "Patriots @ Jets", "spread": 1.5, "pick": "Jets", "timestamp": "2025-08-01 12:04"},
            {"week": 1, "user": "Miles", "game": "Patriots @ Jets", "spread": 1.5, "pick": "Patriots", "timestamp": "2025-08-01 12:05"},
            # Week 2
            {"week": 2, "user": "Jack", "game": "Giants @ Cowboys", "spread": -4.0, "pick": "Giants", "timestamp": "2025-08-08 12:00"},
            {"week": 2, "user": "Louis", "game": "Giants @ Cowboys", "spread": -4.0, "pick": "Giants", "timestamp": "2025-08-08 12:01"},
            {"week": 2, "user": "Miles", "game": "Giants @ Cowboys", "spread": -4.0, "pick": "Cowboys", "timestamp": "2025-08-08 12:02"},
            {"week": 2, "user": "Jack", "game": "Eagles @ Commanders", "spread": +2.5, "pick": "Commanders", "timestamp": "2025-08-08 12:03"},
            {"week": 2, "user": "Louis", "game": "Eagles @ Commanders", "spread": +2.5, "pick": "Eagles", "timestamp": "2025-08-08 12:04"},
            {"week": 2, "user": "Miles", "game": "Eagles @ Commanders", "spread": +2.5, "pick": "Eagles", "timestamp": "2025-08-08 12:05"},
            # Week 3
            {"week": 3, "user": "Jack", "game": "Rams @ Vikings", "spread": -3.5, "pick": "Rams", "timestamp": "2025-08-15 12:00"},
            {"week": 3, "user": "Louis", "game": "Rams @ Vikings", "spread": -3.5, "pick": "Vikings", "timestamp": "2025-08-15 12:01"},
            {"week": 3, "user": "Miles", "game": "Rams @ Vikings", "spread": -3.5, "pick": "Rams", "timestamp": "2025-08-15 12:02"},
            {"week": 3, "user": "Jack", "game": "Seahawks @ Cardinals", "spread": 1.5, "pick": "Cardinals", "timestamp": "2025-08-15 12:03"},
            {"week": 3, "user": "Louis", "game": "Seahawks @ Cardinals", "spread": 1.5, "pick": "Seahawks", "timestamp": "2025-08-15 12:04"},
            {"week": 3, "user": "Miles", "game": "Seahawks @ Cardinals", "spread": 1.5, "pick": "Cardinals", "timestamp": "2025-08-15 12:05"},
        ]
        demo_results = [
            {"week": 1, "game": "Vikings @ Bears", "covered": "Vikings"},
            {"week": 1, "game": "Patriots @ Jets", "covered": "Jets"},
            {"week": 2, "game": "Giants @ Cowboys", "covered": "Cowboys"},
            {"week": 2, "game": "Eagles @ Commanders", "covered": "Eagles"},
            {"week": 3, "game": "Rams @ Vikings", "covered": "Vikings"},
            {"week": 3, "game": "Seahawks @ Cardinals", "covered": "Seahawks"},
        ]
        demo_df = pd.DataFrame(demo_picks)
        demo_results_df = pd.DataFrame(demo_results)

        with demo_tabs[0]:
            st.header("Make Picks")
            st.warning("⚠️ Picks cannot be made in demo mode.")
            st.write("Sample picks interface shown below:")
            st.markdown(f"""
            Example Game:
            {format_game_with_spread("Vikings @ Bears", -3.0)}
            """)
            st.selectbox("Make your pick:", ["Vikings", "Bears"], index=1)
        
        # Past Picks Tab
        with demo_tabs[1]:
            st.header("Past Picks")
            col1, col2 = st.columns(2)
            with col1:
                week_options = sorted(demo_df["week"].unique())
                selected_week = st.selectbox("Select Week (Demo):", week_options)
            with col2:
                user_options = sorted(demo_df["user"].unique())
                selected_user = st.selectbox("Select User (Demo):", user_options)
            
            filtered_picks = demo_df[
                (demo_df["week"] == selected_week) & 
                (demo_df["user"] == selected_user)
            ]
            
            if not filtered_picks.empty:
                # Merge with results
                filtered_picks_with_results = filtered_picks.merge(
                    demo_results_df,
                    on=['week', 'game'],
                    how='left'
                )
                
                # Create display DataFrame
                display_df = filtered_picks_with_results.copy()
                display_df["formatted_game"] = display_df.apply(
                    lambda row: format_game_with_spread(row["game"], row["spread"]), 
                    axis=1
                )
                display_df = display_df[["formatted_game", "pick", "covered"]].rename(columns={
                    "formatted_game": "Game",
                    "pick": "Selection",
                    "covered": "Covered"
                })
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
        
        # Group Picks Tab
        with demo_tabs[2]:
            st.header("Group Picks")
            # Show sample completed game
            st.subheader("📊 Sample Completed Game")
            st.write(format_game_with_spread("Vikings @ Bears", -3.0))
            sample_picks = demo_df[demo_df["game"] == "Vikings @ Bears"]
            if not sample_picks.empty:
                st.dataframe(
                    sample_picks[["user", "pick"]].rename(columns={
                        "user": "User",
                        "pick": "Pick"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
        
        # Group Data Tab
        with demo_tabs[3]:
            st.header("Group Statistics")
            st.subheader("📊 Overall Picking Trends")
            
            # Calculate demo statistics
            demo_merged = demo_df.merge(demo_results_df, on=['week', 'game'])
            total_picks = len(demo_merged)
            
            if total_picks > 0:
                # Calculate favorite/underdog stats
                picks_with_spreads = demo_merged.copy()
                picks_with_spreads['is_favorite'] = picks_with_spreads.apply(
                    lambda row: (row['spread'] < 0 and row['pick'] in row['game'].split(' @ ')[1]) or 
                              (row['spread'] > 0 and row['pick'] in row['game'].split(' @ ')[0]),
                    axis=1
                )
                
                favorites_picked = picks_with_spreads['is_favorite'].sum()
                underdogs_picked = total_picks - favorites_picked
                total_correct = (demo_merged['pick'] == demo_merged['covered']).sum()
                favorites_correct = ((demo_merged['pick'] == demo_merged['covered']) & 
                                  picks_with_spreads['is_favorite']).sum()
                underdogs_correct = ((demo_merged['pick'] == demo_merged['covered']) & 
                                   ~picks_with_spreads['is_favorite']).sum()
                
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
                        f"{(favorites_correct/favorites_picked*100):.1f}%",
                        f"{(underdogs_correct/underdogs_picked*100):.1f}%",
                        f"{(favorites_picked/total_picks*100):.1f}%",
                        f"{(underdogs_picked/total_picks*100):.1f}%"
                    ]
                }
                st.dataframe(
                    pd.DataFrame(stats_data),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Add sample charts
                st.subheader("📈 Most Picked Teams")
                team_picks = demo_df.groupby("pick").size().reset_index(name="count")
                top_teams = team_picks.nlargest(5, "count")
                
                # Debug print to check team names
                print("Team names in picks:", top_teams["pick"].tolist())
                print("Available colors:", list(NFL_TEAM_COLORS.keys()))
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=top_teams["pick"],
                        y=top_teams["count"],
                        marker_color=[NFL_TEAM_COLORS[team] if team in NFL_TEAM_COLORS else "#808080" for team in top_teams["pick"]],
                        text=top_teams["count"],
                        textposition='auto',
                    )
                ])
                fig.update_layout(
                    yaxis=dict(
                        tickformat="d",  # Use whole numbers
                        dtick=1,  # Force tick interval of 1
                        tick0=0,  # Start ticks at 0
                        showgrid=True  # Show gridlines
                    ),
                    showlegend=False,
                    yaxis_title="Times Picked",
                    dragmode=False
                )
                st.plotly_chart(fig, use_container_width=True, key="demo_most_picked")
        
        # Leaderboards Tab (your existing demo leaderboard code)
        with demo_tabs[4]:
            demo_scores = scoring.calculate_scores(demo_df, demo_results_df)
            demo_weekly = demo_scores["weekly"]
            demo_total = demo_scores["total"]
            week_options = sorted(demo_weekly["week"].unique()) if not demo_weekly.empty else []
            selected_week = st.selectbox("Filter weekly leaderboard by week (Demo):", week_options) if week_options else None
            if selected_week:
                demo_weekly_filtered = demo_weekly[demo_weekly["week"] == selected_week]
            else:
                demo_weekly_filtered = demo_weekly
            demo_weekly_ranked = add_rank(demo_weekly_filtered, ["correct", "correct_pct"])
            demo_total_ranked = add_rank(demo_total, ["correct", "correct_pct"])
            st.subheader("🏆 Weekly Leaderboard")
            st.dataframe(
                demo_weekly_ranked.rename(columns={
                    "user": "User",
                    "week": "Week",
                    "correct": "Correct Picks",
                    "correct_pct": "Correct Pick %",
                    "Rank": "Rank"
                })[["Rank", "User", "Week", "Correct Picks", "Correct Pick %"]],
                use_container_width=True,
                hide_index=True
            )
            st.subheader("🏆 Season Total Leaderboard")
            demo_total_ranked = demo_total_ranked.sort_values("Rank")
            if "best_team" not in demo_total_ranked.columns:
                demo_total_ranked["best_team"] = "N/A"
            st.dataframe(
                demo_total_ranked.rename(columns={
                    "user": "User",
                    "correct": "Correct Picks",
                    "correct_pct": "Correct Pick %",
                    "best_team": "Best Team",
                    "Rank": "Rank"
                })[["Rank", "User", "Correct Picks", "Correct Pick %", "Best Team"]],
                use_container_width=True,
                hide_index=True
            )
