# F1Visualized — Latest Race Timelapse Pipeline

An automated, end-to-end Python pipeline that scrapes Formula 1 timing data for
the **most recently completed Grand Prix** and renders a broadcast-style MP4
"position-by-lap" timelapse — in the visual language of the *F1Visualized*
Austrian GP timelapse.

<p align="center"><em>Dark canvas · inverted P1→P20 axis · team-coloured driver
traces · tyre badges · pit tags · flashing VSC banner.</em></p>

---

## What it produces

`latest_race_timelapse.mp4` — a 1280×720 H.264 video that animates the race
lap-by-lap:

| Element | Encoding |
|---|---|
| **Grid position** | y-axis, inverted (P1 top, P20 bottom) |
| **Race progress** | x-axis = lap number; each driver's line grows left→right |
| **Driver identity** | 3-letter abbreviation at the head of the line, in the team colour |
| **Tyre compound** | colour + letter badge — Red `S`, Yellow `M`, White `H`, Green `I`, Blue `W` |
| **Pit stop** | green `[IN PIT]` tag on the lap a driver pits |
| **Virtual Safety Car** | flashing yellow `VIRTUAL SAFETY CAR` banner while a VSC is deployed |
| **Retirement** | the trace ends and the abbreviation dims at the lap of retirement |

---

## Architecture

The pipeline is deliberately split into small, importable pieces so it can be
scripted, tested offline, or wired into a future **live dashboard** without
rewriting the core logic.

```
config.py     Shared style tokens, palettes and file paths (single source of truth)
scraper.py    Stage 1 — dynamic data extraction & tidy transformation  → data/
animator.py   Stage 2 — matplotlib FuncAnimation video engine          → *.mp4
tests/        Network-free unit tests for the pure data transforms
.github/workflows/f1_latest_video.yml   Stage 3 — on-demand CI/CD
```

### Stage 1 — `scraper.py`

* Finds the latest completed race **dynamically** — no hard-coded round. It
  walks the event schedule backwards from today and loads the first race whose
  timing data is actually published, so it self-heals in the window right after
  a race when data isn't live yet.
* Extracts, per driver per lap: **lap number, position, tyre compound**, an
  `is_pit_stop` flag (set on the lap a driver enters the pit lane), and an
  `is_vsc` flag.
* Identifies **Virtual Safety Car** laps from the race-control message feed
  (with a `TrackStatus` fallback).
* Emits a tidy `data/race_data.csv` plus `data/race_meta.json` (event details,
  total laps, per-driver name/team/colour, VSC laps).

The heavy lifting lives in **pure functions** (`build_laps_dataframe`,
`extract_vsc_laps`, `build_driver_meta`, …) that take plain DataFrames, so they
are trivially unit-testable and reusable.

### Stage 2 — `animator.py`

* Consumes the Stage 1 output and renders the MP4 with
  `matplotlib.animation.FuncAnimation`.
* Sub-lap interpolation gives smooth vertical motion as positions change.
* Uses a system `ffmpeg` when available, transparently falling back to the
  `imageio-ffmpeg` binary otherwise.

### Stage 3 — `.github/workflows/f1_latest_video.yml`

On-demand (`workflow_dispatch`) CI that installs Python 3.11 + ffmpeg, runs both
stages, and uploads the video as a workflow artifact.

---

## Local usage

```bash
pip install -r requirements.txt

# Stage 1 — scrape the most recent completed race (or a specific one)
python scraper.py                       # latest completed GP
python scraper.py --year 2024 --round 11  # a specific historical race

# Stage 2 — render the video
python animator.py                      # -> latest_race_timelapse.mp4

# Tweak the look
python animator.py --fps 30 --frames-per-lap 6 --width 1920 --height 1080
```

Run the offline tests with `pytest -q`.

---

## CI/CD — running it on GitHub

1. Open the **Actions** tab → **F1 Latest Race Timelapse** → **Run workflow**.
2. Optionally set `year` / `round` (blank = latest completed race).
3. When it finishes, download the `latest_race_timelapse` artifact.

**Triggers.** The workflow is `workflow_dispatch` only — manual, on-demand. It is
structured so a scheduled `cron` trigger can be added later by dropping a
`schedule:` block into the `on:` section; no Python changes required.

**Authentication (PAT).** Checkout and the optional commit step authenticate
with a Personal Access Token. Create a repo secret named **`F1VIZ_PAT`** (a
fine-grained PAT with `contents: write`); the workflow falls back to the default
`GITHUB_TOKEN` if it is not set. To also commit the generated video + data back
to the repo, tick the **`commit_output`** input when dispatching.

---

## Extending toward a live dashboard

The modular design leaves clean seams for future work:

* **Historical back-fill / batch** — every function already accepts explicit
  `year` / `round_number`; loop over a season to build an archive.
* **Live dashboard** — a Streamlit/Dash front-end can import
  `scraper.process_session(...)` for the same tidy DataFrame, and reuse the
  palettes and tyre/compound styles in `config.py` for consistent styling.
* **Scheduled automation** — add a `schedule:` cron block to the workflow to run
  automatically after each race.

---

## Notes

* `fastf1` caches downloads under `.fastf1_cache/` (git-ignored) so re-runs are
  fast.
* Rich lap/telemetry data is available from the **2018** season onward, which is
  how far back the "latest completed race" search will look.
