import json, os, re, time, unicodedata, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))

BASE="https://www.thesportsdb.com/api/v2/json"
HEADERS_BASE={"Accept":"application/json","User-Agent":"sports-calendar/5.0"}
MIN_REQUEST_GAP=2.05
_last_request=0.0

def api(path):
    global _last_request
    api_key=os.environ.get("THESPORTSDB_API_KEY")
    if not api_key:
        raise RuntimeError("Missing THESPORTSDB_API_KEY")
    wait=MIN_REQUEST_GAP-(time.monotonic()-_last_request)
    if wait>0:
        time.sleep(wait)
    headers=dict(HEADERS_BASE)
    headers["X-API-KEY"]=api_key
    req=urllib.request.Request(BASE+path,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            payload=json.load(r)
    finally:
        _last_request=time.monotonic()
    return payload

def list_from(payload,keys=()):
    if isinstance(payload,list):
        return payload
    if isinstance(payload,dict):
        for k in keys:
            v=payload.get(k)
            if isinstance(v,list):
                return v
        for v in payload.values():
            if isinstance(v,list):
                return v
    return []

def first(d,*keys,default=""):
    for k in keys:
        if d.get(k) not in (None,""):
            return d[k]
    return default

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","",s)

def slug(s):
    return urllib.parse.quote(str(s).strip().replace(" ","_"),safe="")

def alias_match(value,aliases):
    n=norm(value)
    return any(n==norm(a) for a in aliases)

def definition_for(value,config_key):
    for row in CONFIG.get(config_key,[]):
        if alias_match(value,row.get("aliases",[row.get("name","")])):
            return row
    return None

def exact_pair(a,b,pair):
    return bool(a and b) and {a,b}==set(pair)

def parse_ts(e):
    ts=first(e,"strTimestamp","timestamp")
    if ts:
        s=str(ts).strip()
        try:
            if s.endswith("Z"):
                return datetime.fromisoformat(s[:-1]+"+00:00")
            dt=datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    date=first(e,"dateEvent","date")
    tm=first(e,"strTime","time",default="00:00:00")
    if date:
        try:
            return datetime.fromisoformat(f"{date}T{tm}").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None

NOW=datetime.now(timezone.utc)
CUTOFF=NOW+timedelta(days=int(CONFIG.get("days_ahead",120)))

def season_key(s):
    years=[int(x) for x in re.findall(r"(?:19|20)\d{2}",str(s))]
    cur=NOW.year
    expected_start=cur if NOW.month>=7 else cur-1
    if len(years)>=2:
        start,end=years[0],years[1]
        if start==expected_start and end in (expected_start+1,expected_start):
            score=0
        elif start<=cur<=end:
            score=1
        else:
            score=5+abs(start-expected_start)
        tie=-max(years)
    elif years:
        y=years[0]
        if y==cur:
            score=0
        elif y==cur+1:
            score=1
        elif y==cur+2:
            score=2
        else:
            score=5+abs(y-cur)
        tie=-y
    else:
        score=100
        tie=0
    return (score,tie,str(s))

def event_text(e):
    return " | ".join(str(first(e,k,default="")) for k in (
        "strEvent","strEventAlternate","strLeague","strHomeTeam","strAwayTeam",
        "strDescriptionEN","strVenue","strRound","intRound","strGroup","strStatus"
    ))

def detect_stage(e,source):
    low=event_text(e).lower()
    if "practice" in low:
        return "Practice"
    if "quarter-final" in low or "quarter final" in low or "quarterfinal" in low:
        return "QF"
    if "conference final" in low:
        return "SF"
    if "semi-final" in low or "semi final" in low or "semifinal" in low:
        return "SF"
    if re.search(r"\bfinals?\b",low):
        return "Final"
    if "round of 16" in low or "last 16" in low:
        return "R16"
    if "playoff" in low or "play-off" in low:
        return "Playoffs"
    if "qualif" in low:
        return "Qualifier"
    if "group" in low:
        return "Group"
    if source.get("sport")=="Motorsport":
        if "sprint" in low:
            return "Sprint"
        if "qualifying" in low or "qualification" in low:
            return "Qualifying"
        return "Race"
    if source.get("sport")=="Fighting" and "main event" in low:
        return "Main Event"
    return "Regular"

def stage_score(stage):
    return {"R16":4,"QF":8,"SF":14,"Final":22,"Playoffs":8}.get(stage,0)

def add_reason(reasons,tags,text,tag):
    if text and text not in reasons:
        reasons.append(text)
    if tag and tag not in tags:
        tags.append(tag)

def drc_national_event(e,source):
    if source.get("participant_type")!="National":
        return False
    home=first(e,"strHomeTeam","home")
    away=first(e,"strAwayTeam","away")
    aliases=CONFIG.get("drc_national_aliases",[])
    return source.get("name")=="DR Congo" or alias_match(home,aliases) or alias_match(away,aliases)

def tennis_context(e):
    low=event_text(e).lower()
    tournament=None
    for row in CONFIG.get("tennis_tournaments",[]):
        if any(alias.lower() in low for alias in row.get("aliases",[])):
            tournament=row
            break
    top5=[p for p in CONFIG.get("tennis_top5_players",[]) if p.lower() in low]
    top10=[p for p in CONFIG.get("tennis_top10_players",[]) if p.lower() in low]
    return tournament,list(dict.fromkeys(top5)),list(dict.fromkeys(top10))

def is_tennis_relevant(e):
    tournament,_,_=tennis_context(e)
    return tournament is not None

def infer_team_source_group(source,e):
    if source.get("name")=="DR Congo":
        return "National teams"
    league=str(first(e,"strLeague","league")).lower()
    if "caf " in league or "champions league" in league or "confederation cup" in league:
        return "Continental"
    if "cup" in league or "coupe" in league or "pokal" in league or "coppa" in league:
        return "Cup"
    return source.get("competition_group","League")

def infer_team_source_region(source,e):
    if source.get("name")=="DR Congo":
        league=str(first(e,"strLeague","league")).lower()
        if "world cup" in league:
            return "Global"
        if "afric" in league or "afcon" in league:
            return "Africa"
        return "DRC"
    if infer_team_source_group(source,e)=="Continental":
        return "Africa"
    return "DRC"

def competition_score_for(source,e):
    if source.get("_kind")!="team":
        return int(source.get("competition_score",0))
    league=str(first(e,"strLeague","league")).lower()
    if any(x in league for x in ("world cup","african cup","africa cup","afcon")):
        return 10
    if "champions league" in league:
        return 10
    if "confederation cup" in league:
        return 5
    return 0

def resolve_level(score,auto_watch,hot_triggers):
    if hot_triggers:
        return "hot"
    if score>=int(CONFIG.get("interesting_threshold",25)):
        return "interesting"
    if auto_watch or score>=int(CONFIG.get("watch_threshold",8)):
        return "watch"
    return "normal"


def matchup_bonus(t1,t2):
    tiers={t1,t2}
    if t1=="A+" and t2=="A+":
        return 6
    if "A+" in tiers and "A" in tiers:
        return 4
    if t1=="A" and t2=="A":
        return 3
    return 0

def tennis_tournament_score(kind):
    return {"Grand Slam":12,"Tour Finals":10,"1000":7}.get(kind,0)


def score_event(e,source):
    sport=source.get("sport","")
    low=event_text(e).lower()
    stage=detect_stage(e,source)

    # Competition prestige + stage are separate layers.
    score=competition_score_for(source,e)+stage_score(stage)

    reasons=[]
    tags=[]
    hot_triggers=[]
    has_top=False
    auto_watch=False

    if competition_score_for(source,e)>0:
        add_reason(reasons,tags,first(e,"strLeague","league",default=source["name"]),"Competition")
    if stage=="R16":
        add_reason(reasons,tags,"Round of 16","R16")
    if stage=="QF":
        add_reason(reasons,tags,"Quarter-final","Quarter-final")
    if stage=="SF":
        add_reason(reasons,tags,"Semi-final","Semi-final")
    if stage=="Final":
        add_reason(reasons,tags,"Final","Final")
    if stage=="Playoffs":
        add_reason(reasons,tags,"Playoffs","Playoffs")

    home=first(e,"strHomeTeam","home")
    away=first(e,"strAwayTeam","away")

    # DRC national team: HOT regardless of opponent/competition for now.
    if drc_national_event(e,source):
        score=max(score,25)
        hot_triggers.append("DR Congo national team")
        add_reason(reasons,tags,"DR Congo national team","DRC")
        has_top=True
        auto_watch=True

    if sport=="Soccer":
        if source.get("participant_type")=="National":
            hd=definition_for(home,"national_teams")
            ad=definition_for(away,"national_teams")
            has_top=has_top or bool(hd or ad)
            auto_watch=auto_watch or bool(hd or ad)

            for team in (hd,ad):
                if team:
                    score+=int(team.get("score",0))
                    tier=team.get("tier","")
                    add_reason(reasons,tags,f'{team["name"]} · National {tier}',f'National {tier}')

            if hd and ad:
                bonus=matchup_bonus(hd.get("tier"),ad.get("tier"))
                if bonus:
                    score+=bonus
                    add_reason(reasons,tags,"Strong national-team matchup","Top matchup")

                # Small extra local relevance when both are recognised African powers.
                if hd.get("region")=="Africa" and ad.get("region")=="Africa" and hd.get("africa_marquee") and ad.get("africa_marquee"):
                    score+=3
                    add_reason(reasons,tags,"African marquee matchup","African marquee")

                if stage in ("SF","Final") and hd.get("tier") in ("A+","A","B") and ad.get("tier") in ("A+","A","B"):
                    hot_triggers.append("High-profile national late stage")

        else:
            hd=definition_for(home,"football_clubs")
            ad=definition_for(away,"football_clubs")
            has_top=has_top or bool(hd or ad)
            auto_watch=auto_watch or bool(hd or ad)

            hname=hd["name"] if hd else None
            aname=ad["name"] if ad else None
            rivalry=None
            if hname and aname:
                for row in CONFIG.get("football_rivalries",[]):
                    if exact_pair(hname,aname,row.get("teams",[])):
                        rivalry=row
                        break

            if rivalry:
                # Exact rivalry replaces participant points; no double counting.
                score+=40
                add_reason(reasons,tags,rivalry.get("label","Marquee rivalry"),"Rivalry")
                if rivalry.get("hot"):
                    hot_triggers.append("Marquee rivalry")
            else:
                for club in (hd,ad):
                    if club:
                        score+=int(club.get("score",0))
                        tier=club.get("tier","")
                        label={"A+":"Global marquee","A":"Major club","B":"Strong club","C":"Momentum club"}.get(tier,"Relevant club")
                        add_reason(reasons,tags,f'{club["name"]} · {tier}',label)

                if hd and ad:
                    bonus=matchup_bonus(hd.get("tier"),ad.get("tier"))
                    if bonus:
                        score+=bonus
                        add_reason(reasons,tags,"Strong club matchup","Top matchup")

            # A+ vs A+ in Champions League is HOT even in league phase.
            league_name=first(e,"strLeague","league",default=source["name"])
            if hd and ad and hd.get("tier")=="A+" and ad.get("tier")=="A+" and norm(league_name)==norm("UEFA Champions League"):
                hot_triggers.append("UCL global marquee matchup")
                add_reason(reasons,tags,"A+ vs A+ in Champions League","UCL marquee")

            source_name=source.get("name","")
            is_drc_club=source_name in ("TP Mazembe","AS Vita Club") or "tp mazembe" in low or "vita club" in low
            if is_drc_club:
                group=infer_team_source_group(source,e) if source.get("_kind")=="team" else source.get("competition_group")
                bonus=30 if group=="Continental" else 20
                score+=bonus
                add_reason(reasons,tags,"DRC club — continental" if group=="Continental" else "DRC club","DRC")
                has_top=True
                auto_watch=True

            major_final=stage=="Final" and any(norm(x)==norm(league_name) for x in CONFIG.get("major_football_finals",[]))
            if major_final:
                hot_triggers.append("Major football final")
                add_reason(reasons,tags,"Major football final","Final")

            if stage in ("SF","Final") and hd and ad and hd.get("tier") in ("A+","A","B") and ad.get("tier") in ("A+","A","B"):
                hot_triggers.append("High-profile club late stage")

    elif sport=="Basketball":
        hd=definition_for(home,"basketball_teams")
        ad=definition_for(away,"basketball_teams")
        has_top=has_top or bool(hd or ad)
        auto_watch=auto_watch or bool(hd or ad)

        for team in (hd,ad):
            if team:
                score+=int(team.get("score",0))
                tier=team.get("tier","")
                add_reason(reasons,tags,f'{team["name"]} · Basketball {tier}',f'Basketball {tier}')

        if hd and ad:
            bonus=matchup_bonus(hd.get("tier"),ad.get("tier"))
            if bonus:
                score+=bonus
                add_reason(reasons,tags,"Strong basketball matchup","Top matchup")

        league=first(e,"strLeague","league",default=source["name"]).lower()
        if stage=="Final" and "nba" in league:
            hot_triggers.append("NBA Finals")
        elif stage=="Final" and any(x in league for x in ("euroleague","basketball world cup","afrobasket","basketball africa league")):
            hot_triggers.append("Major basketball final")
        elif stage in ("SF","Final") and hd and ad and hd.get("tier") in ("A+","A","B") and ad.get("tier") in ("A+","A","B"):
            hot_triggers.append("High-profile basketball late stage")

    elif sport=="Tennis":
        tournament,top5,top10=tennis_context(e)
        if tournament:
            kind=tournament.get("kind","")
            score+=tennis_tournament_score(kind)
            add_reason(reasons,tags,tournament["name"],kind or "Major tournament")

            top5_count=len(top5)
            top10_count=len(top10)
            total_top=top5_count+top10_count

            # Participant importance: Top 5 = 10, positions 6-10 = 7.
            score+=10*top5_count + 7*top10_count
            if total_top:
                has_top=True
                auto_watch=True
                add_reason(reasons,tags,"Top tennis player","Top participant")
            if total_top>=2:
                score+=6
                add_reason(reasons,tags,"Top-player matchup","Top matchup")

            # HOT triggers are stage-specific, not raw-score based.
            if kind=="Grand Slam" and stage=="Final":
                hot_triggers.append("Grand Slam final")
            elif kind=="Grand Slam" and stage=="SF" and total_top>=2:
                hot_triggers.append("Grand Slam top semi-final")
            elif kind=="Tour Finals" and stage=="Final":
                hot_triggers.append("Tour Finals final")
            elif kind=="1000" and stage=="Final" and total_top>=2:
                hot_triggers.append("1000 final — top matchup")

    elif sport=="Fighting":
        names=CONFIG.get("priority_fighters",[]) if source.get("name")=="UFC" else CONFIG.get("priority_boxers",[])
        hits=list(dict.fromkeys([x for x in names if x.lower() in low]))
        if len(hits)>=2:
            score+=25  # 10 + 10 participants + 5 matchup
            has_top=True
            auto_watch=True
            add_reason(reasons,tags,"Two priority fighters","Top matchup")
        elif len(hits)==1:
            score+=10
            has_top=True
            auto_watch=True
            add_reason(reasons,tags,hits[0],"Top participant")

        if stage=="Main Event":
            score+=8
            auto_watch=True
            add_reason(reasons,tags,"Main event","Main event")

        title_terms=("title fight","world title","championship","unification","undisputed","title bout")
        if any(t in low for t in title_terms):
            score+=25
            add_reason(reasons,tags,"Title fight","Title fight")
            hot_triggers.append("Title fight")

    elif sport=="Motorsport":
        # Practice is filtered out before normalization.
        if stage=="Qualifying":
            score+=7
            auto_watch=True
            add_reason(reasons,tags,"Formula 1 qualifying","Qualifying")
        elif stage=="Sprint":
            score+=10
            auto_watch=True
            add_reason(reasons,tags,"Formula 1 sprint","Sprint")
        else:
            score+=14
            auto_watch=True
            add_reason(reasons,tags,"Formula 1 race","Race")

        if any(x.lower() in low for x in CONFIG.get("marquee_f1_races",[])):
            score+=11
            add_reason(reasons,tags,"Marquee Grand Prix","Marquee race")
        # No automatic F1 HOT without standings/context.

    eid=str(first(e,"idEvent","id",default=""))
    if eid and eid in {str(x) for x in CONFIG.get("manual_featured_event_ids",[])}:
        hot_triggers.append("Manual featured")
        add_reason(reasons,tags,"Manual featured","Manual featured")

    drc_focus=bool(source.get("drc_focus")) or "DRC" in tags
    score=min(score,100)
    level=resolve_level(score,auto_watch,hot_triggers)

    return {
        "score":score,
        "level":level,
        "reasons":reasons,
        "tags":tags,
        "hot_triggers":list(dict.fromkeys(hot_triggers)),
        "drc_focus":drc_focus,
        "has_top_participant":has_top,
        "stage":stage
    }

def normalize_event(e,source,season=""):
    dt=parse_ts(e)
    scored=score_event(e,source)
    if source.get("_kind")=="team":
        group=infer_team_source_group(source,e)
        region=infer_team_source_region(source,e)
    else:
        group=source.get("competition_group","")
        region=source.get("region","")
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
        "participant_type":source.get("participant_type",""),
        "competition_group":group,
        "region":region,
        "tier":source.get("tier",2),
        "stage":scored["stage"],
        "importance":scored["score"],
        "importance_level":scored["level"],
        "importance_reasons":scored["reasons"],
        "priority_tags":scored["tags"],
        "hot_triggers":scored["hot_triggers"],
        "drc_focus":scored["drc_focus"],
        "has_top_participant":scored["has_top_participant"],
        "source":source["name"]
    }

