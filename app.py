import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from src import data, scoring, config
import json

DATA_FILE = Path(config.DATA_FILE)
RESULTS_FILE = Path("data/results.csv")
CURRENT_WEEK = config.CURRENT_WEEK
PASSWORD = st.secrets.get("app_password", config.PASSWORD)

USERS = ["Jack", "Trapp", "Gabe", "Jake"]

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

st.title("🏈 NFL Pick’em Tracker (ATS)")
st.caption("For entertainment only — tracks friendly picks, does not place bets or handle money.")

mode = st.radio("Choose mode:", ["Public Demo", "Live Mode (Password Required)"])

if mode == "Live Mode (Password Required)":
    pw = st.text_input("Enter password:", type="password")
    if pw != PASSWORD:
        st.warning("❌ Incorrect password")
        st.stop()
    st.success("✅ Live mode unlocked")

    user = st.selectbox("Select your name:", USERS)
    section = st.radio("Choose section:", ["Make Picks", "Leaderboards"])

    picks_df = load_picks()

    results_available = RESULTS_FILE.exists() and pd.read_csv(RESULTS_FILE).shape[0] > 0

    if section == "Make Picks":
        st.header(f"Week {CURRENT_WEEK} Picks — {user}")

        weekly_games = data.get_weekly_spreads(CURRENT_WEEK)
        user_picks = picks_df[(picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK)]

        session_picks = []
        for g in weekly_games:
            # Parse teams
            if "@" in g["game"]:
                away_team, home_team = g["game"].split(" @ ")
            else:
                home_team, away_team = g["game"].split(" vs. ")
            teams = [home_team, away_team]

            # Game lock logic
            commence_time_str = g.get("commence_time", None)
            locked = game_has_started(commence_time_str) if commence_time_str else False

            prev_pick = user_picks[user_picks["game"] == g["game"]]["pick"].values
            default = prev_pick[0] if len(prev_pick) else teams[0]

            if locked:
                st.write(f"**{g['game']} (Spread: {g['spread']})** — Locked (Game Started)")
                if len(prev_pick):
                    st.write(f"Your pick: {prev_pick[0]}")
                else:
                    st.write("No pick submitted.")
            else:
                pick = st.selectbox(
                    f"{g['game']} (Spread: {g['spread']})",
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

        if st.button("Submit Picks"):
            unlocked_games = [g["game"] for g in weekly_games if not game_has_started(g.get("commence_time", ""))]
            picks_df = picks_df[~((picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK) & (picks_df["game"].isin(unlocked_games)))]
            if session_picks:
                picks_df = pd.concat([picks_df, pd.DataFrame(session_picks)], ignore_index=True)
                save_picks(picks_df)
                st.success("Picks submitted!")

        st.subheader("Your Picks This Week")
        st.dataframe(
            picks_df[(picks_df["user"] == user) & (picks_df["week"] == CURRENT_WEEK)][["game", "spread", "pick"]],
            use_container_width=True
        )

        st.subheader("All Picks (Games Started)")
        started_games = [g["game"] for g in weekly_games if game_has_started(g.get("commence_time", ""))]
        if started_games:
            st.dataframe(
                picks_df[(picks_df["week"] == CURRENT_WEEK) & (picks_df["game"].isin(started_games))][["user", "game", "pick"]],
                use_container_width=True
            )
        else:
            st.write("No games have started yet.")

    elif section == "Leaderboards":
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
                use_container_width=True
            )

            st.subheader("🏆 Season Total Leaderboard")
            total_ranked = total_ranked.sort_values("Rank")
            st.dataframe(
                total_ranked.rename(columns={
                    "user": "User",
                    "correct": "Correct Picks",
                    "correct_pct": "Correct Pick %",
                    "favorite_team": "Favorite Team",
                    "Rank": "Rank"
                })[["Rank", "User", "Correct Picks", "Correct Pick %", "Favorite Team"]],
                use_container_width=True
            )

else:
    st.info("Public demo — view a sample leaderboard. No picks can be made in demo mode.")

    # Demo data: 3 users, 3 weeks, 2 games per week
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
        {"week": 3, "user": "Louis", "game": "Rams @ 49ers", "spread": -6.0, "pick": "49ers", "timestamp": "2025-08-15 12:01"},
        {"week": 3, "user": "Miles", "game": "Rams @ 49ers", "spread": -6.0, "pick": "Rams", "timestamp": "2025-08-15 12:02"},
        {"week": 3, "user": "Jack", "game": "Seahawks @ Cardinals", "spread": +1.5, "pick": "Cardinals", "timestamp": "2025-08-15 12:03"},
        {"week": 3, "user": "Louis", "game": "Seahawks @ Cardinals", "spread": +1.5, "pick": "Seahawks", "timestamp": "2025-08-15 12:04"},
        {"week": 3, "user": "Miles", "game": "Seahawks @ Cardinals", "spread": +1.5, "pick": "Cardinals", "timestamp": "2025-08-15 12:05"},
    ]

    demo_results = [
        # Week 1
        {"week": 1, "game": "Packers @ Bears", "covered": "Vikings"},
        {"week": 1, "game": "Patriots @ Jets", "covered": "Jets"},
        # Week 2
        {"week": 2, "game": "Giants @ Cowboys", "covered": "Cowboys"},
        {"week": 2, "game": "Eagles @ Commanders", "covered": "Eagles"},
        # Week 3
        {"week": 3, "game": "Rams @ 49ers", "covered": "49ers"},
        {"week": 3, "game": "Seahawks @ Cardinals", "covered": "Seahawks"},
    ]

    demo_df = pd.DataFrame(demo_picks)
    demo_results_df = pd.DataFrame(demo_results)

    # --- Filtering ---
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
        use_container_width=True
    )

    st.subheader("🏆 Season Total Leaderboard (Demo)")
    demo_total_ranked = demo_total_ranked.sort_values("Rank")
    st.dataframe(
        demo_total_ranked.rename(columns={
            "user": "User",
            "correct": "Correct Picks",
            "correct_pct": "Correct Pick %",
            "favorite_team": "Favorite Team",
            "Rank": "Rank"
        })[["Rank", "User", "Correct Picks", "Correct Pick %", "Favorite Team"]],
        use_container_width=True
    )
