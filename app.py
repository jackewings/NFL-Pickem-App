import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ---------------------------
# Setup
# ---------------------------
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "picks.csv"

CURRENT_WEEK = 1
PASSWORD = st.secrets.get("app_password", "demo123")  # set real secret later in Streamlit Cloud

# Demo games (we’ll replace with real data later)
demo_games = [
    {"Game": "Packers @ Bears", "Spread": -3.0},
    {"Game": "Patriots @ Jets", "Spread": +7.0},
]

# ---------------------------
# Helpers
# ---------------------------
def load_picks():
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Week", "User", "Game", "Spread", "Pick", "Timestamp"])

def save_picks(df):
    df.to_csv(DATA_FILE, index=False)

def leaderboard(df):
    if df.empty:
        return pd.DataFrame(columns=["User", "Total Picks"])
    return df.groupby("User").size().reset_index(name="Total Picks").sort_values("Total Picks", ascending=False)

# ---------------------------
# UI
# ---------------------------
st.title("NFL Pick'em App (Prototype)")

name = st.text_input("Enter your name:")
if st.button("Say hi"):
    st.write(f"Hey {name}, welcome to the app!")

mode = st.radio("Choose mode", ["Public Demo", "Live Mode (Password Required)"])

if mode == "Live Mode (Password Required)":
    pw = st.text_input("Enter password", type="password")
    if pw != PASSWORD:
        st.warning("❌ Incorrect password")
        st.stop()

    st.success("✅ Live mode unlocked")

    picks_df = load_picks()
    user = st.text_input("Your name")

    if user:
        st.subheader(f"Week {CURRENT_WEEK} Picks — {user}")
        session_picks = []
        for g in demo_games:
            pick = st.radio(
                f"{g['Game']} | Spread: {g['Spread']}",
                ["Home covers", "Away covers"],
                key=f"{g['Game']}_{user}"
            )
            session_picks.append({
                "Week": CURRENT_WEEK,
                "User": user,
                "Game": g["Game"],
                "Spread": g["Spread"],
                "Pick": pick,
                "Timestamp": datetime.now().isoformat(timespec="seconds")
            })

        if st.button("Submit Picks"):
            picks_df = pd.concat([picks_df, pd.DataFrame(session_picks)], ignore_index=True)
            save_picks(picks_df)
            st.success("✅ Picks saved")

    st.subheader("🏆 Leaderboard (demo scoring)")
    st.dataframe(leaderboard(load_picks()), use_container_width=True)

else:
    st.info("Public demo — play with the UI without saving data.")
    for g in demo_games:
        st.radio(
            f"{g['Game']} | Spread: {g['Spread']}",
            ["Home covers", "Away covers"],
            key=f"demo_{g['Game']}"
        )

    demo_df = pd.DataFrame([
        {"Week": 1, "User": "Alice", "Game": "Packers @ Bears", "Spread": -3.0, "Pick": "Home covers", "Timestamp": "2025-08-01 12:00"},
        {"Week": 1, "User": "Bob",   "Game": "Patriots @ Jets", "Spread": +7.0, "Pick": "Away covers", "Timestamp": "2025-08-01 12:05"},
    ])
    st.subheader("🏆 Leaderboard (demo data)")
    st.dataframe(leaderboard(demo_df), use_container_width=True)