def in_window(n):
    if not n["timestamp"]:
        return False
    dt=datetime.fromisoformat(n["timestamp"].replace("Z","+00:00"))
    return NOW-timedelta(hours=6)<=dt<=CUTOFF

def choose_league(source,all_leagues):
    aliases=[norm(x) for x in source.get("search_names",[source["name"]])]
    sport=norm(source.get("sport",""))
    candidates=[]
    for row in all_leagues:
        row_sport=norm(first(row,"strSport","sport"))
        if sport and row_sport and row_sport!=sport:
            continue
        n=norm(first(row,"strLeague","league","name"))
        if n in aliases:
            return row
        ratio=max((SequenceMatcher(None,a,n).ratio() for a in aliases),default=0)
        if ratio>=0.93:
            candidates.append((ratio,row))
    if candidates:
        return max(candidates,key=lambda x:x[0])[1]

    for term in source.get("search_names",[source["name"]]):
        try:
            rows=list_from(api(f"/search/league/{slug(term)}"),("leagues","league","results"))
            for row in rows:
                if sport and norm(first(row,"strSport","sport")) not in ("",sport):
                    continue
                if norm(first(row,"strLeague","league","name")) in aliases:
                    return row
            same=[r for r in rows if not sport or norm(first(r,"strSport","sport")) in ("",sport)]
            if same:
                return same[0]
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
            if sport and rsport and rsport!=sport:
                continue
            exact=name in aliases
            country_ok=(not country or not rcountry or country in rcountry or rcountry in country)
            ratio=max((SequenceMatcher(None,a,name).ratio() for a in aliases),default=0)
            ranked.append((1 if exact else 0,1 if country_ok else 0,ratio,row))
        if ranked:
            ranked.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
            return ranked[0][3]
    return None

