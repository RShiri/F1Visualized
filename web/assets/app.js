/* F1 Visualized dashboard — loads season JSON and renders standings, calendar, results. */
"use strict";

const SEASONS = {};
let current = "2026";

/* ---- team colours (presentation lives in the front-end) ---- */
const TEAM_COLORS = {
  "mclaren": "#ff8000",
  "ferrari": "#e8002d",
  "red bull racing": "#3671c6", "red bull": "#3671c6",
  "mercedes": "#27f4d2",
  "aston martin": "#229971",
  "alpine": "#0093cc",
  "williams": "#1868db",
  "racing bulls": "#6692ff", "rb": "#6692ff", "visa cash app rb": "#6692ff",
  "haas": "#b6babd", "haas f1 team": "#b6babd",
  "kick sauber": "#52e252", "sauber": "#52e252", "stake f1 team kick sauber": "#52e252",
  "audi": "#26c1a3",
  "cadillac": "#c9a24b",
};
function teamColor(team) {
  if (!team) return "#8a8a95";
  return TEAM_COLORS[team.trim().toLowerCase()] || "#8a8a95";
}

/* ---- country -> flag emoji ---- */
const FLAGS = {
  "australia": "🇦🇺", "china": "🇨🇳", "japan": "🇯🇵", "bahrain": "🇧🇭",
  "saudi arabia": "🇸🇦", "united states": "🇺🇸", "usa": "🇺🇸", "italy": "🇮🇹",
  "monaco": "🇲🇨", "canada": "🇨🇦", "spain": "🇪🇸", "austria": "🇦🇹",
  "great britain": "🇬🇧", "united kingdom": "🇬🇧", "uk": "🇬🇧", "hungary": "🇭🇺",
  "belgium": "🇧🇪", "netherlands": "🇳🇱", "azerbaijan": "🇦🇿", "singapore": "🇸🇬",
  "mexico": "🇲🇽", "brazil": "🇧🇷", "qatar": "🇶🇦", "united arab emirates": "🇦🇪",
  "uae": "🇦🇪", "france": "🇫🇷", "portugal": "🇵🇹", "germany": "🇩🇪",
};
function flag(country) {
  return FLAGS[(country || "").trim().toLowerCase()] || "🏁";
}

const $ = (sel, el = document) => el.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtPts = (p) => (Number.isInteger(p) ? p : (Math.round(p * 10) / 10)).toString();
const swatch = (team, w = 5, h = 18) =>
  `<span class="swatch" style="background:${teamColor(team)};width:${w}px;height:${h}px"></span>`;

/* ---------------- rendering ---------------- */
function data() { return SEASONS[current]; }

function render() {
  const d = data();
  if (!d) return;
  $("#updated").textContent = d.updated
    ? "Updated " + new Date(d.updated).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : "";
  renderOverview(d);
  renderStandings(d);
  renderCalendar(d);
  renderResultsSelect(d);
}

function renderOverview(d) {
  const dl = d.drivers[0], d2 = d.drivers[1];
  const cl = d.constructors[0], c2 = d.constructors[1];

  $("#driverLeader").style.setProperty("--accent", teamColor(dl.team));
  $("#driverLeader").innerHTML = `
    <div class="lc-label">Drivers' Championship Leader</div>
    <div class="lc-pts"><b>${fmtPts(dl.points)}</b><span>points</span></div>
    <div class="lc-name">${esc(dl.name)}</div>
    <div class="lc-team">${esc(dl.team)} · ${dl.wins} win${dl.wins === 1 ? "" : "s"}</div>
    <div class="lc-gap">Lead over ${esc(d2 ? d2.code : "—")}: <b>${d2 ? "+" + fmtPts(dl.points - d2.points) : "—"}</b></div>`;

  $("#constructorLeader").style.setProperty("--accent", teamColor(cl.team));
  $("#constructorLeader").innerHTML = `
    <div class="lc-label">Constructors' Championship Leader</div>
    <div class="lc-pts"><b>${fmtPts(cl.points)}</b><span>points</span></div>
    <div class="lc-name">${esc(cl.team)}</div>
    <div class="lc-team">${cl.wins} win${cl.wins === 1 ? "" : "s"}</div>
    <div class="lc-gap">Lead over ${esc(c2 ? c2.team : "—")}: <b>${c2 ? "+" + fmtPts(cl.points - c2.points) : "—"}</b></div>`;

  const next = d.races.find((r) => r.status === "upcoming");
  const nc = $("#nextRace");
  if (next) {
    const days = Math.max(0, Math.ceil((new Date(next.date) - new Date()) / 864e5));
    nc.innerHTML = `
      <div class="card-title">Next Race</div>
      <div class="nc-flag">${flag(next.country)}</div>
      <div class="nc-round">Round ${next.round}</div>
      <div class="nc-name">${esc(next.name)}</div>
      <div class="nc-sub">${esc(next.locality)} · ${fmtDate(next.date)}</div>
      <div class="nc-countdown"><b>${days}</b> day${days === 1 ? "" : "s"} to go</div>`;
  } else {
    nc.innerHTML = `<div class="card-title">Season</div>
      <div class="nc-name">Season complete</div>
      <div class="nc-sub">All ${d.races.length} rounds finished 🏁</div>`;
  }

  const last = [...d.races].reverse().find((r) => r.status === "completed" && r.podium.length);
  const lc = $("#lastRace");
  if (last) {
    const medals = ["🥇", "🥈", "🥉"];
    lc.innerHTML = `<div class="card-title">Last Race — ${esc(last.name)}</div>` +
      last.podium.map((p, i) => `
        <div class="podium-row">
          <span class="pp">${medals[i] || p.pos}</span>
          <span class="swatch" style="background:${teamColor(p.team)}"></span>
          <span class="pd">${esc(p.name)}</span>
          <span class="pt">${esc(p.team)}</span>
        </div>`).join("");
  } else {
    lc.innerHTML = `<div class="card-title">Last Race</div><div class="nc-sub">No races completed yet.</div>`;
  }

  $("#miniDrivers").innerHTML = miniRows(d.drivers.slice(0, 5), (x) => x.name, (x) => x.team, (x) => x.team);
  $("#miniConstructors").innerHTML = miniRows(d.constructors.slice(0, 5), (x) => x.team, (x) => `${x.wins} win${x.wins === 1 ? "" : "s"}`, (x) => x.team);
}

