"""Fetch a full F1 season via fastf1's Ergast client into a static-site JSON.

This is the data feeder for a static dashboard: for a given year it pulls the
race **schedule**, per-round **race results**, and the final **driver** and
**constructor standings** from the Ergast API (through :mod:`fastf1.ergast`),
then writes a single ``web/data/<year>.json`` document in the exact shape the
front-end expects.

Design notes
------------
* **Modular / unit-testable.** The schema is assembled by the *pure* function
  :func:`build_season_dict`, which takes plain ``pandas`` DataFrames and a
  ``now`` timestamp and never touches the network. The thin
  :func:`fetch_season` adapter is the only piece that talks to Ergast; it feeds
  those DataFrames into the pure builder.
* **Degrades gracefully.** Every network call is wrapped so that a blocked or
  missing endpoint logs a warning and still yields a *valid* JSON document
  (e.g. the schedule with all races marked "upcoming" and empty standings)
  rather than raising and losing the whole season.
* **No presentation logic.** Only team *names* are emitted — colours and other
  styling are the front-end's job.

Run standalone::

    python fetch_season.py                 # both 2025 and 2026
    python fetch_season.py --year 2025     # a single season
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s"
)
log = logging.getLogger("fetch_season")

# Seasons fetched when no --year is supplied on the command line.
DEFAULT_SEASONS = (2025, 2026)

# Ergast paginates on the innermost result rows and defaults to 30. A full
# season of race results is ~24 races * ~20 cars, so a generous limit keeps the
# whole season in a single response. 1000 is the Ergast maximum.
_RESULTS_LIMIT = 1000
_STANDINGS_LIMIT = 100
_SCHEDULE_LIMIT = 100


# --------------------------------------------------------------------------- #
# Small, defensive value helpers (shared by the pure builder)
# --------------------------------------------------------------------------- #
def _str(value) -> str:
    """Coerce any cell to a clean string; NaN/None become an empty string."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        # Non-scalar (e.g. a list) — fall through and stringify.
        pass
    return str(value)


def _int_or_none(value):
    """Return an ``int`` or ``None``.

    Ergast's ``save_int`` casting uses ``-1`` as a sentinel for missing values,
    so ``-1`` (and NaN/None/garbage) all collapse to ``None``. Legitimate zeros
    (e.g. a pit-lane start = grid 0) are preserved.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return None
    return None if ivalue == -1 else ivalue


def _points(value):
    """Return points as a JSON-friendly number (int when whole, else float)."""
    if value is None:
        return 0
    try:
        if pd.isna(value):
            return 0
    except (TypeError, ValueError):
        return 0
    try:
        fvalue = float(value)
    except (TypeError, ValueError):
        return 0
    return int(fvalue) if fvalue.is_integer() else fvalue


def _to_date(value):
    """Best-effort conversion of a cell to a :class:`datetime.date` or ``None``.

    Handles ``datetime``/``pd.Timestamp`` (auto-cast schedule dates), bare
    ``date`` objects, and ``YYYY-MM-DD`` strings.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    if isinstance(value, datetime):        # also covers pd.Timestamp
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    date_attr = getattr(value, "date", None)
    if callable(date_attr):
        try:
            return date_attr()
        except Exception:
            return None
    return None


def _format_lap_time(value):
    """Format an Ergast fastest-lap ``timedelta`` as ``M:SS.mmm`` (or ``None``)."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        total = value.total_seconds()
    except AttributeError:
        # Already a plain string representation from a non-cast response.
        text = str(value).strip()
        return text or None
    if total < 0:
        return None
    minutes = int(total // 60)
    seconds = total - minutes * 60
    return f"{minutes}:{seconds:06.3f}"


def _json_default(obj):
    """Last-resort JSON encoder for stray datetime/timedelta/numpy scalars."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return _format_lap_time(obj)
    try:
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except Exception:
        pass
    return str(obj)


# --------------------------------------------------------------------------- #
# Driver / team field extraction (shared by results and standings)
# --------------------------------------------------------------------------- #
def _driver_code(row) -> str:
    """3-letter driver code from ``driverCode``; fall back to family name."""
    code = row.get("driverCode")
    if isinstance(code, str) and code.strip():
        return code.strip()
    family = _str(row.get("familyName")).strip()
    if family:
        return family[:3].upper()
    return ""


def _full_name(row) -> str:
    """``"givenName familyName"`` with whitespace tidied up."""
    given = _str(row.get("givenName")).strip()
    family = _str(row.get("familyName")).strip()
    return f"{given} {family}".strip()


