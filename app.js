const state = { data: [], search: "", sport: "", league: "" };

function browserDate(ts) {
  if (!ts) return null;
  // If TheSportsDB gives a timezone-less ISO timestamp, treat it as UTC.
  const value = /Z$|[+-]\d\d:\d\d$/.test(ts) ? ts : `${ts}Z`;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtDay(d) {
  return new Intl.DateTimeFormat("uk-UA", {
    weekday: "long", day: "2-digit", month: "long", year: "numeric"
  }).format(d);
}

function fmtTime(d) {
  return new Intl.DateTimeFormat("uk-UA", {
    hour: "2-digit", minute: "2-digit"
  }).format(d);
}

function esc(v="") {
  return String(v).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

function options(values, current, allLabel) {
  return `<option value="">${allLabel}</option>` + [...values]
    .sort((a,b)=>a.localeCompare(b))
    .map(v => `<option ${v===current?"selected":""}>${esc(v)}</option>`).join("");
}

function render() {
  const now = new Date();
  const q = state.search.trim().toLowerCase();
  let rows = state.data
    .map(e => ({...e, _date: browserDate(e.timestamp)}))
    .filter(e => e._date && e._date >= new Date(now.getTime() - 6*60*60*1000))
    .filter(e => !state.sport || e.sport === state.sport)
    .filter(e => !state.league || e.league === state.league)
    .filter(e => !q || [e.name,e.league,e.sport,e.home,e.away,e.venue]
      .some(v => String(v||"").toLowerCase().includes(q)))
    .sort((a,b)=>a._date-b._date);

  document.querySelector("#eventCount").textContent = rows.length;
  document.querySelector("#empty").hidden = rows.length !== 0;

  if (rows.length) {
    const a = rows[0]._date, b = rows[rows.length-1]._date;
    const f = new Intl.DateTimeFormat("uk-UA",{day:"2-digit",month:"2-digit"});
    document.querySelector("#dateRange").textContent = `${f.format(a)} – ${f.format(b)}`;
  } else {
    document.querySelector("#dateRange").textContent = "—";
  }

  const groups = new Map();
  for (const e of rows) {
    const key = e._date.toLocaleDateString("en-CA");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  }

  document.querySelector("#calendar").innerHTML = [...groups.entries()].map(([_, events]) => {
    const date = events[0]._date;
    return `<section class="day">
      <h2>${esc(fmtDay(date))}</h2>
      <div class="grid">${events.map(e => `
        <article class="card">
          <div>
            <div class="time">${esc(fmtTime(e._date))}</div>
            <div class="sport">${esc(e.sport || "")}</div>
          </div>
          <div>
            <div class="league">${esc(e.league || "")}</div>
            <div class="event">${esc(e.name || [e.home,e.away].filter(Boolean).join(" vs "))}</div>
            ${e.venue ? `<div class="venue">${esc(e.venue)}</div>` : ""}
          </div>
          ${e.badge ? `<img class="badge" src="${esc(e.badge)}" alt="">` : ""}
        </article>`).join("")}</div>
    </section>`;
  }).join("");
}

async function init() {
  try {
    const res = await fetch("./data/events.json", {cache:"no-store"});
    const payload = await res.json();
    state.data = Array.isArray(payload.events) ? payload.events : [];
    document.querySelector("#updated").textContent =
      payload.updated_at ? `Updated: ${new Date(payload.updated_at).toLocaleString("uk-UA")}` : "Not updated yet";

    const sports = new Set(state.data.map(x=>x.sport).filter(Boolean));
    const leagues = new Set(state.data.map(x=>x.league).filter(Boolean));
    document.querySelector("#sportFilter").innerHTML = options(sports, "", "All sports");
    document.querySelector("#leagueFilter").innerHTML = options(leagues, "", "All leagues");

    render();
  } catch (e) {
    document.querySelector("#updated").textContent = "Could not load events.";
    console.error(e);
  }
}

document.querySelector("#search").addEventListener("input", e => {state.search=e.target.value;render()});
document.querySelector("#sportFilter").addEventListener("change", e => {state.sport=e.target.value;render()});
document.querySelector("#leagueFilter").addEventListener("change", e => {state.league=e.target.value;render()});
init();
