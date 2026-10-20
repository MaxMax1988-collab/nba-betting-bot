import json
import os
import pandas as pd
import requests


def get_fresh_nba_stats():
  print("Pobieranie aktualnych statystyk z otwartego serwera...")
  url = (
      "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings?season=2026"
  )
  headers = {"User-Agent": "Mozilla/5.0"}

  try:
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    data = res.json()

    teams_data = []
    for children in data.get("children", []):
      for stand in children.get("standings", {}).get("entries", []):
        team_info = stand.get("team", {})
        stats_list = stand.get("stats", [])

        def get_stat(name, default=0.0):
          for s in stats_list:
            if s.get("name") == name:
              return float(s.get("value", default))
          return float(default)

        gp = get_stat("gamesPlayed", 82)
        wins = get_stat("wins", 0)
        losses = get_stat("losses", 0)
        win_pct = get_stat("winPercent", wins / gp) if gp > 0 else 0.500

        avg_pts_for = get_stat("avgPointsFor", 112.0)
        avg_pts_against = get_stat("avgPointsAgainst", 112.0)

        off_rating = round(avg_pts_for * 0.98, 1)
        def_rating = round(avg_pts_against * 0.98, 1)
        net_rating = round(off_rating - def_rating, 1)

        teams_data.append({
            "TEAM_ID": int(team_info.get("id", 0)),
            "TEAM_NAME": team_info.get("displayName", "Unknown Team"),
            "GP": int(gp),
            "W": int(wins),
            "L": int(losses),
            "W_PCT": round(win_pct, 3),
            "OFF_RATING": off_rating,
            "DEF_RATING": def_rating,
            "NET_RATING": net_rating,
            "PACE": 99.0,
            "AST_PCT": 0.620,
            "REB_PCT": 0.500,
            "TS_PCT": 0.580,
        })

    if teams_data:
      with open("team_stats.json", "w", encoding="utf-8") as f:
        json.dump(teams_data, f, indent=4, ensure_ascii=False)
      print(
          f"SUKCES: Zapisano {len(teams_data)} aktualnych zespołów do"
          " team_stats.json"
      )
      return True
    else:
      print("BŁĄD: Pusta odpowiedź z API")
      return False

  except Exception as e:
    print(f"Błąd podczas pobierania danych z otwartego API: {e}")
    return False


if __name__ == "__main__":
  get_fresh_nba_stats()
    