def _driver_fields(row):
    """Return ``(code, name, team)`` for a race-result row."""
    return _driver_code(row), _full_name(row), _str(row.get("constructorName"))


def _standings_team(row) -> str:
    """Team name for a driver-standings row.

    Driver standings expose ``constructorNames`` as a *list* (a driver may have
    raced for several teams in a season); the most recent one is used. Falls
    back to a singular ``constructorName`` when present.
    """
    names = row.get("constructorNames")
    if isinstance(names, str):
        return names
    if isinstance(names, (list, tuple)) and len(names):
        return _str(names[-1])
    return _str(row.get("constructorName"))


# --------------------------------------------------------------------------- #
# Pure builders — operate on plain DataFrames (no network, unit-testable)
# --------------------------------------------------------------------------- #
def _build_results(results_df: pd.DataFrame) -> list:
    """Full classification for one race, sorted by finishing position."""
    entries = []
    for _, row in results_df.iterrows():
        code, name, team = _driver_fields(row)
        entries.append({
            "pos": _int_or_none(row.get("position")),
            "code": code,
            "name": name,
            "team": team,
            "grid": _int_or_none(row.get("grid")),
            "points": _points(row.get("points")),
            "laps": _int_or_none(row.get("laps")),
            "status": _str(row.get("status")),
        })
    # Unclassified rows (pos is None) drop to the bottom.
    entries.sort(key=lambda e: (e["pos"] is None, e["pos"] if e["pos"] is not None else 0))
    return entries


def _build_podium(results_list: list) -> list:
    """Top-three finishers as ``{pos, code, name, team}`` (already sorted)."""
    podium = [
        {"pos": e["pos"], "code": e["code"], "name": e["name"], "team": e["team"]}
        for e in results_list
        if e["pos"] in (1, 2, 3)
    ]
    return podium[:3]


def _winner_from_podium(podium: list):
    """Winner ``{code, name, team}`` (pos 1) or ``None``."""
    for entry in podium:
        if entry.get("pos") == 1:
            return {"code": entry["code"], "name": entry["name"], "team": entry["team"]}
    return None


def _build_fastest_lap(results_df: pd.DataFrame):
    """Fastest-lap ``{code, name, time}`` for a race, or ``None`` if absent.

    Ergast race results *may* carry a fastest-lap block. We prefer the row
    flagged with ``fastestLapRank == 1``; otherwise we take the smallest
    ``fastestLapTime``. Any problem (missing columns, odd dtypes) yields
    ``None`` rather than raising.
    """
    try:
        columns = results_df.columns
        if "fastestLapTime" not in columns:
            return None

        best = None
        if "fastestLapRank" in columns:
            ranked = results_df[results_df["fastestLapRank"] == 1]
            if len(ranked):
                best = ranked.iloc[0]
        if best is None:
            valid = results_df[results_df["fastestLapTime"].notna()]
            if not len(valid):
                return None
            best = valid.loc[valid["fastestLapTime"].idxmin()]

        time_str = _format_lap_time(best.get("fastestLapTime"))
        if time_str is None:
            return None
        code, name, _team = _driver_fields(best)
        return {"code": code, "name": name, "time": time_str}
    except Exception as exc:  # never let fastest-lap parsing break a race
        log.warning("Could not determine fastest lap: %s", exc)
        return None


def _build_race(row, results_by_round: dict, now_date) -> dict:
    """Assemble one race object from a schedule row (+ results if completed)."""
    rnd = _int_or_none(row.get("round")) or 0
    race_date = _to_date(row.get("raceDate"))
    results_df = results_by_round.get(rnd)

    has_results = results_df is not None and len(results_df) > 0
    date_in_past = (
        race_date is not None and now_date is not None and race_date <= now_date
    )
    completed = bool(has_results and date_in_past)

    race = {
        "round": rnd,
        "name": _str(row.get("raceName")),
        "country": _str(row.get("country")),
        "locality": _str(row.get("locality")),
        "circuit": _str(row.get("circuitName")),
        "date": race_date.isoformat() if race_date is not None else "",
        "status": "completed" if completed else "upcoming",
        "winner": None,
        "podium": [],
        "fastest_lap": None,
        "results": [],
    }

    if completed:
        results_list = _build_results(results_df)
        race["results"] = results_list
        race["podium"] = _build_podium(results_list)
        race["winner"] = _winner_from_podium(race["podium"])
        race["fastest_lap"] = _build_fastest_lap(results_df)

    return race


