"""Network-free unit tests for the dashboard data assembler.

Builds Ergast-shaped DataFrames by hand and checks that `build_season_dict`
emits exactly the JSON contract the `web/` dashboard consumes.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fetch_season as fs  # noqa: E402


def _schedule():
    return pd.DataFrame([
        {"round": 1, "raceName": "Australian Grand Prix", "raceDate": pd.Timestamp("2026-03-08"),
         "circuitName": "Albert Park", "locality": "Melbourne", "country": "Australia"},
        {"round": 2, "raceName": "Chinese Grand Prix", "raceDate": pd.Timestamp("2026-03-15"),
         "circuitName": "Shanghai", "locality": "Shanghai", "country": "China"},
    ])


def _race_results():
    return pd.DataFrame([
        {"position": 1, "driverCode": "NOR", "givenName": "Lando", "familyName": "Norris",
         "constructorName": "McLaren", "grid": 1, "points": 25.0, "laps": 58, "status": "Finished"},
        {"position": 2, "driverCode": "LEC", "givenName": "Charles", "familyName": "Leclerc",
         "constructorName": "Ferrari", "grid": 2, "points": 18.0, "laps": 58, "status": "Finished"},
        {"position": 3, "driverCode": "VER", "givenName": "Max", "familyName": "Verstappen",
         "constructorName": "Red Bull", "grid": 4, "points": 15.0, "laps": 58, "status": "Finished"},
        {"position": None, "driverCode": "HAM", "givenName": "Lewis", "familyName": "Hamilton",
         "constructorName": "Ferrari", "grid": 3, "points": 0.0, "laps": 12, "status": "Retired"},
    ])


def _driver_standings():
    return pd.DataFrame([
        {"position": 1, "driverCode": "NOR", "givenName": "Lando", "familyName": "Norris",
         "constructorNames": ["McLaren"], "points": 25.0, "wins": 1},
        {"position": 2, "driverCode": "LEC", "givenName": "Charles", "familyName": "Leclerc",
         "constructorNames": ["Ferrari"], "points": 18.0, "wins": 0},
    ])


def _constructor_standings():
    return pd.DataFrame([
        {"position": 1, "constructorName": "McLaren", "points": 25.0, "wins": 1},
        {"position": 2, "constructorName": "Ferrari", "points": 18.0, "wins": 0},
    ])


def _season():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    return fs.build_season_dict(_schedule(), {1: _race_results()},
                                _driver_standings(), _constructor_standings(), 2026, now)


def test_top_level_schema():
    d = _season()
    assert set(d) == {"season", "updated", "races", "drivers", "constructors"}
    assert d["season"] == 2026
    # fully JSON-serialisable (front-end fetches it verbatim)
    json.dumps(d, default=fs._json_default)


def test_completed_vs_upcoming_race():
    races = _season()["races"]
    assert races[0]["status"] == "completed"
    assert races[0]["winner"]["code"] == "NOR"
    assert len(races[0]["podium"]) == 3
    # DNF sorts to the bottom of the classification
    assert races[0]["results"][-1]["status"] == "Retired"
    # round 2 has no results yet
    assert races[1]["status"] == "upcoming" and races[1]["results"] == []


def test_standings_shape():
    d = _season()
    assert d["drivers"][0] == {"pos": 1, "code": "NOR", "name": "Lando Norris",
                               "team": "McLaren", "points": 25.0, "wins": 1}
    assert d["constructors"][0]["team"] == "McLaren"


def test_empty_inputs_do_not_crash():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    d = fs.build_season_dict(pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame(), 2026, now)
    assert d["races"] == [] and d["drivers"] == [] and d["constructors"] == []
