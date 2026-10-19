import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats


def get_team_advanced_stats(season="2025-26", last_n_games=0):
  """Pobiera zaawansowane statystyki zespołów (OffRtg, DefRtg, Pace, NetRtg).

  :param season: Sezon NBA w formacie 'YYYY-YY'
  :param last_n_games: 0 dla całego sezonu, lub np. 5/10 dla oceny ostatniej
  formy
  """
  try:
    print(
        f"Pobieranie statystyk NBA za sezon {season} (Ostatnie mecze:"
        f" {last_n_games})..."
    )
    stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense="Advanced",
        season=season,
        last_n_games=last_n_games,
        timeout=30,
    )

    df = stats.get_data_frames()[0]

    # Wybieramy kluczowe kolumny dla naszego systemu wag
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
        "TS_PCT",  # True Shooting %
    ]

    df_filtered = df[cols_to_keep].copy()
    return df_filtered

  except Exception as e:
    print(f"Błąd podczas pobierania statystyk z NBA API: {e}")
    return pd.DataFrame()


def calculate_power_rating(df_stats, weights=None):
  """Oblicza unikalny Rating Mocy (Power Index) dla każdej drużyny

  na podstawie zdefiniowanego systemu wag.
  """
  if df_stats.empty:
    return df_stats

  if weights is None:
    weights = {
        "off_rtg": 0.40,
        "def_rtg": 0.40,
        "pace": 0.10,
        "ts_pct": 0.10,
    }

  df = df_stats.copy()

  # Normalizacja wskaźników do skali 0-100 dla ułatwienia obliczeń
  df["OFF_SCORE"] = (
      (df["OFF_RATING"] - df["OFF_RATING"].min())
      / (df["OFF_RATING"].max() - df["OFF_RATING"].min())
  ) * 100

  # Drapanie/Defensywa: im niższy DefRtg tym lepiej, więc odwracamy skalę
  df["DEF_SCORE"] = (
      (df["DEF_RATING"].max() - df["DEF_RATING"])
      / (df["DEF_RATING"].max() - df["DEF_RATING"].min())
  ) * 100

  df["TS_SCORE"] = (
      (df["TS_PCT"] - df["TS_PCT"].min())
      / (df["TS_PCT"].max() - df["TS_PCT"].min())
  ) * 100

  # Algorytm oceny końcowej (Power Index)
  df["POWER_INDEX"] = (
      (df["OFF_SCORE"] * weights["off_rtg"])
      + (df["DEF_SCORE"] * weights["def_rtg"])
      + (df["TS_SCORE"] * weights["ts_pct"])
  ).round(2)

  return df.sort_values(by="POWER_INDEX", ascending=False)


if __name__ == "__main__":
  # Szybki test lokalny
  df = get_team_advanced_stats(season="2025-26")
  if not df.empty:
    df_ranked = calculate_power_rating(df)
    print("\n--- TOP 5 Drużyn według naszego Power Index ---")
    print(
        df_ranked[
            ["TEAM_NAME", "OFF_RATING", "DEF_RATING", "NET_RATING", "POWER_INDEX"]
        ].head()
    )
    