def _build_races(schedule_df, results_by_round: dict, now) -> list:
    """Ordered list of race objects for the whole season."""
    races: list = []
    if schedule_df is None or len(schedule_df) == 0:
        return races

    now_date = _to_date(now)

    # Iterate rounds in ascending order regardless of source ordering.
    rows = list(schedule_df.iterrows())

    def _round_key(item):
        _, row = item
        rnd = _int_or_none(row.get("round"))
        return rnd if rnd is not None else 0

    rows.sort(key=_round_key)

    for _, row in rows:
        try:
            races.append(_build_race(row, results_by_round, now_date))
        except Exception as exc:  # skip a single malformed row, keep the season
            log.warning("Skipping malformed schedule row: %s", exc)
    return races


def _build_drivers(driver_standings_df) -> list:
    """Driver championship table, sorted by standings position."""
    drivers: list = []
    if driver_standings_df is None or len(driver_standings_df) == 0:
        return drivers

    for _, row in driver_standings_df.iterrows():
        try:
            drivers.append({
                "pos": _int_or_none(row.get("position")),
                "code": _driver_code(row),
                "name": _full_name(row),
                "team": _standings_team(row),
                "points": _points(row.get("points")),
                "wins": _int_or_none(row.get("wins")) or 0,
            })
        except Exception as exc:
            log.warning("Skipping malformed driver-standings row: %s", exc)

    drivers.sort(key=lambda d: (d["pos"] is None, d["pos"] if d["pos"] is not None else 0))
    return drivers


def _build_constructors(constructor_standings_df) -> list:
    """Constructor championship table, sorted by standings position."""
    constructors: list = []
    if constructor_standings_df is None or len(constructor_standings_df) == 0:
        return constructors

    for _, row in constructor_standings_df.iterrows():
        try:
            constructors.append({
                "pos": _int_or_none(row.get("position")),
                "team": _str(row.get("constructorName")),
                "points": _points(row.get("points")),
                "wins": _int_or_none(row.get("wins")) or 0,
            })
        except Exception as exc:
            log.warning("Skipping malformed constructor-standings row: %s", exc)

    constructors.sort(key=lambda c: (c["pos"] is None, c["pos"] if c["pos"] is not None else 0))
    return constructors


def build_season_dict(
    schedule_df,
    results_by_round: dict,
    driver_standings_df,
    constructor_standings_df,
    year: int,
    now: datetime,
) -> dict:
    """Assemble the dashboard JSON document from plain DataFrames.

    This function is deliberately free of any network or fastf1 dependency so
    it can be unit-tested with hand-built DataFrames.

    Args:
        schedule_df: Race schedule (Ergast ``get_race_schedule`` result / plain
            DataFrame). Expected columns: ``round``, ``raceName``, ``raceDate``,
            ``circuitName``, ``locality``, ``country``.
        results_by_round: Mapping of ``round -> race-results DataFrame`` (each
            an element of an Ergast ``get_race_results`` multi-response).
        driver_standings_df: Final driver standings DataFrame (Ergast content).
        constructor_standings_df: Final constructor standings DataFrame.
        year: Season year.
        now: Reference "current" time (UTC) used to classify completed vs
            upcoming races and to stamp the ``updated`` field.

    Returns:
        A JSON-serialisable ``dict`` following the dashboard schema.
    """
    if results_by_round is None:
        results_by_round = {}

    return {
        "season": int(year),
        "updated": now.isoformat() if hasattr(now, "isoformat") else str(now),
        "races": _build_races(schedule_df, results_by_round, now),
        "drivers": _build_drivers(driver_standings_df),
        "constructors": _build_constructors(constructor_standings_df),
    }


# --------------------------------------------------------------------------- #
# Ergast adapter — the only part that touches the network
# --------------------------------------------------------------------------- #
def _get_ergast():
    """Enable the on-disk cache and return a configured Ergast client.

    Mirrors the caching idiom in ``scraper.py``: create the local
    ``.fastf1_cache`` directory and register it with fastf1 before any request,
    so repeated runs are fast and offline-friendly.
    """
    import fastf1  # lazy import keeps ``import fetch_season`` cheap & network-free
    from fastf1.ergast import Ergast

    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(config.CACHE_DIR))
    return Ergast(result_type="pandas", auto_cast=True)


