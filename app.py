import os
import json
import requests
import pandas as pd
import streamlit as st
import nba_stats

# Konfiguracja Streamlit
st.set_page_config(
    page_title="NBA AI Betting & Predictor", page_icon="🏀", layout="wide"
)

st.title("🏀 NBA AI Predictor & Value Betting System")
st.markdown(
    "*W pełni zautomatyzowany system predykcji, kalibracji i value bettingu w NBA.*"
)

# Wczytywanie zkalibrowanych wag z pliku model_weights.json (jeśli istnieje)
WEIGHTS_FILE = "model_weights.json"


def load_active_weights():
  if os.path.exists(WEIGHTS_FILE):
    try:
      with open(WEIGHTS_FILE, "r") as f:
        return json.load(f)
    except Exception:
      pass
  return {"off_rtg": 0.38, "def_rtg": 0.38, "pace": 0.12, "ts_pct": 0.12}


active_weights = load_active_weights()

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


@st.cache_data(ttl=1800)
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


@st.cache_data(ttl=10800)
def fetch_nba_analytics(weights):
  df = nba_stats.get_team_advanced_stats(season="2025-26")
  if not df.empty:
    return nba_stats.calculate_power_rating(df, weights=weights)
  return pd.DataFrame()


# Nawigacja
st.sidebar.header("🎛️ Panel Sterowania")
page = st.sidebar.selectbox(
    "Wybierz zakładkę",
    [
        "🔥 Dzisiejsze Value Bety i Kursy",
        "⚡ Analizator Matchupów & Predyktor",
        "🏆 Power Index & Baza Statystyk",
        "⚙️ Stan Samouczenia (Wagi Modelu)",
        "📈 Dashboard Skuteczności (ROI)",
    ],
)

df_power = fetch_nba_analytics(active_weights)

if page == "🔥 Dzisiejsze Value Bety i Kursy":
  st.header("🎯 Wykryte Value Bety na Dziś")

  bankroll = st.sidebar.number_input(
      "Twój Kapitał (Bankroll PLN):", value=1000, step=100
  )

  with st.spinner("Analizowanie meczów i wyliczanie EV..."):
    odds_data = fetch_odds()

  if not odds_data:
    st.info("Brak dostępnych kursów bukmacherskich na ten moment.")
  else:
    found_value = False
    for game in odds_data:
      home_team = game["home_team"]
      away_team = game["away_team"]

      if not df_power.empty and home_team in df_power["TEAM_NAME"].values and away_team in df_power["TEAM_NAME"].values:
        home_row = df_power[df_power["TEAM_NAME"] == home_team].iloc[0]
        away_row = df_power[df_power["TEAM_NAME"] == away_team].iloc[0]

        # Model Probability (Moneyline) oparty na Power Index
        prob_home = home_row["POWER_INDEX"] / (
            home_row["POWER_INDEX"] + away_row["POWER_INDEX"]
        )
        prob_away = 1.0 - prob_home

        bookmakers = game.get("bookmakers", [])
        if bookmakers:
          bm = bookmakers[0]
          for market in bm.get("markets", []):
            if market["key"] == "h2h":
              for outcome in market.get("outcomes", []):
                team_name = outcome["name"]
                price = outcome["price"]

                model_p = prob_home if team_name == home_team else prob_away
                val_info = nba_stats.calculate_value_bet(
                    model_p, price, bankroll=bankroll
                )

                if val_info["is_value"]:
                  found_value = True
                  st.success(
                      f"🔥 **VALUE BET:** {team_name} (vs"
                      f" {away_team if team_name==home_team else home_team})"
                  )
                  v_col1, v_col2, v_col3, v_col4 = st.columns(4)
                  v_col1.metric("Kurs Bukmachera", f"{price}")
                  v_col2.metric("Prawdopodobieństwo Modelu", f"{val_info['model_prob']}%")
                  v_col3.metric("Expected Value (EV)", f"+{val_info['ev_percent']}%")
                  v_col4.metric(
                      "Sugerowana Stawka (Kelly)",
                      f"{val_info['recommended_stake']} PLN",
                  )
                  st.markdown("---")

    if not found_value:
      st.info(
          "Model przeanalizował dzisiejsze mecze i nie wykrył czystych Value"
          " Betów (EV > +2%). Zalecana powściągliwość."
      )

elif page == "⚡ Analizator Matchupów & Predyktor":
  st.header("⚡ Symulacja Meczu & Wpływ Zmęczenia")

  if not df_power.empty:
    teams_list = sorted(df_power["TEAM_NAME"].unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
      home_t = st.selectbox("Gospodarz:", teams_list, index=0)
      home_b2b = st.checkbox("Gospodarz gra Back-to-Back (B2B)?")
    with c2:
      away_t = st.selectbox(
          "Gość:", [t for t in teams_list if t != home_t], index=0
      )
      away_b2b = st.checkbox("Gość gra Back-to-Back (B2B)?")

    if st.button("🚀 Symuluj Spotkanie"):
      h_row = df_power[df_power["TEAM_NAME"] == home_t].iloc[0]
      a_row = df_power[df_power["TEAM_NAME"] == away_t].iloc[0]

      pace = (h_row["PACE"] + a_row["PACE"]) / 2

      # Zmęczenie daje -3.5 pkt dla drużyny grającej dzień po dniu
      h_fatigue = -3.5 if home_b2b else 0.0
      a_fatigue = -3.5 if away_b2b else 0.0

      exp_h = (
          (
              (
                  h_row["OFF_RATING"]
                  + a_row["DEF_RATING"]
                  - df_power["OFF_RATING"].mean()
              )
              / 100
          )
          * pace
      ) + 2.5 + h_fatigue
      exp_a = (
          (
              (
                  a_row["OFF_RATING"]
                  + h_row["DEF_RATING"]
                  - df_power["OFF_RATING"].mean()
              )
              / 100
          )
          * pace
      ) + a_fatigue

      spread = round(exp_h - exp_a, 1)

      m1, m2, m3 = st.columns(3)
      m1.metric("Prognoza Wyniku", f"{round(exp_h, 1)} : {round(exp_a, 1)}")
      m2.metric("Handicap Modelu", f"{home_t} {('-' if spread > 0 else '+')}{abs(spread)}")
      m3.metric("Suma Punktów (Total)", f"{round(exp_h + exp_a, 1)} pkt")

elif page == "🏆 Power Index & Baza Statystyk":
  st.header("🏆 Aktualny Ranking Formy (Power Index)")
  if not df_power.empty:
    st.dataframe(
        df_power[[
            "TEAM_NAME",
            "POWER_INDEX",
            "OFF_RATING",
            "DEF_RATING",
            "PACE",
            "TS_PCT",
        ]],
        use_container_width=True,
    )

elif page == "⚙️ Stan Samouczenia (Wagi Modelu)":
  st.header("⚙️ Aktualne Zkalibrowane Wagi Modelu")
  st.markdown(
      "Te wagi są automatycznie modyfikowane przez skrypt `trainer.py` po"
      " każdej kolejce meczowej!"
  )

  st.json(active_weights)

elif page == "📈 Dashboard Skuteczności (ROI)":
  st.header("📈 Statystyki i Historia Wyników")
  if os.path.exists("predictions_history.json"):
    with open("predictions_history.json", "r") as f:
      hist = json.load(f)
    st.write(f"Łącznie zarejestrowanych predykcji w bazie: **{len(hist)}**")
    st.dataframe(pd.DataFrame(hist))
  else:
    st.info("Baza danych predykcji jest budowana. Pierwsze rozliczenia pojawią się po nadchodzącej kolejce!")
      
