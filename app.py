import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from src import data, scoring, config

DATA_FILE = Path(config.DATA_FILE)
RESULTS_FILE = Path("data/results.csv")
CURRENT_WEEK = config.CURRENT_WEEK
PASSWORD = st.secrets["app_password"]
USERS = ["Gabe", "Jack", "Jake", "Trapp"]

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

st.title("🏈 NFL Pick'em Tracker (ATS)")
st.caption("For entertainment purposes only. Tracks friendly picks, does not involve betting or money.")

# --- Mode selection with session state ---
if "mode" not in st.session_state:
    st.session_state.mode = None

if st.session_state.mode is None:
    mode = st.radio("Choose mode:", ["Public Demo", "Live Mode (Password Required)"])
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
        tabs = st.tabs(["Make Picks", "Past Picks", "Group Picks", "Leaderboards"])
        picks_df = load_picks()
        results_available = RESULTS_FILE.exists() and pd.read_csv(RESULTS_FILE).shape[0] > 0

        with tabs[0]:
            st.header(f"Week {CURRENT_WEEK} Picks — {user}")
            weekly_games = data.get_weekly_spreads(CURRENT_WEEK)
            user_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK)]
            session_picks = []
            for g in weekly_games:
                if "@" in g["game"]:
                    away_team, home_team = g["game"].split(" @ ")
                else:
                    home_team, away_team = g["game"].split(" vs. ")
                
                teams = [home_team, away_team]
                spread = g["spread"]
                
                # Format spread with proper +/- signs
                if spread > 0:
                    home_spread_text = f"(+{spread})"
                    away_spread_text = f"(-{spread})"
                else:
                    home_spread_text = f"({spread})"  # Already has negative sign
                    away_spread_text = f"(+{abs(spread)})"
                
                # Create formatted game display
                formatted_game = f"{away_team} {away_spread_text} @ {home_team} {home_spread_text}"
                
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
                        formatted_game,
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
                # Format spreads with + for positive values
                current_picks_display = current_picks.copy()
                current_picks_display["spread"] = current_picks_display["spread"].apply(format_spread)
                st.table(
                    current_picks_display[["game", "spread", "pick"]].rename(columns={
                        "game": "Game",
                        "spread": "Spread", 
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
                    filtered_picks_display["spread"] = filtered_picks_display["spread"].apply(format_spread)
                    st.dataframe(
                        filtered_picks_display[["game", "spread", "pick"]].rename(columns={
                            "game": "Game",
                            "spread": "Spread",
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
                        if "@" in g["game"]:
                            away_team, home_team = g["game"].split(" @ ")
                        else:
                            home_team, away_team = g["game"].split(" vs. ")
                        
                        spread = g["spread"]
                        
                        # Format spread with proper +/- signs
                        if spread > 0:
                            home_spread_text = f"(+{spread})"
                            away_spread_text = f"(-{spread})"
                        else:
                            home_spread_text = f"({spread})"  # Already has negative sign
                            away_spread_text = f"(+{abs(spread)})"
                        
                        # Create formatted game display
                        formatted_game = f"{away_team} {away_spread_text} @ {home_team} {home_spread_text}"
                        
                        st.subheader(f"📊 {formatted_game}")
                        
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
                        # Format upcoming games with spreads too
                        if "@" in g["game"]:
                            away_team, home_team = g["game"].split(" @ ")
                        else:
                            home_team, away_team = g["game"].split(" vs. ")
                        
                        spread = g["spread"]
                        
                        # Format spread with proper +/- signs
                        if spread > 0:
                            home_spread_text = f"(+{spread})"
                            away_spread_text = f"(-{spread})"
                        else:
                            home_spread_text = f"({spread})"  # Already has negative sign
                            away_spread_text = f"(+{abs(spread)})"
                        
                        # Create formatted game display
                        formatted_upcoming_game = f"{away_team} {away_spread_text} @ {home_team} {home_spread_text}"
                        st.write(f"• {formatted_upcoming_game}")
            else:
                st.write("No games available for this week.")

        with tabs[3]:
            st.header("Leaderboards")
            if not results_available:
                st.info("Leaderboards will be available after results are entered.")
            else:
                results_df = pd.read_csv(RESULTS_FILE)
                scores = scoring.calculate_scores(picks_df, results_df)
                weekly = scores["weekly"]
                total = scores["total"]
                week_options = sorted(weekly["week"].unique()) if not weekly.empty else []
                selected_week = st.selectbox("Filter weekly leaderboard by week:", week_options) if week_options else None
                if selected_week:
                    weekly_filtered = weekly[weekly["week"] == selected_week]
                else:
                    weekly_filtered = weekly
                weekly_ranked = add_rank(weekly_filtered, ["correct", "correct_pct"])
                total_ranked = add_rank(total, ["correct", "correct_pct"])
                st.subheader("🏆 Weekly Leaderboard")
                st.dataframe(
                    weekly_ranked.rename(columns={
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
                total_ranked = total_ranked.sort_values("Rank")
                if "best_team" not in total_ranked.columns:
                    total_ranked["best_team"] = "N/A"
                st.dataframe(
                    total_ranked.rename(columns={
                        "user": "User",
                        "correct": "Correct Picks",
                        "correct_pct": "Correct Pick %",
                        "best_team": "Best Team",
                        "Rank": "Rank"
                    })[["Rank", "User", "Correct Picks", "Correct Pick %", "Best Team"]],
                    use_container_width=True,
                    hide_index=True
                )

    else:
        # Demo mode
        st.info("Public demo — view a sample leaderboard. No picks can be made in demo mode.")
        demo_tabs = st.tabs(["Demo Leaderboard"])
        with demo_tabs[0]:
            demo_picks = [
                # Week 1
                {"week": 1, "user": "Jack", "game": "Vikings @ Bears", "spread": -3.0, "pick": "Bears", "timestamp": "2025-08-01 12:00"},
                {"week": 1, "user": "Louis", "game": "Vikings @ Bears", "spread": -3.0, "pick": "Vikings", "timestamp": "2025-08-01 12:01"},
                {"week": 1, "user": "Miles", "game": "Vikings @ Bears", "spread": -3.0, "pick": "Vikings", "timestamp": "2025-08-01 12:02"},
                {"week": 1, "user": "Jack", "game": "Patriots @ Jets", "spread": +7.0, "pick": "Jets", "timestamp": "2025-08-01 12:03"},
                {"week": 1, "user": "Louis", "game": "Patriots @ Jets", "spread": +7.0, "pick": "Jets", "timestamp": "2025-08-01 12:04"},
                {"week": 1, "user": "Miles", "game": "Patriots @ Jets", "spread": +7.0, "pick": "Patriots", "timestamp": "2025-08-01 12:05"},
                # Week 2
                {"week": 2, "user": "Jack", "game": "Giants @ Cowboys", "spread": -4.0, "pick": "Giants", "timestamp": "2025-08-08 12:00"},
                {"week": 2, "user": "Louis", "game": "Giants @ Cowboys", "spread": -4.0, "pick": "Giants", "timestamp": "2025-08-08 12:01"},
                {"week": 2, "user": "Miles", "game": "Giants @ Cowboys", "spread": -4.0, "pick": "Cowboys", "timestamp": "2025-08-08 12:02"},
                {"week": 2, "user": "Jack", "game": "Eagles @ Commanders", "spread": +2.5, "pick": "Commanders", "timestamp": "2025-08-08 12:03"},
                {"week": 2, "user": "Louis", "game": "Eagles @ Commanders", "spread": +2.5, "pick": "Eagles", "timestamp": "2025-08-08 12:04"},
                {"week": 2, "user": "Miles", "game": "Eagles @ Commanders", "spread": +2.5, "pick": "Eagles", "timestamp": "2025-08-08 12:05"},
                # Week 3
                {"week": 3, "user": "Jack", "game": "Rams @ 49ers", "spread": -6.0, "pick": "Rams", "timestamp": "2025-08-15 12:00"},
                {"week": 3, "user": "Louis", "game": "Rams @ Vikings", "spread": -6.0, "pick": "Vikings", "timestamp": "2025-08-15 12:01"},
                {"week": 3, "user": "Miles", "game": "Rams @ 49ers", "spread": -6.0, "pick": "Rams", "timestamp": "2025-08-15 12:02"},
                {"week": 3, "user": "Jack", "game": "Seahawks @ Cardinals", "spread": +1.5, "pick": "Cardinals", "timestamp": "2025-08-15 12:03"},
                {"week": 3, "user": "Louis", "game": "Seahawks @ Cardinals", "spread": +1.5, "pick": "Seahawks", "timestamp": "2025-08-15 12:04"},
                {"week": 3, "user": "Miles", "game": "Seahawks @ Cardinals", "spread": +1.5, "pick": "Cardinals", "timestamp": "2025-08-15 12:05"},
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
            st.subheader("🏆 Weekly Leaderboard (Demo)")
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
            st.subheader("🏆 Season Total Leaderboard (Demo)")
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
