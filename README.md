# Sports Calendar v5

V5 introduces a four-level importance ladder and fixes the basketball regression from v4.2.

## Importance ladder

- **Normal** — curated coverage, but no special signal.
- **👀 Watch** — worth noticing; one relevant participant or a moderately relevant event.
- **⭐ Interesting** — stronger promo candidate: strong matchup, stronger stage, or score >= 25.
- **🔥 Hot** — requires an explicit strong trigger. Small bonuses cannot accidentally create HOT.

Default site view is **Watch+**, which shows Watch + Interesting + Hot.

## Football clubs

The broader v4.2 club list remains:
- Tier A / marquee: 15 pts
- Tier B / major: 10 pts
- Tier C / momentum: 6 pts

A single relevant club now produces **Watch**, not automatically Interesting.

Examples:
- Dortmund vs Werder → Watch
- Newcastle vs Burnley → Watch
- Arsenal vs Liverpool → Interesting
- Real Madrid vs Barcelona → Hot via exact rivalry trigger
- Inter vs Shakhtar in UCL → Interesting, not Hot

## National teams

National teams now have their own A/B/C tiers.

Examples:
- Belgium vs France, Nations League → Interesting
- France vs a low-priority opponent → Watch
- Morocco vs Senegal, AFCON → Interesting
- DR Congo national-team match → **always Hot for now**

African powers get dedicated relevance in the DRC-facing model: Morocco, Senegal, Nigeria, Egypt, Algeria, Côte d'Ivoire, Cameroon, Ghana, Tunisia, South Africa and Mali are explicitly tracked.

## Basketball

Basketball is restored. The v4.2 `canonical_team()` regression is removed.

Basketball now has its own relevant-team list:
- marquee NBA teams
- current/recurring NBA contenders
- major EuroLeague clubs

One relevant team → Watch; a strong two-team matchup can become Interesting; NBA/EuroLeague/FIBA/AfroBasket finals can become Hot.

## Tennis

Coverage remains intentionally strict:
- Grand Slams
- ATP/WTA Finals
- configured ATP Masters 1000 / WTA 1000-level events

Highlighting:
- one top player → Watch
- top-player matchup → Interesting
- QF → Watch
- SF → Interesting
- Grand Slam Final → Hot
- Grand Slam top-player SF → Hot
- 1000 Final with two top players → Hot

Small ATP/WTA tournaments are not admitted into the calendar.

## Formula 1

- Practice → Normal
- Qualifying → Watch
- Sprint → Watch
- Regular race → Watch
- marquee GP (Monaco, Silverstone, Monza, etc.) → Interesting
- no automatic F1 Hot without standings/context; manual HOT remains possible

## UFC / Boxing

- one priority fighter → Watch
- two priority fighters / strong main event → Interesting
- title fight / world title / unification / undisputed → Hot

Not every boxing event is Hot.

## Filters

Existing filters stay, including:
- Sport
- Competition type
- Region
- Competition
- Stage
- Priority reason
- DRC only
- Top participants only
- Score minimum
- All / Watch+ / Interesting / Hot

## No AI/context layer

V5 intentionally does **not** implement news, milestones, standings, title-race or relegation context.

## Deploy

Replace:
- `index.html`
- `styles.css`
- `app.js`
- `config.json`
- `scripts/fetch_events.py`
- `README.md`

Keep `.github/workflows/update.yml`, then run the existing GitHub Action.
