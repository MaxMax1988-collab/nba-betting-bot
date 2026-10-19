import os
import json
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import leaguegamefinder

DB_FILE = "predictions_history.json"
WEIGHTS_FILE = "model_weights.json"


def load_weights():
  """Wczytuje aktualne wagi modelu lub domyślne, jeśli plik nie istnieje."""
  default_weights = {
      "off_rtg": 0.38,
      "def_rtg": 0.38,
      "pace": 0.12,
      "ts_pct": 0.12,
      "learning_rate": 0.01,
  }
  if os.path.exists(WEIGHTS_FILE):
    try:
      with open(WEIGHTS_FILE, "r") as f:
        return json.load(f)
    except Exception:
      pass
  return default_weights


def save_weights(weights):
  """Zapisuje zkalibrowane wagi do pliku."""
  with open(WEIGHTS_FILE, "w") as f:
    json.dump(weights, f, indent=4)


def save_prediction(game_id, date, home_team, away_team, pred_home, pred_away, pred_spread):
  """Rejestruje nową predykcję bota przed meczem."""
  history = []
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r") as f:
        history = json.load(f)
    except Exception:
      pass

  # Sprawdzamy czy mecz już nie jest zapisany
  if not any(item["game_id"] == game_id for item in history):
    history.append({
        "game_id": game_id,
        "date": date,
        "home_team": home_team,
        "away_team": away_team,
        "pred_home": pred_home,
        "pred_away": pred_away,
        "pred_spread": pred_spread,
        "actual_home": None,
        "actual_away": None,
        "resolved": False,
    })
    with open(DB_FILE, "w") as f:
      json.dump(history, f, indent=4)


def calibrate_and_resolve_results(season="2025-26"):
  """Pobiera wczorajsze wyniki z NBA API, rozlicza typy i koryguje wagi modelu (Self-Learning)."""
  if not os.path.exists(DB_FILE):
    print("Brak historii predykcji do rozliczenia.")
    return

  with open(DB_FILE, "r") as f:
    history = json.load(f)

  unresolved = [h for h in history if not h["resolved"]]
  if not unresolved:
    print("Wszystkie dotychczasowe predykcie zostały już rozliczone.")
    return

  print(
      f"Pobieranie ostatnich wyników z NBA API w celu kalibracji dla"
      f" {len(unresolved)} meczów..."
  )
  try:
    # Pobieramy ostatnie wyniki ligowe
    gamefinder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season, season_type_nullable="Regular Season"
    )
    df_games = gamefinder.get_data_frames()[0]
  except Exception as e:
    print(f"Błąd pobierania wyników z NBA API: {e}")
    return

  weights = load_weights()
  updated_count = 0
  total_error = 0

  for item in unresolved:
    h_team = item["home_team"]
    a_team = item["away_team"]
    target_date = item["date"]

    # Szukamy meczu w dataframe po nazwach drużyn (uproszczone dopasowanie)
    # W docelowym systemie opieramy się na skrótach ID lub dacie
    match = df_games[df_games["MATCHUP"].str.contains(h_team[:3], na=False)]

    if not match.empty:
      # Pobieramy faktyczny wynik (PTS)
      # W LeagueGameFinder każdy wiersz to jedna drużyna w danym meczu
      game_ids = match["GAME_ID"].unique()
      for gid in game_ids:
        game_rows = df_games[df_games["GAME_ID"] == gid]
        if len(game_rows) == 2:
          team1_name = game_rows.iloc[0]["TEAM_NAME"]
          team2_name = game_rows.iloc[1]["TEAM_NAME"]

          if (h_team in team1_name or h_team in team2_name) and (
              a_team in team1_name or a_team in team2_name
          ):
            row_home = game_rows[game_rows["TEAM_NAME"].str.contains(h_team[:4])].iloc[0]
            row_away = game_rows[game_rows["TEAM_NAME"].str.contains(a_team[:4])].iloc[0]

            actual_home_pts = row_home["PTS"]
            actual_away_pts = row_away["PTS"]

            item["actual_home"] = int(actual_home_pts)
            item["actual_away"] = int(actual_away_pts)
            item["resolved"] = True

            # Obliczamy błąd predykcji punktowej
            error_home = abs(item["pred_home"] - actual_home_pts)
            error_away = abs(item["pred_away"] - actual_away_pts)
            game_error = (error_home + error_away) / 2
            total_error += game_error
            updated_count += 1

            # Pętla sprzężenia zwrotnego (Gradient Descent / Adjustment)
            # Jeśli model pomylił się w stronę zawyżenia punktów gospodarzy, korygujemy wagi ofensywne
            if item["pred_home"] > actual_home_pts:
              weights["off_rtg"] = max(
                  0.20, weights["off_rtg"] - weights["learning_rate"] * 0.05
              )
            else:
              weights["off_rtg"] = min(
                  0.55, weights["off_rtg"] + weights["learning_rate"] * 0.05
            )

            print(
                f"Rozliczono mecz: {a_team} @ {h_team} | Wynik realny:"
                f" {actual_home_pts}:{actual_away_pts} | Model:"
                f" {item['pred_home']}:{item['pred_away']}"
            )

  if updated_count > 0:
    # Normalizujemy wagi żeby suma głównych współczynników dawała ~0.88 + pace/ts
    save_weights(weights)
    save_prediction_history(history)
    print(
        f"Kalibracja zakończona pomyślnie. Zaktualizowano {updated_count}"
        f" meczów. Nowe wagi: {weights}"
    )


def save_prediction_history(history):
  with open(DB_FILE, "w") as f:
    json.dump(history, f, indent=4)


if __name__ == "__main__":
  calibrate_and_resolve_results()
      
