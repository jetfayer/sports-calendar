import json, os, re, time, unicodedata, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
API_KEY=os.environ.get("THESPORTSDB_API_KEY")
if not API_KEY:
    raise SystemExit("Missing THESPORTSDB_API_KEY")

BASE="https://www.thesportsdb.com/api/v2/json"
HEADERS={"X-API-KEY":API_KEY,"Accept":"application/json","User-Agent":"sports-calendar/3.0"}
MIN_REQUEST_GAP=2.05  # stays under roughly 30 requests/minute
_last_request=0.0

def api(path):
    global _last_request
    wait=MIN_REQUEST_GAP-(time.monotonic()-_last_request)
    if wait>0: time.sleep(wait)
    req=urllib.request.Request(BASE+path,headers=HEADERS)
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            payload=json.load(r)
    finally:
        _last_request=time.monotonic()
    return payload

def list_from(payload,keys=()):
    if isinstance(payload,list): return payload
    if isinstance(payload,dict):
        for k in keys:
            v=payload.get(k)
            if isinstance(v,list): return v
        for v in payload.values():
            if isinstance(v,list): return v
    return []

def first(d,*keys,default=""):
    for k in keys:
        if d.get(k) not in (None,""): return d[k]
    return default

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","",s)

def slug(s):
    return urllib.parse.quote(str(s).strip().replace(" ","_"),safe="")

def parse_ts(e):
    ts=first(e,"strTimestamp","timestamp")
    if ts:
        s=str(ts).strip()
        try:
            if s.endswith("Z"): return datetime.fromisoformat(s[:-1]+"+00:00")
            dt=datetime.fromisoformat(s)
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError: pass
    date=first(e,"dateEvent","date")
    tm=first(e,"strTime","time",default="00:00:00")
    if date:
        try:
            return datetime.fromisoformat(f"{date}T{tm}").replace(tzinfo=timezone.utc)
        except ValueError: pass
    return None

NOW=datetime.now(timezone.utc)
CUTOFF=NOW+timedelta(days=int(CONFIG.get("days_ahead",120)))

def season_key(s):
    years=[int(x) for x in re.findall(r"(?:19|20)\d{2}",str(s))]
    cur=NOW.year
    expected_start=cur if NOW.month>=7 else cur-1
    if len(years)>=2:
        start,end=years[0],years[1]
        if start==expected_start and end in (expected_start+1,expected_start): score=0
        elif start<=cur<=end: score=1
        else: score=5+abs(start-expected_start)
        tie=-max(years)
    elif years:
        y=years[0]
        if y==cur: score=0
        elif y==cur+1: score=1
        elif y==cur+2: score=2
        else: score=5+abs(y-cur)
        tie=-y
    else:
        score=100;tie=0
    return (score,tie,str(s))

def event_text(e):
    return " | ".join(str(first(e,k,default="")) for k in
        ("strEvent","strEventAlternate","strLeague","strHomeTeam","strAwayTeam","strDescriptionEN"))

def score_event(e,source):
    score=int(source.get("base_importance",0))
    reasons=[source["name"]] if score else []
    hay=event_text(e)
    low=hay.lower()

    for rule in CONFIG.get("keyword_rules",[]):
        if rule["term"].lower() in low:
            score+=int(rule.get("points",0));reasons.append(rule.get("reason") or rule["term"])

    for rule in CONFIG.get("pair_rules",[]):
        if all(term.lower() in low for term in rule.get("terms",[])):
            score+=int(rule.get("points",0));reasons.append(rule.get("reason","Rivalry"))

    eid=str(first(e,"idEvent","id",default=""))
    if eid and eid in {str(x) for x in CONFIG.get("manual_featured_event_ids",[])}:
        score+=100;reasons.append("Manual featured")

    focus=bool(source.get("drc_focus"))
    if not focus:
        focus=any(t.lower() in low for t in CONFIG.get("focus_terms",[]))

    score=min(score,100)
    hot=int(CONFIG.get("hot_threshold",70))
    interesting=int(CONFIG.get("interesting_threshold",35))
    level="hot" if score>=hot else "interesting" if score>=interesting else "normal"
    return score,level,list(dict.fromkeys(reasons)),focus