function miniRows(rows, name, sub, team) {
  return rows.map((x) => `
    <div class="row">
      <span class="pos">${x.pos}</span>
      <span class="swatch" style="background:${teamColor(team(x))}"></span>
      <span><div class="who">${esc(name(x))}</div><div class="sub">${esc(sub(x))}</div></span>
      <span class="pts">${fmtPts(x.points)}</span>
    </div>`).join("");
}

function renderStandings(d) {
  const maxD = Math.max(1, ...d.drivers.map((x) => x.points));
  $("#driverStandings").innerHTML = d.drivers.map((x) => standRow(
    x.pos, `${esc(x.name)} <span class="code">${esc(x.code)}</span>`, x.team, x.points, maxD, x.wins)).join("");
  const maxC = Math.max(1, ...d.constructors.map((x) => x.points));
  $("#constructorStandings").innerHTML = d.constructors.map((x) => standRow(
    x.pos, esc(x.team), x.team, x.points, maxC, x.wins)).join("");
}

function standRow(pos, nameHtml, team, points, max, wins) {
  const w = Math.max(2, (points / max) * 100);
  return `
    <div class="st-row">
      <div class="st-pos">${pos}</div>
      <div class="st-main">
        <div class="st-name">${swatch(team)}<span>${nameHtml}</span></div>
        <div class="st-team">${esc(team)}</div>
        <div class="bar"><span style="width:${w}%;background:${teamColor(team)}"></span></div>
      </div>
      <div class="st-pts">${fmtPts(points)}<small>${wins} win${wins === 1 ? "" : "s"}</small></div>
    </div>`;
}

function renderCalendar(d) {
  const done = d.races.filter((r) => r.status === "completed").length;
  $("#calendarMeta").textContent = `${done} of ${d.races.length} rounds completed`;
  const nextRound = (d.races.find((r) => r.status === "upcoming") || {}).round;
  const grid = $("#calendarGrid");
  grid.innerHTML = "";
  d.races.forEach((r) => {
    const isNext = r.round === nextRound;
    const badge = r.status === "completed" ? `<span class="badge done">Completed</span>`
      : isNext ? `<span class="badge next">Next Up</span>` : `<span class="badge up">Upcoming</span>`;
    const foot = r.status === "completed" && r.winner
      ? `<span class="rc-winner">${swatch(r.winner.team, 4, 15)} ${esc(r.winner.code)} · ${esc(r.winner.name.split(" ").slice(-1)[0])}</span>`
      : `<span class="rc-sub">${fmtDate(r.date)}</span>`;
    const card = el("div", "race-card" + (isNext ? " next" : ""));
    card.innerHTML = `
      <div class="rc-top"><span class="rc-round">R${r.round}</span><span class="rc-flag">${flag(r.country)}</span></div>
      <div class="rc-name">${esc(r.name)}</div>
      <div class="rc-sub">${esc(r.locality)}${r.country ? ", " + esc(r.country) : ""}</div>
      <div class="rc-foot">${badge}${foot}</div>`;
    if (r.status === "completed") {
      card.style.cursor = "pointer";
      card.addEventListener("click", () => { showTab("results"); selectRace(r.round); });
    } else {
      card.style.cursor = "default";
    }
    grid.appendChild(card);
  });
}

