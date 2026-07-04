"""Network-free unit tests for the f1db-backed season fetcher.

Injects fixtures into the module's caches so the pure assembly logic
(``build_race``, ``assemble_season``, slug/team helpers) is exercised without
touching ``raw.githubusercontent.com``.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fetch_season as fs  # noqa: E402


def setup_function(_):
    fs._yaml_cache.clear()
    fs._driver_cache.clear()
    fs._driver_cache.update({
        "lando-norris": {"code": "NOR", "name": "Lando Norris"},
        "max-verstappen": {"code": "VER", "name": "Max Verstappen"},
        "charles-leclerc": {"code": "LEC", "name": "Charles Leclerc"},
    })


def test_team_name_mapping_and_fallback():
    assert fs.team_name("red-bull") == "Red Bull Racing"
    assert fs.team_name("kick-sauber") == "Kick Sauber"
    assert fs.team_name("audi") == "Audi"
    assert fs.team_name("some-new-team") == "Some New Team"   # title-case fallback
    assert fs.team_name(None) == ""


def test_slug_candidates():
    cands = fs._slug_candidates("Austrian Grand Prix", "Austria", "Spielberg")
    assert cands[0] == "austria"                 # from the name map
    assert "spielberg" in cands                  # locality is a fallback candidate


def test_build_race_upcoming_is_offline():
    ev = {"round": 20, "name": "Qatar Grand Prix", "country": "Qatar",
          "locality": "Lusail", "circuit": "Lusail", "date": "2026-11-29"}
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)   # race is in the future
    race = fs.build_race(2026, ev, now, {"drivers": {}, "teams": {}})
    assert race["status"] == "upcoming" and race["results"] == [] and race["winner"] is None


def test_build_race_completed_parses_f1db_results():
    fs._yaml_cache["seasons/2025/races/01-australia/race-results.yml"] = [
        {"position": 1, "driverId": "lando-norris", "constructorId": "mclaren",
         "points": 25, "gridPosition": 1, "laps": 57, "reasonRetired": None},
        {"position": 2, "driverId": "max-verstappen", "constructorId": "red-bull",
         "points": 18, "gridPosition": 3, "laps": 57, "reasonRetired": None},
        {"position": 3, "driverId": "charles-leclerc", "constructorId": "ferrari",
         "points": 15, "gridPosition": 2, "laps": 57, "reasonRetired": None},
    ]
    fs._yaml_cache["seasons/2025/races/01-australia/fast-laps.yml"] = None
    ev = {"round": 1, "name": "Australian Grand Prix", "country": "Australia",
          "locality": "Melbourne", "circuit": "Melbourne", "date": "2025-03-16"}
    wins = {"drivers": {}, "teams": {}}
    race = fs.build_race(2025, ev, datetime(2025, 7, 1, tzinfo=timezone.utc), wins)

    assert race["status"] == "completed"
    assert race["winner"] == {"code": "NOR", "name": "Lando Norris", "team": "McLaren"}
    assert [p["code"] for p in race["podium"]] == ["NOR", "VER", "LEC"]
    assert race["results"][1]["team"] == "Red Bull Racing"
    assert wins["drivers"]["NOR"] == 1 and wins["teams"]["McLaren"] == 1


def test_assemble_season_schema():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    driver_standings = [
        {"position": 1, "driverId": "lando-norris", "points": 423},
        {"position": 2, "driverId": "max-verstappen", "points": 421},
    ]
    constructor_standings = [
        {"position": 1, "constructorId": "mclaren", "points": 833},
        {"position": 2, "constructorId": "red-bull", "points": 451},
    ]
    team_by_code = {"NOR": "McLaren", "VER": "Red Bull Racing"}
    wins = {"drivers": {"NOR": 7, "VER": 8}, "teams": {"McLaren": 14}}
    d = fs.assemble_season(2025, [], driver_standings, constructor_standings,
                           team_by_code, wins, now)
    assert set(d) == {"season", "updated", "source", "races", "drivers", "constructors"}
    assert d["drivers"][0] == {"pos": 1, "code": "NOR", "name": "Lando Norris",
                               "team": "McLaren", "points": 423, "wins": 7}
    assert d["constructors"][0] == {"pos": 1, "team": "McLaren", "points": 833, "wins": 14}