def normalize_event(e,source,season=""):
    dt=parse_ts(e)
    score,level,reasons,focus=score_event(e,source)
    return {
        "id":str(first(e,"idEvent","id",default="")),
        "name":first(e,"strEvent","event","name"),
        "sport":first(e,"strSport","sport",default=source.get("sport","")),
        "league":first(e,"strLeague","league",default=source["name"]),
        "league_id":str(first(e,"idLeague","league_id",default=source.get("_resolved_id",""))),
        "season":first(e,"strSeason","season",default=season),
        "timestamp":dt.isoformat().replace("+00:00","Z") if dt else "",
        "home":first(e,"strHomeTeam","homeTeam","home"),
        "away":first(e,"strAwayTeam","awayTeam","away"),
        "venue":first(e,"strVenue","venue"),
        "country":first(e,"strCountry","country"),
        "status":first(e,"strStatus","status"),
        "postponed":first(e,"strPostponed","postponed"),
        "competition_type":source.get("competition_type",""),
        "region":source.get("region",""),
        "importance":score,
        "importance_level":level,
        "importance_reasons":reasons,
        "drc_focus":focus,
        "source":source["name"]
    }

def in_window(n):
    if not n["timestamp"]: return False
    dt=datetime.fromisoformat(n["timestamp"].replace("Z","+00:00"))
    return NOW-timedelta(hours=6)<=dt<=CUTOFF

def choose_league(source,all_leagues):
    aliases=[norm(x) for x in source.get("search_names",[source["name"]])]
    sport=norm(source.get("sport",""))
    candidates=[]
    for row in all_leagues:
        row_sport=norm(first(row,"strSport","sport"))
        if sport and row_sport and row_sport!=sport: continue
        n=norm(first(row,"strLeague","league","name"))
        if n in aliases:
            return row
        ratio=max((SequenceMatcher(None,a,n).ratio() for a in aliases),default=0)
        if ratio>=0.93:
            candidates.append((ratio,row))
    if candidates:
        return max(candidates,key=lambda x:x[0])[1]

    # Fallback to V2 search for only unresolved names.
    for term in source.get("search_names",[source["name"]]):
        try:
            rows=list_from(api(f"/search/league/{slug(term)}"),("leagues","league","results"))
            for row in rows:
                if sport and norm(first(row,"strSport","sport")) not in ("",sport): continue
                if norm(first(row,"strLeague","league","name")) in aliases:
                    return row
            if rows:
                same=[r for r in rows if not sport or norm(first(r,"strSport","sport")) in ("",sport)]
                if same: return same[0]
        except Exception:
            pass
    return None

def choose_team(source):
    aliases=[norm(x) for x in source.get("search_names",[source["name"]])]
    sport=norm(source.get("sport",""))
    country=norm(source.get("country",""))
    for term in source.get("search_names",[source["name"]]):
        rows=list_from(api(f"/search/team/{slug(term)}"),("teams","team","results"))
        ranked=[]
        for row in rows:
            name=norm(first(row,"strTeam","team","name"))
            rsport=norm(first(row,"strSport","sport"))
            rcountry=norm(first(row,"strCountry","country"))
            if sport and rsport and rsport!=sport: continue
            exact=name in aliases
            country_ok=(not country or not rcountry or country in rcountry or rcountry in country)
            ratio=max((SequenceMatcher(None,a,name).ratio() for a in aliases),default=0)
            ranked.append((1 if exact else 0,1 if country_ok else 0,ratio,row))
        if ranked:
            ranked.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
            return ranked[0][3]
    return None

all_events=[]
stats=[]
errors=[]

print("Loading league directory…")
try:
    ALL_LEAGUES=list_from(api("/all/leagues"),("leagues","league","results"))
    print(f"League directory: {len(ALL_LEAGUES)}")
except Exception as exc:
    ALL_LEAGUES=[]
    errors.append({"source":"league directory","error":str(exc)})
    print("League directory ERROR:",exc)

