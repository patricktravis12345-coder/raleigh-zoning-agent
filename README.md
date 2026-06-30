# Raleigh Zoning Change Tracker

An agent that checks the City of Raleigh's open data for new/updated rezoning
cases each morning, geocodes them, and publishes them to a Google-Maps-based
webpage hosted via GitHub Pages.

## How it works

1. `scripts/find_endpoint.py` — **run this first, once.** Raleigh's rezoning
   case data lives behind an ArcGIS REST service, but the exact URL/fields
   weren't confirmed ahead of time. This script discovers the live
   FeatureServer URL and prints its field schema so we can lock in the real
   query.
2. `scripts/fetch_zoning_cases.py` — queries the confirmed endpoint, filters
   to Raleigh city limits / Wake County, and writes results to
   `data/cases.json`.
3. `scripts/build_map_data.py` — diffs the new pull against `data/seen.json`
   (cases already recorded), appends new/changed cases, and writes
   `docs/data.js` — the file the map page reads.
4. `docs/index.html` — a static page with the Google Maps JS embed. Hosted
   via GitHub Pages, reads `docs/data.js`.
5. `scripts/run_daily.py` — orchestrates steps 2–3 and commits/pushes the
   updated `docs/` folder to GitHub so Pages redeploys automatically.
6. `scheduler/run_agent.bat` — what Windows Task Scheduler calls at 9am.

## One-time setup (Windows)

See `SETUP.md` for full step-by-step instructions, including:
- Installing Python + dependencies
- Getting a Google Maps JavaScript API key
- Setting up the GitHub repo + Pages
- Registering the Task Scheduler job

## Folder structure

```
raleigh-zoning-agent/
├── scripts/
│   ├── find_endpoint.py       # run once to confirm the data source
│   ├── fetch_zoning_cases.py  # pulls latest case data
│   ├── build_map_data.py      # diffs + writes docs/data.js
│   └── run_daily.py           # orchestrates the full daily job
├── data/
│   ├── cases.json             # most recent raw pull (gitignored details TBD)
│   └── seen.json              # case IDs already recorded, for diffing
├── docs/                      # published via GitHub Pages
│   ├── index.html             # the map page
│   └── data.js                # generated — points the map reads
├── config/
│   └── settings.py            # endpoint URL, API keys (via .env), constants
├── scheduler/
│   └── run_agent.bat          # Task Scheduler entry point
├── .env.example
├── requirements.txt
└── SETUP.md
```
