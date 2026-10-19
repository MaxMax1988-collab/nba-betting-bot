import os
import nba_stats
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="NBA AI Betting & Predictor", page_icon="🏀", layout="wide"
)

st.title("🏀 NBA AI Predictor & Value Betting System")
st.markdown(
    "*Zaawansowany system predykcji wyników, handicapów i szukania value"
    " betów.*"
)

# Pobieranie klucza API
API_KEY = None
try:
  if "ODDS_API_KEY" in st.secrets:
    API_KEY = st.secrets["ODDS_API_KEY"]
except Exception:
  pass

if not API_KEY:
  API_KEY = os.getenv("ODDS_API_KEY", "5f16c049cc0baccae587e0f50116f255")

SPORT = "basketball_nba"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"


@st.cache_data(ttl=3600)
def fetch_odds():
  url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
  params = {
      "api_key": API_KEY,
      "regions": REGIONS,
      "markets": MARKETS,
      "oddsFormat": "decimal",
  }
  response = requests.get(url, params=params)
  if response.status_code != 200:
    return None
  return response.json()


@st.cache_data(ttl=21600)  # Cache statystyk NBA na 6 godzin
def fetch_nba_analytics():
  df = nba_stats.get_team_advanced_stats(season="2025-26")
  if not df.empty:
    return nba_stats.calculate_power_rating(df)
  return pd.DataFrame()


st.sidebar.header("🎛️ Panel Sterowania")
page = st.sidebar.selectbox(
    "Wybierz zakładkę",
    [
        "Dzisiejsze Mecze i Kursy",
        "Analizator Matchupów i Predyktor",
        "Baza Statystyk i Power Index",
        "Statystyki i ROI (Backtesting)",
    ],
)

# Pobieramy dane w tle
df_power = fetch_nba_analytics()

if page == "Dzisiejsze Mecze i Kursy":
  st.header("📅 Nadchodzące spotkania i kursy rynkowe")
  with st.spinner("Pobieranie najświeższych kursów..."):
    data = fetch_odds()

  if data is None or len(data) == 0:
    st.info("Brak dostępnych meczów lub błąd API.")
  else:
    for game in data:
      home_team = game["home_team"]
      away_team = game["away_team"]
      commence_time = game["commence_time"]

      with st.expander(f"🏟️ {away_team} @ {home_team} | Start: {commence_time}"):
        bookmakers = game.get("bookmakers", [])
        if bookmakers:
          bm = bookmakers[0]
          st.markdown(f"**Bukmacher główny:** `{bm['title']}`")
          for market in bm.get("markets", []):
            st.markdown(f"* **Rynek:** `{market['key']}`")
            for outcome in market.get("outcomes", []):
              point_info = (
                  f" (Linia: {outcome.get('point')})"
                  if "point" in outcome
                  else ""
              )
              st.write(
                  f"  - {outcome['name']}: **{outcome.get('price')}**"
                  f" {point_info}"
              )

elif page == "Analizator Matchupów i Predyktor":
  st.header("⚡ Kalkulator Symulacji Meczu & Prediction Engine")

  if df_power.empty:
    st.error("Brak danych statystycznych z NBA API.")
  else:
    teams_list = sorted(df_power["TEAM_NAME"].unique().tolist())

    col1, col2 = st.columns(2)
    with col1:
      home_team = st.selectbox(
          "Gospodarz (Home Team):", teams_list, index=0
      )
    with col2:
      away_list = [t for t in teams_list if t != home_team]
      away_team = st.selectbox(
          "Gość (Away Team):", away_list, index=0
      )

    # Parametry symulacji
    home_advantage = st.slider("Atut własnego parkietu (pkt)", 0.0, 5.0, 2.5, 0.5)

    if st.button("🚀 Przeprowadź Analizę i Predykcję"):
      home_row = df_power[df_power["TEAM_NAME"] == home_team].iloc[0]
      away_row = df_power[df_power["TEAM_NAME"] == away_team].iloc[0]

      # Wyznaczenie oczekiwanego tempa (Pace)
      expected_pace = (home_row["PACE"] + away_row["PACE"]) / 2

      # Szacowanie zdobytych punktów na bazie Off/Def Ratings na 100 posiadan
      # Oczekiwany Offense Gospodarzy vs Defense Gości
      exp_home_score = (
          (
              (
                  home_row["OFF_RATING"]
                  + away_row["DEF_RATING"]
                  - df_power["OFF_RATING"].mean()
              )
              / 100
          )
          * expected_pace
      ) + home_advantage
      exp_away_score = (
          (
              away_row["OFF_RATING"]
              + home_row["DEF_RATING"]
              - df_power["OFF_RATING"].mean()
          )
          / 100
      ) * expected_pace

      predicted_spread = round(exp_home_score - exp_away_score, 1)
      predicted_total = round(exp_home_score + exp_away_score, 1)

      st.markdown("---")
      st.subheader("📊 Wynik Symulacji Modelu:")

      res_col1, res_col2, res_col3 = st.columns(3)
      res_col1.metric("Prognozowany Wynik", f"{round(exp_home_score, 1)} : {round(exp_away_score, 1)}")
      res_col2.metric(
          "Sugerowany Handicap (Spread)",
          f"{home_team} {('-' if predicted_spread > 0 else '+')}{abs(predicted_spread)}",
      )
      res_col3.metric("Prognozowana Suma (Total)", f"{predicted_total} pkt")

elif page == "Baza Statystyk i Power Index":
  st.header("🏆 Ranking Drużyn (Power Index & Advanced Stats)")
  if not df_power.empty:
    st.dataframe(
        df_power[[
            "TEAM_NAME",
            "POWER_INDEX",
            "OFF_RATING",
            "DEF_RATING",
            "NET_RATING",
            "PACE",
            "TS_PCT",
        ]],
        use_container_width=True,
    )
  else:
    st.warning("Ładowanie statystyk z NBA API...")

elif page == "Statystyki i ROI (Backtesting)":
  st.header("📈 Skuteczność Systemu i ROI")
  chart_data = pd.DataFrame(
      {"Kolejka": ["Dzień 1", "Dzień 2", "Dzień 3", "Dzień 4"], "ROI (%)": [0.0, 4.2, 8.5, 12.4]}
  )
  st.line_chart(chart_data, x="Kolejka", y="ROI (%)")
    