for src0 in CONFIG.get("league_sources",[]):
    if not src0.get("enabled",True): continue
    source=dict(src0)
    stat={"name":source["name"],"kind":"league","competition_type":source.get("competition_type",""),
          "region":source.get("region",""),"resolved_id":"","resolved_name":"","seasons_tried":[],
          "received":0,"upcoming":0,"status":"UNRESOLVED","error":""}
    try:
        row=choose_league(source,ALL_LEAGUES)
        if not row:
            stat["error"]="League not found in TheSportsDB"
            stats.append(stat);print(source["name"],": UNRESOLVED");continue
        lid=str(first(row,"idLeague","id"))
        rname=first(row,"strLeague","league","name",default=source["name"])
        source["_resolved_id"]=lid
        stat["resolved_id"]=lid;stat["resolved_name"]=rname

        seasons_payload=api(f"/list/seasons/{urllib.parse.quote(lid)}")
        seasons_rows=list_from(seasons_payload,("seasons","season","results"))
        seasons=sorted({str(first(x,"strSeason","season","name")) for x in seasons_rows if first(x,"strSeason","season","name")},key=season_key)

        # Try best-ranked season first. Only try the second if the first has no upcoming events.
        candidates=seasons[:2] if seasons else []
        if not candidates:
            # Fallback: next events endpoint needs no season.
            candidates=[None]

        source_upcoming=[]
        for season in candidates:
            if season is None:
                payload=api(f"/schedule/next/league/{urllib.parse.quote(lid)}")
                label="next"
            else:
                payload=api(f"/schedule/league/{urllib.parse.quote(lid)}/{urllib.parse.quote(season,safe='')}")
                label=season
            stat["seasons_tried"].append(label)
            rows=list_from(payload,("events","event","schedule","data","results"))
            stat["received"]+=len(rows)
            normalized=[normalize_event(e,source,season or "") for e in rows]
            upcoming=[n for n in normalized if in_window(n)]
            source_upcoming.extend(upcoming)
            if upcoming: break

        stat["upcoming"]=len(source_upcoming)
        stat["status"]="OK" if source_upcoming else "EMPTY"
        all_events.extend(source_upcoming)
        print(f'{source["name"]}: {stat["status"]}, {stat["received"]} received, {stat["upcoming"]} upcoming')
    except Exception as exc:
        stat["status"]="ERROR";stat["error"]=str(exc)
        errors.append({"source":source["name"],"error":str(exc)})
        print(source["name"],": ERROR",exc)
    stats.append(stat)

for src0 in CONFIG.get("team_sources",[]):
    if not src0.get("enabled",True): continue
    source=dict(src0)
    stat={"name":source["name"],"kind":"team","competition_type":source.get("competition_type",""),
          "region":source.get("region",""),"resolved_id":"","resolved_name":"","seasons_tried":["full current"],
          "received":0,"upcoming":0,"status":"UNRESOLVED","error":""}
    try:
        row=choose_team(source)
        if not row:
            stat["error"]="Team not found in TheSportsDB"
            stats.append(stat);print(source["name"],": UNRESOLVED");continue
        tid=str(first(row,"idTeam","id"))
        tname=first(row,"strTeam","team","name",default=source["name"])
        source["_resolved_id"]=tid
        stat["resolved_id"]=tid;stat["resolved_name"]=tname

        payload=api(f"/schedule/full/team/{urllib.parse.quote(tid)}")
        rows=list_from(payload,("events","event","schedule","data","results"))
        stat["received"]=len(rows)
        upcoming=[normalize_event(e,source,first(e,"strSeason","season")) for e in rows]
        upcoming=[n for n in upcoming if in_window(n)]
        stat["upcoming"]=len(upcoming)
        stat["status"]="OK" if upcoming else "EMPTY"
        all_events.extend(upcoming)
        print(f'{source["name"]}: {stat["status"]}, {stat["received"]} received, {stat["upcoming"]} upcoming')
    except Exception as exc:
        stat["status"]="ERROR";stat["error"]=str(exc)
        errors.append({"source":source["name"],"error":str(exc)})
        print(source["name"],": ERROR",exc)
    stats.append(stat)

# Deduplicate events seen through both league and team sources; keep the higher-priority copy.
dedup={}
for e in all_events:
    key=e["id"] or f'{e["timestamp"]}|{e["name"]}|{e["league_id"]}'
    if key not in dedup or e["importance"]>dedup[key]["importance"] or (e["drc_focus"] and not dedup[key]["drc_focus"]):
        dedup[key]=e

events=sorted(dedup.values(),key=lambda x:(x["timestamp"],-x["importance"],x["name"]))
out={
    "updated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
    "window_days":CONFIG.get("days_ahead",120),
    "default_view_days":CONFIG.get("default_view_days",30),
    "interesting_threshold":CONFIG.get("interesting_threshold",35),
    "hot_threshold":CONFIG.get("hot_threshold",70),
    "events":events,
    "source_stats":stats,
    "errors":errors
}
(ROOT/"data").mkdir(exist_ok=True)
(ROOT/"data"/"events.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Saved {len(events)} unique upcoming events from {len(stats)} configured sources.")
