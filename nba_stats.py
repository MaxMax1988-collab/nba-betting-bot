import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats


def get_team_advanced_stats(season="2026-27", last_n_games=0):
  """Pobiera zaawansowane statystyki zespołów bezpośrednio z oficjalnego NBA API

  z pełnym logowaniem błędów w celu diagnozy połączenia.
  """
  # Sprawdzamy kolejno sezon bieżący oraz poprzedni jako fallback
  for target_season in [season, "2025-26"]:
    try:
      print(
          f"Rozpoczęto pobieranie statystyk NBA dla sezonu: {target_season}..."
      )

      # Wywołanie endpointu zaawansowanych statystyk drużyn
      stats = leaguedashteamstats.LeagueDashTeamStats(
          measure_type_detailed_defense="Advanced",
          season=target_season,
          last_n_games=last_n_games,
          timeout=30,
      )

      df = stats.get_data_frames()[0]

      if not df.empty:
        cols_to_keep = [
            "TEAM_ID",
            "TEAM_NAME",
            "GP",
            "W",
            "L",
            "W_PCT",
            "OFF_RATING",
            "DEF_RATING",
            "NET_RATING",
            "PACE",
            "AST_PCT",
            "REB_PCT",
            "TS_PCT",
        ]
        print(
            f"Sukces! Pobrano {len(df)} wierszy danych z NBA API dla sezonu"
            f" {target_season}"
        )
        return df[cols_to_keep].copy()
      else:
        print(
            f"Ostrzeżenie: NBA API zwróciło pustą tabelę dla sezonu"
            f" {target_season}."
        )

    except Exception as e:
      print(
          f"BŁÓD krytyczny podczas zapytania do NBA API (sezon"
          f" {target_season}): {e}"
      )

  print(
      "Nie udało się pobrać danych z żadnego sezonu. Sprawdź logi serwera."
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
    
