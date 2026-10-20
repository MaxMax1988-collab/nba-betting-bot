import json
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats


def fetch_and_save_real_data():
  """Pobiera wyłącznie prawdziwe statystyki z NBA API i zapisuje do pliku JSON.

  Żadnych sztucznych danych.
  """
  for target_season in ["2026-27", "2025-26"]:
    try:
      print(f"Próba pobrania prawdziwych danych dla sezonu {target_season}...")
      stats = leaguedashteamstats.LeagueDashTeamStats(
          measure_type_detailed_defense="Advanced",
          season=target_season,
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
        df_filtered = df[cols_to_keep].copy()
        df_filtered.to_json(
            "team_stats.json", orient="records", force_ascii=False, indent=4
        )
        print(
            f"Sukces! Pobrano i zapisano {len(df_filtered)} autentycznych"
            f" zespołów dla sezonu {target_season}."
        )
        return True
    except Exception as e:
      print(
          "Błąd podczas pobierania z API dla sezonu"
          f" {target_season}: {e}"
      )

  print("Nie udało się pobrać danych z oficjalnego API NBA.")
  return False


if __name__ == "__main__":
  fetch_and_save_real_data()
  
