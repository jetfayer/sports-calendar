# Sports Calendar v3

Personal sports-event calendar for CRM / promo planning.

## Included coverage

### Football — clubs
- Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- UEFA Champions League, Europa League, Conference League
- CAF Champions League, CAF Confederation Cup
- DRC Ligue 1 / Linafoot lookup
- Direct tracking: TP Mazembe, AS Vita Club

### Football — national teams
- DR Congo direct tracking
- UEFA Nations League
- AFCON + AFCON Qualifying
- FIFA World Cup
- World Cup qualifying: CAF, UEFA, CONMEBOL, CONCACAF, AFC, OFC
- Copa América, Gold Cup, Asian Cup
- UEFA European Championship + qualifying

### Other sports
- NBA, EuroLeague, Basketball Africa League
- FIBA Basketball World Cup, AfroBasket
- UFC, Boxing
- Formula 1
- ATP, WTA

## UI
- Date From / To
- 7 / 30 / 60 / 120 day shortcuts
- Sport / Club-National-Individual / Region / Competition filters
- Search
- All / Interesting / Hot
- Separate DRC Focus block
- Data Health table showing exactly which configured sources resolve and return upcoming events

## Important
TheSportsDB coverage is not equally complete for every competition. V3 intentionally exposes this in **Data health** instead of silently pretending every configured source works.

The script resolves league IDs from TheSportsDB dynamically and selects the most plausible current season. It then tries a second season only when the first has no upcoming events.

## Deploy over the existing repo

Upload/replace:
- `index.html`
- `styles.css`
- `app.js`
- `config.json`
- `scripts/fetch_events.py`
- `README.md`

Do not change your existing `.github/workflows/update.yml`.

Then:
1. Commit changes
2. Actions → Update sports calendar → Run workflow
3. Wait for success
4. Open GitHub Pages
5. Expand **Data health** and review any EMPTY / UNRESOLVED / ERROR sources
