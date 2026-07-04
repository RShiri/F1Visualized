"""Fetch real F1 season data for the dashboard.

Data sources — both reachable without the blocked live-timing / Ergast APIs:

* **Calendar** — ``fastf1.get_event_schedule`` (real rounds, names, dates, venues).
* **Results & standings** — the open-source **f1db** dataset, read straight from
  its committed source YAML on ``raw.githubusercontent.com`` (authoritative and
  updated through the current season, 2025 *and* 2026).

Writes ``web/data/<year>.json`` in the schema the ``web/`` dashboard consumes.
The pure ``assemble_season`` builder is decoupled from the network for testing.

    python fetch_season.py --year 2025
    python fetch_season.py                 # both 2025 and 2026
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fetch_season")

F1DB = "https://raw.githubusercontent.com/f1db/f1db/main/src/data"

# f1db constructorId -> display name (aligned with the front-end colour map).
# Era-correct display names (f1db uses distinct constructorIds across eras).
TEAM_NAMES = {
    "mclaren": "McLaren", "ferrari": "Ferrari", "mercedes": "Mercedes",
    "red-bull": "Red Bull Racing", "aston-martin": "Aston Martin", "alpine": "Alpine",
    "williams": "Williams", "haas": "Haas", "audi": "Audi", "cadillac": "Cadillac",
    "alphatauri": "AlphaTauri", "rb": "RB", "racing-bulls": "Racing Bulls",
    "alfa-romeo": "Alfa Romeo", "sauber": "Sauber", "kick-sauber": "Kick Sauber",
}

# fastf1 event name (lowercased, minus "grand prix") -> f1db grand-prix slug.
# Country/locality are tried as extra candidates, so this only needs oddities.
GP_SLUGS = {
    "australian": "australia", "chinese": "china", "japanese": "japan",
    "bahrain": "bahrain", "saudi arabian": "saudi-arabia", "miami": "miami",
    "emilia romagna": "emilia-romagna", "monaco": "monaco", "spanish": "spain",
    "canadian": "canada", "austrian": "austria", "british": "great-britain",
    "belgian": "belgium", "hungarian": "hungary", "dutch": "netherlands",
    "italian": "italy", "azerbaijan": "azerbaijan", "singapore": "singapore",
    "united states": "united-states", "mexico city": "mexico", "mexican": "mexico",
    "são paulo": "sao-paulo", "sao paulo": "sao-paulo", "brazilian": "sao-paulo",
    "las vegas": "las-vegas", "qatar": "qatar", "abu dhabi": "abu-dhabi",
    "portuguese": "portugal", "french": "france",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


# --------------------------------------------------------------------------- #
# Network layer (only touches raw.githubusercontent.com)
# --------------------------------------------------------------------------- #
_session = None
_yaml_cache: dict[str, object] = {}


def _get_yaml(path: str, retries: int = 3):
    """GET + parse an f1db YAML file. Returns parsed data, or None on 404/failure."""
    if path in _yaml_cache:
        return _yaml_cache[path]
    global _session
    import requests
    import yaml

    if _session is None:
        _session = requests.Session()
    url = f"{F1DB}/{path}"
    for attempt in range(retries):
        try:
            resp = _session.get(url, timeout=25)
            if resp.status_code == 404:
                _yaml_cache[path] = None
                return None
            resp.raise_for_status()
            data = yaml.safe_load(resp.text)
            _yaml_cache[path] = data
            return data
        except requests.RequestException as exc:
            if attempt == retries - 1:
                log.warning("Failed to fetch %s: %s", path, exc)
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


# --------------------------------------------------------------------------- #
# Resolvers (cached)
# --------------------------------------------------------------------------- #
_driver_cache: dict[str, dict] = {}
_country_cache: dict[str, str] = {}


def country_alpha2(country_id) -> str:
    """f1db ``countryId`` -> ISO alpha-2 code (drives flag emoji). '' if unknown."""
    if not country_id:
        return ""
    if country_id in _country_cache:
        return _country_cache[country_id]
    info = _get_yaml(f"countries/{country_id}.yml") or {}
    code = str(info.get("alpha2Code") or "").upper()
    _country_cache[country_id] = code
    return code


def resolve_driver(driver_id: str) -> dict:
    """``driverId`` -> ``{code, name, nat}`` (from the f1db driver file)."""
    if driver_id in _driver_cache:
        return _driver_cache[driver_id]
    info = _get_yaml(f"drivers/{driver_id}.yml") or {}
    name = info.get("name") or driver_id.replace("-", " ").title()
    last = str(info.get("lastName") or driver_id.split("-")[-1])
    code = info.get("abbreviation") or last[:3].upper()
    nat = country_alpha2(info.get("nationalityCountryId"))
    out = {"code": code, "name": name, "nat": nat}
    _driver_cache[driver_id] = out
    return out


def team_name(constructor_id: Optional[str]) -> str:
    if not constructor_id:
        return ""
    return TEAM_NAMES.get(constructor_id, constructor_id.replace("-", " ").title())


# --------------------------------------------------------------------------- #
# Per-race fetch
# --------------------------------------------------------------------------- #
def _slug_candidates(event_name: str, country: str, locality: str) -> list[str]:
    name = (event_name or "").lower().replace(" grand prix", "").strip()
    cands = []
    if name in GP_SLUGS:
        cands.append(GP_SLUGS[name])
    for token in (name, locality, country):
        s = _slugify(token)
        if s and s not in cands:
            cands.append(s)
    return cands


def _fetch_race_results(year: int, rnd: int, candidates: list[str]):
    """Return ``(results_list, slug)`` for a completed race, or ``(None, None)``."""
    for slug in candidates:
        data = _get_yaml(f"seasons/{year}/races/{rnd:02d}-{slug}/race-results.yml")
        if data:
            return data, slug
    return None, None


def build_race(year: int, ev: dict, now: datetime, wins: dict) -> dict:
    """Assemble one race dict; fetches f1db results if the race is in the past."""
    race = {
        "round": ev["round"], "name": ev["name"], "country": ev["country"],
        "locality": ev["locality"], "circuit": ev["circuit"], "date": ev["date"],
        "status": "upcoming", "winner": None, "podium": [], "fastest_lap": None, "results": [],
    }
    if not (ev["date"] and ev["date"] <= now.strftime("%Y-%m-%d")):
        return race  # future race — don't probe

    candidates = _slug_candidates(ev["name"], ev["country"], ev["locality"])
    results, slug = _fetch_race_results(year, ev["round"], candidates)
    if not results:
        return race  # completed but not yet in f1db

    rows = []
    for r in results:
        drv = resolve_driver(r.get("driverId", ""))
        pos = r.get("position")
        rows.append({
            "pos": int(pos) if isinstance(pos, int) else None,
            "code": drv["code"], "name": drv["name"], "nat": drv["nat"],
            "team": team_name(r.get("constructorId")),
            "grid": r.get("gridPosition") if isinstance(r.get("gridPosition"), int) else None,
            "points": r.get("points") or 0,
            "laps": r.get("laps") if isinstance(r.get("laps"), int) else None,
            "status": "Finished" if not r.get("reasonRetired") else str(r.get("reasonRetired")),
        })
    rows.sort(key=lambda e: (e["pos"] is None, e["pos"] or 0))

    race["status"] = "completed"
    race["results"] = rows
    race["podium"] = [{"pos": r["pos"], "code": r["code"], "name": r["name"],
                       "nat": r["nat"], "team": r["team"]}
                      for r in rows if r["pos"] in (1, 2, 3)]
    if race["podium"]:
        w = race["podium"][0]
        race["winner"] = {"code": w["code"], "name": w["name"], "nat": w["nat"], "team": w["team"]}
        wins["drivers"][w["code"]] = wins["drivers"].get(w["code"], 0) + 1
        wins["teams"][w["team"]] = wins["teams"].get(w["team"], 0) + 1

    fl = _get_yaml(f"seasons/{year}/races/{ev['round']:02d}-{slug}/fast-laps.yml")
    if isinstance(fl, list) and fl:
        d = resolve_driver(fl[0].get("driverId", ""))
        race["fastest_lap"] = {"code": d["code"], "name": d["name"], "time": str(fl[0].get("time") or "")}
    return race


# --------------------------------------------------------------------------- #
# Season assembly
# --------------------------------------------------------------------------- #
def assemble_season(year, races, driver_standings, constructor_standings,
                    team_by_code, wins, now) -> dict:
    """Pure assembler: combine fetched pieces into the dashboard schema."""
    drivers = []
    for s in driver_standings or []:
        drv = resolve_driver(s.get("driverId", ""))
        drivers.append({
            "pos": s.get("position"), "code": drv["code"], "name": drv["name"],
            "nat": drv["nat"], "team": team_by_code.get(drv["code"], ""),
            "points": s.get("points") or 0, "wins": wins["drivers"].get(drv["code"], 0),
        })
    constructors = []
    for s in constructor_standings or []:
        tm = team_name(s.get("constructorId"))
        constructors.append({
            "pos": s.get("position"), "team": tm,
            "points": s.get("points") or 0, "wins": wins["teams"].get(tm, 0),
        })
    return {
        "season": int(year), "updated": now.isoformat(), "source": "f1db + fastf1",
        "races": races, "drivers": drivers, "constructors": constructors,
    }


def _team_by_code(year: int, races: list) -> dict:
    """driver code -> current team: season entrants, overridden by latest race."""
    out: dict[str, str] = {}
    for ent in _get_yaml(f"seasons/{year}/entrants.yml") or []:
        tm = team_name(ent.get("constructorId"))
        for d in ent.get("drivers", []) or []:
            if d.get("rounds") and not d.get("testDriver"):
                out[resolve_driver(d["driverId"])["code"]] = tm
    for race in races:  # earliest -> latest, so the most recent team wins
        for r in race.get("results", []):
            if r["team"]:
                out[r["code"]] = r["team"]
    return out


def fetch_season(year: int, now: Optional[datetime] = None) -> dict:
    """Fetch one season from fastf1 (calendar) + f1db (results/standings)."""
    import fastf1
    import pandas as pd

    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(config.CACHE_DIR))
    now = now or datetime.now(timezone.utc)

    schedule_df = fastf1.get_event_schedule(year, include_testing=False)
    events = []
    for _, ev in schedule_df.iterrows():
        rnd = int(ev["RoundNumber"])
        if rnd < 1:
            continue
        d = pd.to_datetime(ev.get("Session5DateUtc") or ev.get("EventDate"))
        events.append({
            "round": rnd, "name": str(ev["EventName"]), "country": str(ev.get("Country", "")),
            "locality": str(ev.get("Location", "")), "circuit": str(ev.get("Location", "")),
            "date": d.strftime("%Y-%m-%d") if pd.notna(d) else "",
        })

    wins = {"drivers": {}, "teams": {}}
    races = [build_race(year, ev, now, wins) for ev in events]

    driver_standings = _get_yaml(f"seasons/{year}/driver-standings.yml") or []
    constructor_standings = _get_yaml(f"seasons/{year}/constructor-standings.yml") or []
    team_by_code = _team_by_code(year, races)

    season = assemble_season(year, races, driver_standings, constructor_standings,
                             team_by_code, wins, now)
    done = sum(1 for r in races if r["status"] == "completed")
    log.info("%s: %d races (%d completed), %d drivers, %d constructors.",
             year, len(races), done, len(season["drivers"]), len(season["constructors"]))
    return season


def write_season_json(season: dict, year: int, out_dir: Optional[Path] = None) -> Path:
    out_dir = out_dir or (config.ROOT_DIR / "web" / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{year}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(season, fh, ensure_ascii=False, indent=1, default=str)
    log.info("Wrote %s", path)
    return path


def main(argv=None):
    p = argparse.ArgumentParser(description="Fetch real F1 season data for the dashboard.")
    p.add_argument("--year", type=int, action="append", help="Season(s); repeatable.")
    args = p.parse_args(argv)
    for y in (args.year or [2025, 2026]):
        try:
            write_season_json(fetch_season(y), y)
        except Exception as exc:
            log.warning("Could not fetch %s: %s", y, exc)


if __name__ == "__main__":
    main()
