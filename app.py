import os
import pandas as pd
import requests
import streamlit as st

# Konfiguracja strony Streamlit
st.set_page_config(
    page_title="NBA AI Betting & Predictor", page_icon="🏀", layout="wide"
)

# Nagłówek aplikacji
st.title("🏀 NBA AI Predictor & Value Betting System")
st.markdown(
    "*Zaawansowany system predykcji wyników, handicapów i szukania value"
    " betów oparty na algorytmach i analizie danych.*"
)

# Pobieranie klucza API (Streamlit Secrets na chmurze lub zmienna środowiskowa lokalnie/GitHub Actions)
API_KEY = None
try:
  if "ODDS_API_KEY" in st.secrets:
    API_KEY = st.secrets["ODDS_API_KEY"]
except Exception:
  pass

if not API_KEY:
  API_KEY = os.getenv("ODDS_API_KEY", "5f16c049cc0baccae587e0f50116f255")

# Parametry The Odds API
SPORT = "basketball_nba"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"


@st.cache_data(ttl=3600)  # Cache'ujemy dane na 1 godzinę, żeby nie zużywać limitu API
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


# Sekcja interfejsu
st.sidebar.header("🎛️ Panel Sterowania")
page = st.sidebar.selectbox(
    "Wybierz zakładkę",
    [
        "Dzisiejsze Mecze i Kursy",
        "Modele i Wagi (Algorytm)",
        "Statystyki i ROI (Backtesting)",
    ],
)

if page == "Dzisiejsze Mecze i Kursy":
  st.header("📅 Nadchodzące spotkania i kursy rynkowe")

  with st.spinner("Pobieranie najświeższych kursów z The Odds API..."):
    data = fetch_odds()

  if data is None:
    st.error(
        "Nie udało się pobrać danych z The Odds API. Sprawdź poprawność klucza"
        " API."
    )
  elif len(data) == 0:
    st.info(
        "Brak nadchodzących meczów NBA w tej chwili (sezon/przerwa lub brak"
        " wystawionych linii)."
    )
  else:
    st.success(f"Pomyślnie pobrano {len(data)} nadchodzących meczów!")

    for game in data:
      home_team = game["home_team"]
      away_team = game["away_team"]
      commence_time = game["commence_time"]

      with st.expander(f"🏟️ {away_team} @ {home_team} | Start: {commence_time}"):
        st.write(f"**ID Meczu:** `{game['id']}`")

        # Wyciągamy kursy bukmacherów
        bookmakers = game.get("bookmakers", [])
        if bookmakers:
          # Bierzemy pierwszego bukmachera jako przykład
          bm = bookmakers[0]
          st.markdown(f"**Bukmacher główny:** `{bm['title']}`")

          for market in bm.get("markets", []):
            st.markdown(f"* **Rynek:** `{market['key']}`")
            for outcome in market.get("outcomes", []):
              point_info = (
                  f" (Linia/Spread: {outcome.get('point')})"
                  if "point" in outcome
                  else ""
              )
              st.write(
                  f"  - {outcome['name']}: **{outcome.get('price')}**"
                  f" {point_info}"
              )
        else:
          st.warning("Brak dostępnych kursów u bukmacherów dla tego spotkania.")

elif page == "Modele i Wagi (Algorytm)":
  st.header("⚙️ Konfiguracja Systemu Wag i Czynników Predykcji")
  st.markdown(
    "Tutaj w przyszłości dostosujemy wagi poszczególnych zmiennych"
    " decydujących o typie:"
  )

  col1, col2 = st.columns(2)
  with col1:
    w_off = st.slider(
        "Waga Formy Offensive (OffRtg)", 0.0, 1.0, 0.35, 0.05
    )
    w_def = st.slider(
        "Waga Formy Defensive (DefRtg)", 0.0, 1.0, 0.35, 0.05
    )
  with col2:
    w_rest = st.slider("Waga Zmęczenia (B2B / Podróże)", 0.0, 1.0, 0.15, 0.05)
    w_home = st.slider("Waga Parkietu (Home Court Advantage)", 0.0, 1.0, 0.15, 0.05)

  st.info(
      "Suma wag musi wynosić 1.0. W kolejnym kroku podepniemy pod te wagi"
      " statystyki z oficjalnego API NBA."
  )

elif page == "Statystyki i ROI (Backtesting)":
  st.header("📈 Skuteczność Systemu i ROI")
  st.markdown(
    "Moduł śledzenia trafności typów oraz wykres wzrostu kapitału (Bankrolla)."
  )

  # Przykładowe dane wykresowe dla ilustracji struktury
  chart_data = pd.DataFrame(
      {
          "Kolejka / Dzień": [
              "Dzień 1",
              "Dzień 2",
              "Dzień 3",
              "Dzień 4",
              "Dzień 5",
          ],
          "ROI (%)": [0.0, 4.2, 3.1, 8.5, 12.4],
      }
  )

  st.line_chart(chart_data, x="Kolejka / Dzień", y="ROI (%)")
  st.metric(label="Aktualny ROI", value="+12.4%", delta="+3.9% wczoraj")
          
