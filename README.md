# Sports Calendar v6

V6 finalizes the point model across sports and sorts each day by priority by default.

## Universal levels

- Normal: 0–9
- Watch: 10–24
- Interesting: 25–44
- Hot: explicit trigger only

A high raw score alone never creates HOT.

## Daily sorting

Default:
1. Hot
2. Interesting
3. Watch
4. Normal
5. within the same level: higher score first
6. equal score: earlier kickoff first

UI also includes `Sort: Time`.

## Football — participant points

- A+ Global marquee: 14
- A Major: 10
- B Strong/relevant: 7
- C Momentum: 4

Matchup bonus:
- A+ vs A+: +6
- A+ vs A: +4
- A vs A: +3

Exact marquee rivalries remain HOT and replace normal participant scoring.

Examples:
- Dortmund vs Werder, Bundesliga -> Watch
- Newcastle vs Burnley, EPL -> Watch
- Newcastle vs Arsenal, EPL -> Interesting
- Arsenal vs Liverpool, EPL -> Interesting
- Chelsea vs Manchester United -> Hot (exact marquee rivalry)
- Bayern vs Dortmund -> Hot
- Inter vs Milan -> Hot
- Manchester City vs PSG, Champions League -> Hot (A+ vs A+ UCL trigger)
- Roma vs Real Madrid, Champions League -> Interesting

## Football — competition points

- Domestic Cup: +2
- Top domestic league: +5
- Conference League: +7
- Europa League: +9
- CAF Confederation Cup: +6
- CAF Champions League: +9
- Champions League: +12
- Nations League: +4
- AFCON / World Cup qualifier: +8
- AFCON / EURO / Copa América: +13
- World Cup: +16

Stage:
- R16: +4
- QF: +8
- SF: +14
- Final: +22

## National teams

Same participant tier scale: 14 / 10 / 7 / 4.

African marquee pair gets a small +3 local-interest bonus.
DR Congo national-team match is Hot regardless of opponent/competition for now.

## Basketball

Competition:
- NBA regular season: +6
- EuroLeague: +5
- Basketball Africa League: +5
- AfroBasket: +10
- FIBA Basketball World Cup: +13

Participant tiers:
- A+: 14
- A: 10
- B: 7

Same small matchup bonus model applies.
NBA Finals / selected major basketball finals are Hot.

## Tennis

Only major tournaments enter the calendar:
- Grand Slam: +12
- ATP/WTA Finals: +10
- Masters 1000 / WTA 1000: +7

Players:
- Top 5: +10
- No. 6–10: +7
- two top players: +6 matchup

Stage uses the same R16/QF/SF/Final points.
Grand Slam Final is Hot.
Top-player Grand Slam SF can be Hot.
Small ATP/WTA events stay out.

## UFC / Boxing

- one priority fighter: +10
- two priority fighters: +25 total (10 + 10 + 5 matchup)
- Main Event: +8
- title/world title/unification/undisputed: +25 + Hot trigger

## Formula 1

Practice is excluded.
- Qualifying: +7
- Sprint: +10
- Race: +14
- marquee GP: +11

Therefore:
- normal race -> Watch
- Monaco / Silverstone / Monza type race -> Interesting
- no automatic Hot without standings/context; manual Hot remains possible

## No AI/context layer

No news, milestones, standings, title-race or relegation logic is included.

## Deploy

Replace:
- index.html
- styles.css
- app.js
- config.json
- scripts/fetch_events.py
- README.md

Keep `.github/workflows/update.yml`, then run the existing GitHub Action.