function renderResultsSelect(d) {
  const sel = $("#raceSelect");
  const completed = d.races.filter((r) => r.status === "completed");
  sel.innerHTML = completed.map((r) => `<option value="${r.round}">R${r.round} — ${esc(r.name)}</option>`).join("")
    || `<option value="">No completed races</option>`;
  sel.onchange = () => renderRaceDetail(d, +sel.value);
  const last = completed[completed.length - 1];
  if (last) { sel.value = last.round; renderRaceDetail(d, last.round); }
  else $("#raceDetail").innerHTML = `<div class="empty-note">No completed races in this season yet.</div>`;
}

function selectRace(round) {
  const sel = $("#raceSelect");
  sel.value = round;
  renderRaceDetail(data(), round);
}

function renderRaceDetail(d, round) {
  const r = d.races.find((x) => x.round === round);
  const box = $("#raceDetail");
  if (!r || !r.results.length) { box.innerHTML = `<div class="empty-note">No results available.</div>`; return; }
  const medals = ["🥇", "🥈", "🥉"];
  const podium = r.podium.map((p, i) => `
    <div class="pod" style="--accent:${teamColor(p.team)}">
      <div class="medal">${medals[i]}</div>
      <div class="pn">${esc(p.name)}</div>
      <div class="pt">${esc(p.team)}</div>
    </div>`).join("");
  const rows = r.results.map((x) => `
    <tr>
      <td class="num">${x.status === "Finished" || x.pos ? x.pos : "—"}</td>
      <td><span class="cell-driver">${swatch(x.team)}<span>${esc(x.name)}</span><span class="code">${esc(x.code)}</span></span></td>
      <td>${esc(x.team)}</td>
      <td class="num">${x.grid ?? "—"}</td>
      <td class="num">${x.status === "Finished" ? "" : `<span class="dnf">${esc(x.status)}</span>`}${x.status === "Finished" ? x.laps ?? "" : ""}</td>
      <td class="num">${x.points ? fmtPts(x.points) : "—"}</td>
    </tr>`).join("");
  box.innerHTML = `
    <div class="race-hero">
      <div class="card" style="flex:1 1 100%">
        <div class="card-title">${flag(r.country)} ${esc(r.name)} · Round ${r.round} · ${fmtDate(r.date)}</div>
        <div class="podium-cards">${podium}</div>
        ${r.fastest_lap ? `<div style="margin-top:14px;color:var(--ink-2);font-size:13px">⏱ Fastest lap — <b style="color:var(--ink)">${esc(r.fastest_lap.name || r.fastest_lap.code)}</b> ${esc(r.fastest_lap.time || "")}</div>` : ""}
      </div>
    </div>
    <table class="results">
      <thead><tr><th class="num">Pos</th><th>Driver</th><th>Team</th><th class="num">Grid</th><th class="num">Laps / Status</th><th class="num">Pts</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

/* ---------------- helpers & wiring ---------------- */
function fmtDate(s) {
  if (!s) return "TBC";
  const d = new Date(s + "T00:00:00");
  return isNaN(d) ? s : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function showTab(name) {
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === name));
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setSeason(year) {
  if (!SEASONS[year]) return;
  current = year;
  document.querySelectorAll("#seasonToggle button").forEach((b) => b.classList.toggle("active", b.dataset.season === year));
  render();
}

function wire() {
  document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  document.querySelectorAll("#seasonToggle button").forEach((b) => b.addEventListener("click", () => setSeason(b.dataset.season)));
}

async function boot() {
  wire();
  const years = ["2025", "2026"];
  // Embedded mode (self-contained bundle): data injected as window.SEASON_DATA.
  if (window.SEASON_DATA) {
    Object.assign(SEASONS, window.SEASON_DATA);
  } else {
    await Promise.all(years.map(async (y) => {
      try {
        const res = await fetch(`data/${y}.json`, { cache: "no-store" });
        if (res.ok) SEASONS[y] = await res.json();
      } catch (e) { /* offline / file:// */ }
    }));
  }
  const avail = years.filter((y) => SEASONS[y]);
  if (!avail.length) {
    $("#main").innerHTML = `<div class="empty-note">Could not load season data. Serve this folder over HTTP (e.g. <code>python -m http.server</code>) or run the deploy workflow.</div>`;
    return;
  }
  if (!SEASONS[current]) current = avail[avail.length - 1];
  $("#footNote").textContent = "Data via fastf1 / Ergast · sample data shown until the fetch workflow runs";
  setSeason(current);
}

document.addEventListener("DOMContentLoaded", boot);