def _fetch_schedule(ergast, year: int) -> pd.DataFrame:
    """Season schedule as a plain DataFrame (empty DataFrame on failure)."""
    try:
        response = ergast.get_race_schedule(season=year, limit=_SCHEDULE_LIMIT)
        return pd.DataFrame(response)
    except Exception as exc:
        log.warning("Could not fetch %s race schedule: %s", year, exc)
        return pd.DataFrame()


def _fetch_results(ergast, year: int) -> dict:
    """Map ``round -> race-results DataFrame`` (empty dict on failure).

    ``get_race_results`` returns an :class:`ErgastMultiResponse`: ``.content``
    is a list of per-race DataFrames and ``.description`` is a DataFrame whose
    i-th row (with a ``round`` column) describes ``content[i]``.
    """
    results_by_round: dict = {}
    try:
        response = ergast.get_race_results(season=year, limit=_RESULTS_LIMIT)
        description = response.description
        content = response.content
    except Exception as exc:
        log.warning("Could not fetch %s race results: %s", year, exc)
        return results_by_round

    for i in range(len(content)):
        try:
            rnd = int(description.iloc[i]["round"])
        except Exception:
            rnd = i + 1  # fall back to positional round numbering
        results_by_round[rnd] = pd.DataFrame(content[i])
    return results_by_round


def _fetch_driver_standings(ergast, year: int) -> pd.DataFrame:
    """Final driver standings DataFrame (empty DataFrame on failure).

    ``get_driver_standings`` returns an :class:`ErgastMultiResponse`; a
    season-wide query yields a single standings list at ``content[0]``.
    """
    try:
        response = ergast.get_driver_standings(season=year, limit=_STANDINGS_LIMIT)
        content = response.content
        if content:
            return pd.DataFrame(content[0])
        log.warning("No driver standings available for %s.", year)
    except Exception as exc:
        log.warning("Could not fetch %s driver standings: %s", year, exc)
    return pd.DataFrame()


def _fetch_constructor_standings(ergast, year: int) -> pd.DataFrame:
    """Final constructor standings DataFrame (empty DataFrame on failure)."""
    try:
        response = ergast.get_constructor_standings(
            season=year, limit=_STANDINGS_LIMIT
        )
        content = response.content
        if content:
            return pd.DataFrame(content[0])
        log.warning("No constructor standings available for %s.", year)
    except Exception as exc:
        log.warning("Could not fetch %s constructor standings: %s", year, exc)
    return pd.DataFrame()


def fetch_season(year: int, now: datetime | None = None) -> dict:
    """Fetch one season from Ergast and build its dashboard JSON document.

    Every network call is isolated so a blocked/missing endpoint degrades to
    empty data instead of raising; the returned dict is always schema-valid.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    try:
        ergast = _get_ergast()
    except Exception as exc:  # fastf1 missing / cache dir unwritable / ...
        log.warning("Could not initialise Ergast client for %s: %s", year, exc)
        return build_season_dict(
            pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame(), year, now
        )

    schedule_df = _fetch_schedule(ergast, year)
    results_by_round = _fetch_results(ergast, year)
    driver_standings_df = _fetch_driver_standings(ergast, year)
    constructor_standings_df = _fetch_constructor_standings(ergast, year)

    return build_season_dict(
        schedule_df,
        results_by_round,
        driver_standings_df,
        constructor_standings_df,
        year,
        now,
    )


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def write_season_json(season: dict, year: int, out_dir: Path | None = None) -> Path:
    """Write ``season`` to ``<out_dir>/<year>.json`` (default: ``web/data``)."""
    out_dir = Path(out_dir) if out_dir is not None else (config.ROOT_DIR / "web" / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{year}.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(season, fh, indent=2, ensure_ascii=False, default=_json_default)
    log.info(
        "Wrote %s (%d races, %d drivers, %d constructors).",
        out_path,
        len(season.get("races", [])),
        len(season.get("drivers", [])),
        len(season.get("constructors", [])),
    )
    return out_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch an F1 season from Ergast into web/data/<year>.json."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help=f"Season year (default: {' and '.join(map(str, DEFAULT_SEASONS))}).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    """CLI entry point: fetch the requested season(s) and write their JSON."""
    args = _parse_args(argv)
    years = [args.year] if args.year is not None else list(DEFAULT_SEASONS)

    for year in years:
        try:
            season = fetch_season(year)
        except Exception as exc:  # belt-and-suspenders; fetch_season shouldn't raise
            log.warning("Falling back to empty document for %s: %s", year, exc)
            season = build_season_dict(
                pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame(),
                year, datetime.now(timezone.utc),
            )
        write_season_json(season, year)


if __name__ == "__main__":
    main()
