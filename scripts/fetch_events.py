import json, os, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
API_KEY = os.environ.get("THESPORTSDB_API_KEY")

if not API_KEY:
    raise SystemExit("Missing THESPORTSDB_API_KEY")

BASE = "https://www.thesportsdb.com/api/v2/json"
HEADERS = {
    "X-API-KEY": API_KEY,
    "Accept": "application/json",
    "User-Agent": "sports-calendar-github-action/1.0",
}

def get_json(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def find_event_list(payload):
    """Accept small response-shape changes without hard-coding one wrapper key."""
    if isinstance(payload, list):
        if not payload or isinstance(payload[0], dict):
            return payload
    if isinstance(payload, dict):
        for key in ("events", "event", "schedule", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        for value in payload.values():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                sample = value[0] if value else {}
                if any(k in sample for k in ("idEvent","strEvent","strTimestamp","dateEvent")):
                    return value
    return []

def first(d, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default

def parse_timestamp(event):
    ts = first(event, "strTimestamp", "timestamp")
    if ts:
        s = str(ts).strip()
        try:
            # TheSportsDB commonly returns UTC-like timestamps without a suffix.
            if s.endswith("Z"):
                return datetime.fromisoformat(s.replace("Z","+00:00"))
            if "+" in s[10:] or s.endswith("+00:00"):
                return datetime.fromisoformat(s)
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    date = first(event, "dateEvent", "date")
    tm = first(event, "strTime", "time", default="00:00:00")
    if date:
        try:
            return datetime.fromisoformat(f"{date}T{tm}").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None

def normalize(e, fallback):
    dt = parse_timestamp(e)
    return {
        "id": str(first(e, "idEvent", "id", default="")),
        "name": first(e, "strEvent", "event", "name"),
        "sport": first(e, "strSport", "sport", default=fallback["sport"]),
        "league": first(e, "strLeague", "league", default=fallback["name"]),
        "league_id": str(first(e, "idLeague", "league_id", default=fallback["league_id"])),
        "season": first(e, "strSeason", "season", default=fallback["season"]),
        "timestamp": dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z") if dt else "",
        "home": first(e, "strHomeTeam", "homeTeam", "home"),
        "away": first(e, "strAwayTeam", "awayTeam", "away"),
        "venue": first(e, "strVenue", "venue"),
        "country": first(e, "strCountry", "country"),
        "badge": first(e, "strLeagueBadge", "leagueBadge"),
        "status": first(e, "strStatus", "status"),
        "postponed": first(e, "strPostponed", "postponed"),
    }

now = datetime.now(timezone.utc)
cutoff = now + timedelta(days=int(CONFIG.get("days_ahead", 60)))
all_events = []
errors = []

for league in CONFIG["leagues"]:
    if not league.get("enabled", True):
        continue
    path = f'/schedule/league/{league["league_id"]}/{league["season"]}'
    try:
        raw = get_json(path)
        events = find_event_list(raw)
        for e in events:
            n = normalize(e, league)
            dt = datetime.fromisoformat(n["timestamp"].replace("Z","+00:00")) if n["timestamp"] else None
            if dt and (now - timedelta(hours=6)) <= dt <= cutoff:
                all_events.append(n)
        print(f'{league["name"]}: {len(events)} records received')
    except Exception as exc:
        errors.append({"league": league["name"], "error": str(exc)})
        print(f'{league["name"]}: ERROR {exc}')

dedup = {}
for e in all_events:
    key = e["id"] or f'{e["league_id"]}|{e["timestamp"]}|{e["name"]}'
    dedup[key] = e

events = sorted(dedup.values(), key=lambda x: x["timestamp"])
out = {
    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
    "window_days": CONFIG.get("days_ahead", 60),
    "events": events,
    "errors": errors,
}
(ROOT / "data" / "events.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(events)} upcoming events")
