# Sports Calendar

A small personal sports-event calendar powered by TheSportsDB V2 and GitHub Actions.

## Setup

1. Add repository secret `THESPORTSDB_API_KEY`.
2. Open **Actions → Update sports calendar → Run workflow** once.
3. Enable **Settings → Pages → Deploy from a branch → main / (root)**.
4. Edit `config.json` to add/remove tracked leagues.

The API key is never stored in the repository. GitHub Actions uses it only while fetching data.

### Current starter leagues
- NBA — league ID `4387`, season `2026-2027`
- English Premier League — league ID `4328`, season `2026-2027`

The website displays event times in the visitor's browser timezone.
