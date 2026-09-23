# Sports Calendar v4

V4 finalizes the importance logic and adds the requested filters.

## Importance model

### Football matchup layer
Only one matchup rule is applied:
- one priority club: +10
- two priority clubs: +25 total
- exact marquee rivalry: +40 instead of +25

This prevents double-counting. For example, `Inter Milan vs Shakhtar Donetsk` is not a Milan derby because rivalries are checked by the exact home/away pair.

### Stage layer
- QF: +10
- SF: +20
- Final: +30
- Playoffs: +10

### HOT
HOT is not produced by accumulating many small bonuses. It requires an explicit strong trigger:
- selected exact marquee rivalry
- DRC competitive national-team match
- major football final
- top-vs-top SF/Final
- NBA Finals / selected major basketball final
- UFC/boxing title fight
- Grand Slam final, selected top tennis late-stage match
- manual feature

### Tennis
The ATP/WTA source is filtered first. Only major tournaments are allowed into the calendar:
- Grand Slams
- ATP/WTA Finals
- configured Masters 1000 / WTA 1000-level tournaments

A top player at a small tournament no longer gets into the calendar just because of the player name. Within major tournaments, top-player matchups and late stages drive highlighting.

## Added football cups
- FA Cup
- EFL / Carabao Cup
- Copa del Rey
- DFB-Pokal
- Coppa Italia
- Coupe de France

Early cup rounds get no automatic importance bonus. QF/SF/Final stage scoring applies.

## Filters
- Sport
- Competition type: League / Cup / Continental / National teams / Tour-Event
- Region
- Competition
- Stage
- Priority reason
- DRC only
- Top participants only
- All / Interesting / Hot

## Data health
`NO UPCOMING` replaces the misleading `EMPTY` status.

## No AI/context layer
V4 intentionally does not implement news, standings, milestones, title-race context, or OpenAI API calls.

## Deploy
Replace:
- `index.html`
- `styles.css`
- `app.js`
- `config.json`
- `scripts/fetch_events.py`
- `README.md`

Keep the existing `.github/workflows/update.yml`.

Then run:
Actions → Update sports calendar → Run workflow.
