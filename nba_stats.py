import json
import os
import pandas as pd

DATA_FILE = "team_stats.json"


def get_team_advanced_stats(season="2026-27", last_n_games=0):
  """Wczytuje wyłącznie prawdziwe, pobrane ze źródeł zewnętrznych dane.

  Zero sztucznych lub zmyślonych wartości.
  """
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
      df = pd.DataFrame(data)
      if not df.empty:
        return df
    except Exception as e:
      print(f"Błąd odczytu pliku z danymi: {e}")

  print(
      "OSTRZEŻENIE: Brak pliku team_stats.json z prawdziwymi statystykami."
  )
  return pd.DataFrame()


def calculate_power_rating(df_stats, weights=None):
  """Oblicza unikalny Power Index dla każdej drużyny na bazie zdefiniowanych wag."""
  if df_stats.empty:
    return df_stats

  if weights is None:
    weights = {
        "off_rtg": 0.38,
        "def_rtg": 0.38,
        "pace": 0.12,
        "ts_pct": 0.12,
    }

  df = df_stats.copy()

  df["OFF_SCORE"] = (
      (df["OFF_RATING"] - df["OFF_RATING"].min())
      / (df["OFF_RATING"].max() - df["OFF_RATING"].min())
  ) * 100

  df["DEF_SCORE"] = (
      (df["DEF_RATING"].max() - df["DEF_RATING"])
      / (df["DEF_RATING"].max() - df["DEF_RATING"].min())
  ) * 100

  df["TS_SCORE"] = (
      (df["TS_PCT"] - df["TS_PCT"].min())
      / (df["TS_PCT"].max() - df["TS_PCT"].min())
  ) * 100

  df["POWER_INDEX"] = (
      (df["OFF_SCORE"] * weights.get("off_rtg", 0.38))
      + (df["DEF_SCORE"] * weights.get("def_rtg", 0.38))
      + (df["TS_SCORE"] * weights.get("ts_pct", 0.12))
  ).round(2)

  return df.sort_values(by="POWER_INDEX", ascending=False)


def calculate_value_bet(
    model_prob, decimal_odds, bankroll=1000, kelly_fraction=0.25
):
  implied_prob = 1.0 / decimal_odds
  ev = (model_prob * decimal_odds) - 1.0

  recommended_stake = 0
  if ev > 0:
    b = decimal_odds - 1.0
    p = model_prob
    q = 1.0 - p
    f_kelly = (b * p - q) / b
    recommended_stake = round(bankroll * f_kelly * kelly_fraction, 2)

  return {
      "is_value": ev > 0.02,
      "ev_percent": round(ev * 100, 2),
      "implied_prob": round(implied_prob * 100, 1),
      "model_prob": round(model_prob * 100, 1),
      "recommended_stake": max(0, recommended_stake),
  }
  
