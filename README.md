# 🏈 NFL Pick'em App

A modern, interactive web app for tracking NFL spread picks with friends, featuring live and demo modes, Google Sheets integration, and rich analytics.

**Disclaimer:** This app is for fun and does not involve real-money betting.

---

## Features

- **Make Picks:**  
  Select your picks each week against the spread, with real-time line updates.
- **Past Picks:**  
  Review your historical picks and results, with clear win/loss indicators.
- **Group Picks:**  
  See what everyone picked for each game, with a group summary scoreboard.
- **Group Data:**  
  Visualize pick trends, most/least picked teams, and ATS (against the spread) records.
- **Leaderboards:**  
  Weekly and season-long leaderboards, including each user's "Best Team" (the team they've picked correctly most often).
- **Demo Mode:**  
  Try out the app with sample data, no login or sign-up required.
- **Mobile Friendly:**  
  Responsive design for desktop and mobile.
- **Google Sheets Integration:**  
  Live mode picks are saved and loaded from Google Sheets for persistence.

---

## Demo

Try the public demo:  
[NFL Pick'em App](https://nfl-pickem.streamlit.app)

---

## How It Works

The NFL Pick'em App is designed to make weekly NFL spread pools easy, fun, and transparent for groups of friends, coworkers, or leagues. Here’s a breakdown of the main workflows:

### Live Mode

- **User Authentication:**  
  Each user logs in with a unique password (one per user, managed by the admin).
- **Making Picks:**  
  Each week, users select their picks for every NFL game against the spread. Spreads are updated automatically from The Odds API.
- **Pick Submission:**  
  Picks are saved to a shared Google Sheet, ensuring persistence and transparency.
- **Results & Scoring:**  
  After games finish, results are automatically updated. Each pick is scored as correct, incorrect, or push (if applicable).
- **Review Past Picks:**  
  Users can view their historical picks and results, including which picks were correct or incorrect.
- **Group Insights:**  
  See what other users picked for each game, and view group-wide stats like most/least picked teams and ATS records.
- **Leaderboards:**  
  Weekly and season-long leaderboards show who’s on top.

### Demo Mode

- **No Login Required:**  
  Anyone can try out the app using sample data, no sign-up or password needed.
- **Mock Picks:**  
  Users can make picks for a sample week, see how the interface works, and view example results and leaderboards.
- **No Data Saved:**  
  Demo picks are not saved or tracked, it's just for exploring the app’s features.
- **Full Feature Access:**  
  All analytics, charts, and tables are available in demo mode, so users can see the full experience.

---

## Tech Stack

- [Streamlit](https://streamlit.io/) (frontend & backend)
- [Google Sheets API](https://developers.google.com/sheets/api) (live data storage)
- [Pandas](https://pandas.pydata.org/) (data analysis)
- [Plotly](https://plotly.com/python/) (charts)
- [GitHub Actions](https://github.com/features/actions) (automated data updates)
- [The Odds API](https://the-odds-api.com/) (NFL lines & scores)

---

## Setup & Deployment

1. **Clone the repo:**
    ```sh
    git clone https://github.com/jackewings/NFL-Pickem-App.git
    cd NFL-Pickem-App
    ```

2. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

3. **Set up Google Sheets credentials:**
    - Add your `gcp_service_account.json` (see [Google Sheets API docs](https://developers.google.com/sheets/api/quickstart/python)).

4. **Configure environment variables (if needed):**
    - Set any required API keys or secrets as environment variables on your system or deployment platform.

5. **Run locally:**
    ```sh
    streamlit run app.py
    ```

6. **Deploy:**
    - Deploy to [Streamlit Cloud](https://streamlit.io/cloud) or your preferred host.

---

## Data & Automation

- **Weekly spreads and results** are updated automatically via GitHub Actions (`.github/workflows/update_data.yml`).
- Demo data lives in `/data/demo_*` CSVs.

---

## Contact

Questions or feedback?  
Connect with me:  
[GitHub](https://github.com/jackewings) | [LinkedIn](https://www.linkedin.com/in/jack-ewings-profile/)

---

## License

MIT License. See [LICENSE](LICENSE.txt) for details.

---

**Enjoy tracking your NFL picks!**

