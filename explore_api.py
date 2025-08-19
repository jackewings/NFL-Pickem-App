import requests
import json

# ---------------------------
# Replace with your API key
# ---------------------------
API_KEY = st.secrets['API_KEY']

# Endpoint for NFL odds
url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
params = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "spreads",
    "oddsFormat": "decimal"
}

# Fetch data
response = requests.get(url, params=params)

try:
    data = response.json()
except Exception as e:
    print("Error decoding JSON:", e)
    exit()

# Pretty-print JSON in terminal
print(json.dumps(data, indent=2))

# Optionally save a copy locally to inspect later
with open("data/weekly_spreads_sample.json", "w") as f:
    json.dump(data, f, indent=2)

print("\nSaved JSON to data/weekly_spreads_sample.json")
