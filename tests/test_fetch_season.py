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
    fs._country_cache.clear()
    fs._driver_cache.update({
        "lando-norris": {"code": "NOR", "name": "Lando Norris", "nat": "GB"},
        "max-verstappen": {"code": "VER", "name": "Max Verstappen", "nat": "NL"},
        "charles-leclerc": {"code": "LEC", "name": "Charles Leclerc", "nat": "MC"},
    })


def test_team_name_mapping_and_fallback():
    assert fs.team_name("red-bull") == "Red Bull Racing"
    assert fs.team_name("kick-sauber") == "Kick Sauber"
    assert fs.team_name("audi") == "Audi"
    assert fs.team_name("some-new-team") == "Some New Team"   # title-case fallback
    assert fs.team_name(None) == ""


def test_country_alpha2_for_flags():
    fs._yaml_cache["countries/netherlands.yml"] = {"alpha2Code": "NL"}
    assert fs.country_alpha2("netherlands") == "NL"
    assert fs.country_alpha2(None) == ""


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
    assert race["winner"] == {"code": "NOR", "name": "Lando Norris", "nat": "GB", "team": "McLaren"}
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
    assert set(d) == {"season", "updated", "source", "races", "drivers",
                      "constructors", "stats"}
    assert d["drivers"][0] == {"pos": 1, "code": "NOR", "name": "Lando Norris",
                               "nat": "GB", "team": "McLaren", "points": 423, "wins": 7}
    assert d["constructors"][0] == {"pos": 1, "team": "McLaren", "points": 833, "wins": 14}
    assert d["stats"] == []          # no races supplied -> no per-driver rows


def test_build_driver_stats_aggregates_across_races():
    def row(code, name, pos, grid, pts, status="Finished", qpos=None,
            stops=None, pit_avg=None, pit_best=None, laps=57):
        return {"code": code, "name": name, "nat": "", "pos": pos, "grid": grid,
                "points": pts, "status": status, "qpos": qpos, "stops": stops,
                "pit_avg": pit_avg, "pit_best": pit_best, "laps": laps}

    races = [
        {"status": "completed", "dotd": "VER", "results": [
            row("NOR", "Lando Norris", 1, 1, 25, qpos=1, stops=2, pit_avg=23.0, pit_best=22.0),
            row("VER", "Max Verstappen", 2, 4, 18, qpos=3, stops=2, pit_avg=25.0, pit_best=24.0),
        ]},
        {"status": "completed", "dotd": None, "results": [
            row("NOR", "Lando Norris", 3, 5, 15, qpos=2, stops=1, pit_avg=21.0, pit_best=21.0),
            row("VER", "Max Verstappen", None, 2, 0, status="Accident", qpos=1,
                stops=1, pit_avg=27.0, pit_best=27.0, laps=10),
        ]},
        {"status": "upcoming", "results": []},   # ignored
    ]
    stats = fs.build_driver_stats(races, {"NOR": "McLaren", "VER": "Red Bull Racing"})
    by = {s["code"]: s for s in stats}

    nor = by["NOR"]
    assert nor["starts"] == 2 and nor["wins"] == 1 and nor["podiums"] == 2
    assert nor["poles"] == 1 and nor["dnf"] == 0 and nor["points"] == 40
    assert nor["avg_finish"] == 2.0 and nor["avg_grid"] == 3.0
    assert nor["gained"] == 2                       # (1-1) + (5-3)
    assert nor["avg_stops"] == 1.5                  # (2 + 1) / 2
    assert nor["pit_avg"] == 22.33                  # (23*2 + 21*1) / 3 stops
    assert nor["pit_best"] == 21.0
    assert nor["team"] == "McLaren" and nor["laps_led"] is None

    ver = by["VER"]
    assert ver["poles"] == 1 and ver["dnf"] == 1 and ver["dotd"] == 1
    assert ver["gained"] == 2                        # only the finished race counts (4-2)
    assert stats[0]["code"] == "NOR"                 # sorted by points desc


def test_build_driver_stats_uses_official_points_when_given():
    races = [{"status": "completed", "dotd": None, "results": [
        {"code": "VER", "name": "Max Verstappen", "nat": "", "pos": 2, "grid": 2,
         "points": 18, "status": "Finished", "laps": 57},   # sprint points not in GP result
    ]}]
    # Championship total (incl. sprint) differs from the summed GP points.
    stats = fs.build_driver_stats(races, {"VER": "Red Bull Racing"}, {"VER": 26})
    assert stats[0]["points"] == 26


def test_build_driver_stats_surfaces_laps_led_when_present():
    races = [{"status": "completed", "dotd": None, "results": [
        {"code": "VER", "name": "Max Verstappen", "nat": "", "pos": 1, "grid": 1,
         "points": 25, "status": "Finished", "laps": 57, "led": 40},
    ]}]
    stats = fs.build_driver_stats(races, {"VER": "Red Bull Racing"})
    assert stats[0]["laps_led"] == 40