def main():
    all_events=[]
    stats=[]
    errors=[]

    print("Loading league directory…")
    try:
        all_leagues=list_from(api("/all/leagues"),("leagues","league","results"))
        print(f"League directory: {len(all_leagues)}")
    except Exception as exc:
        all_leagues=[]
        errors.append({"source":"league directory","error":str(exc)})
        print("League directory ERROR:",exc)

    for src0 in CONFIG.get("league_sources",[]):
        if not src0.get("enabled",True):
            continue
        source=dict(src0)
        source["_kind"]="league"
        stat={
            "name":source["name"],"kind":"league","competition_group":source.get("competition_group",""),
            "region":source.get("region",""),"resolved_id":"","resolved_name":"","seasons_tried":[],
            "received":0,"upcoming":0,"status":"UNRESOLVED","error":""
        }
        try:
            row=choose_league(source,all_leagues)
            if not row:
                stat["error"]="League not found in TheSportsDB"
                stats.append(stat)
                print(source["name"],": UNRESOLVED")
                continue

            lid=str(first(row,"idLeague","id"))
            rname=first(row,"strLeague","league","name",default=source["name"])
            source["_resolved_id"]=lid
            stat["resolved_id"]=lid
            stat["resolved_name"]=rname

            seasons_payload=api(f"/list/seasons/{urllib.parse.quote(lid)}")
            seasons_rows=list_from(seasons_payload,("seasons","season","results"))
            seasons=sorted({
                str(first(x,"strSeason","season","name"))
                for x in seasons_rows if first(x,"strSeason","season","name")
            },key=season_key)
            candidates=seasons[:2] if seasons else [None]

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

                # Tennis coverage is intentionally curated: only major tournaments enter the calendar.
                if source.get("sport")=="Tennis":
                    rows=[e for e in rows if is_tennis_relevant(e)]
                if source.get("sport")=="Motorsport":
                    rows=[e for e in rows if detect_stage(e,source)!="Practice"]

                normalized=[normalize_event(e,source,season or "") for e in rows]
                upcoming=[n for n in normalized if in_window(n)]
                source_upcoming.extend(upcoming)
                if upcoming:
                    break

            stat["upcoming"]=len(source_upcoming)
            stat["status"]="OK" if source_upcoming else "NO UPCOMING"
            all_events.extend(source_upcoming)
            print(f'{source["name"]}: {stat["status"]}, {stat["received"]} received, {stat["upcoming"]} upcoming')
        except Exception as exc:
            stat["status"]="ERROR"
            stat["error"]=str(exc)
            errors.append({"source":source["name"],"error":str(exc)})
            print(source["name"],": ERROR",exc)
        stats.append(stat)

    for src0 in CONFIG.get("team_sources",[]):
        if not src0.get("enabled",True):
            continue
        source=dict(src0)
        source["_kind"]="team"
        stat={
            "name":source["name"],"kind":"team","competition_group":source.get("competition_group",""),
            "region":source.get("region",""),"resolved_id":"","resolved_name":"","seasons_tried":["full current"],
            "received":0,"upcoming":0,"status":"UNRESOLVED","error":""
        }
        try:
            row=choose_team(source)
            if not row:
                stat["error"]="Team not found in TheSportsDB"
                stats.append(stat)
                print(source["name"],": UNRESOLVED")
                continue

            tid=str(first(row,"idTeam","id"))
            tname=first(row,"strTeam","team","name",default=source["name"])
            source["_resolved_id"]=tid
            stat["resolved_id"]=tid
            stat["resolved_name"]=tname

            payload=api(f"/schedule/full/team/{urllib.parse.quote(tid)}")
            rows=list_from(payload,("events","event","schedule","data","results"))
            stat["received"]=len(rows)
            upcoming=[normalize_event(e,source,first(e,"strSeason","season")) for e in rows]
            upcoming=[n for n in upcoming if in_window(n)]
            stat["upcoming"]=len(upcoming)
            stat["status"]="OK" if upcoming else "NO UPCOMING"
            all_events.extend(upcoming)
            print(f'{source["name"]}: {stat["status"]}, {stat["received"]} received, {stat["upcoming"]} upcoming')
        except Exception as exc:
            stat["status"]="ERROR"
            stat["error"]=str(exc)
            errors.append({"source":source["name"],"error":str(exc)})
            print(source["name"],": ERROR",exc)
        stats.append(stat)

    dedup={}
    level_rank={"normal":0,"watch":1,"interesting":2,"hot":3}
    for e in all_events:
        key=e["id"] or f'{e["timestamp"]}|{e["name"]}|{e["league_id"]}'
        current=dedup.get(key)
        rank=(level_rank.get(e["importance_level"],0),1 if e["drc_focus"] else 0,e["importance"])
        if current is None:
            dedup[key]=e
        else:
            crank=(level_rank.get(current["importance_level"],0),1 if current["drc_focus"] else 0,current["importance"])
            if rank>crank:
                dedup[key]=e

    events=sorted(dedup.values(),key=lambda x:(x["timestamp"],-x["importance"],x["name"]))
    out={
        "updated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "window_days":CONFIG.get("days_ahead",120),
        "default_view_days":CONFIG.get("default_view_days",30),
        "watch_threshold":CONFIG.get("watch_threshold",8),
        "interesting_threshold":CONFIG.get("interesting_threshold",25),
        "hot_requires_trigger":True,
        "events":events,
        "source_stats":stats,
        "errors":errors
    }
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"data"/"events.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Saved {len(events)} unique upcoming events from {len(stats)} configured sources.")

if __name__=="__main__":
    main()
