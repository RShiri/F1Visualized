# PROGRESS

Running journal for the "Broadcast Kinetic" dashboard port
(`claude/broadcast-kinetic-redesign-port-lt6e37`). Scope was `web/` only —
the Python video pipeline (`scraper.py`, `race_animator.py`, `animator.py`,
`combine_gp_videos.py`, `fetch_season.py`, `config.py`, and
`.github/workflows/f1_latest_video.yml`) was explicitly out of scope and
wasn't touched.

## What worked

- **The bug was real and worth fixing first.** `app.js` fetched every
  season's JSON with `cache: "no-store"`, which doesn't just skip a
  cache-buster — it forbids the browser from caching *or even conditionally
  revalidating* the response, so all ~700KB across 5 seasons was
  re-downloaded on every single page load. Switching to `cache: "no-cache"`
  (always revalidates, so a real update is never missed) plus a `?v=<updated>`
  query tag remembered from the previous load fixed it without risking
  stale data — verified by checking the response actually round-trips
  through a normal `fetch` in a local server.
- **Purple as the signal colour was a clean, native fit.** F1 broadcasts
  already use purple site-wide for "fastest lap / the best time set" — using
  it as this dashboard's one accent needed no persuading and reads as
  on-brand rather than borrowed (unlike a generic lime or teal would have).
- **The colour-collision guard turned out to matter more than expected.**
  Checking real ΔE values before touching anything showed Red Bull Racing,
  Racing Bulls and Williams sit within ~18–27 CIE76 ΔE of each other — all
  blue, all present together in the 2024+ standings — which is a genuine
  legibility problem in the race-progression chart (20 overlapping lines)
  and not just a theoretical one. A small hue-rotate nudge (keyed off
  standings order, so the higher-ranked team keeps its true colour) resolved
  it cleanly without inventing brand-secondary colours we don't actually
  have data for.
- **Existing structure needed re-skinning, not restructuring.** The five-tab
  IA, the `TEAM_COLORS` map, and the season-JSON contract were all sound —
  every change was a CSS/token/markup pass, not an architecture change.
- Playwright + the pre-installed Chromium made it easy to actually verify
  each tab at both desktop and phone widths instead of guessing from the
  CSS. The colour-guard fix in particular was only confirmed by looking at
  the rendered standings screenshot, not by reading the diff.

## What didn't (or needed a second pass)

- **Scope drifted mid-task.** An earlier pass of this port had assumed the
  bug to fix was a missing rendered-video backfill (there's a real gap there
  — 100+ completed races across 5 seasons have zero published replay — but
  it's in the out-of-scope Python pipeline) and started wiring
  `render_missing_videos.py` plus workflow changes into
  `deploy_dashboard.yml` before the scope was clarified to `web/`-only. That
  work was fully reverted before any of it was committed; flagging the video
  backfill gap here in case a future session wants to pick it up
  *inside its own properly-scoped task*, not as a side effect of a dashboard
  redesign.
- **`--accent-ink` needed an actual contrast check, not a guess.** The
  reference token block defaulted to a dark ink on the accent fill; textbook
  WCAG contrast math on `#9d4dff` showed dark text (~4.9:1) actually reads
  better than white (~4.25:1) against that particular purple, so this port
  kept the dark ink rather than assuming a vivid colour needs light text.
- **Canvas export fonts need an explicit `document.fonts.load()`.** Text
  drawn to a `<canvas>` doesn't pick up a webfont just because the page
  loaded it via `<link>` — each exact font/weight/style/size string used in
  `renderRaceCard()` has to be individually requested through
  `document.fonts.load()` (and awaited) before drawing, or the canvas falls
  back to the platform's generic serif italic.
- Sandboxed testing couldn't reach `fonts.googleapis.com` (network
  restricted), so the Google Fonts request 404s/resets in this environment.
  Screenshots and the exported PNG both still render — the font-loading
  code degrades to the system font stack — but this hasn't been verified
  against the *actual* Barlow/Barlow Condensed rendering on a real
  connection. Worth a spot-check after this deploys to GitHub Pages.

## Deliberately skipped

- **Per-season data split (§3-equivalent).** `web/data/<year>.json` is
  already split one file per season — there was no monolithic bundle to
  break apart.
- **Standings position-change indicators.** The season JSON doesn't carry a
  previous-round position field, so there's nothing to diff; not invented.
- **A standings-snapshot export** (top-10 as of the selected season) is a
  reasonable follow-up to the race-card export but wasn't required for v1
  and would duplicate a fair amount of the same canvas-drawing code — worth
  factoring `chamferPath`/`loadImg`/`downloadCanvas` out if/when it's added.
