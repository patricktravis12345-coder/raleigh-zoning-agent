# Setup Guide (Windows)

Follow these steps in order. This only needs to be done once.

## 1. Install Python

If you don't already have it: download from https://www.python.org/downloads/
and install. **Check "Add Python to PATH"** during install.

Verify in a Command Prompt or PowerShell:
```
python --version
```

## 2. Create a GitHub repository

1. On github.com, create a new repository (e.g. `raleigh-zoning-agent`).
   Public is required for free GitHub Pages hosting on a personal account,
   unless you have GitHub Pro/Team (which allows private repo Pages).
2. Clone it to your machine, or `git init` in this project folder and add
   the GitHub repo as the remote:
   ```
   git remote add origin https://github.com/<your-username>/raleigh-zoning-agent.git
   ```
3. Make sure git can push without prompting for a password every time --
   either set up a GitHub Personal Access Token (used as your password when
   prompted) or, better, set up an SSH key and use the `git@github.com:...`
   remote URL instead. GitHub's guide:
   https://docs.github.com/en/authentication/connecting-to-github-with-ssh

   This matters because the agent runs unattended at 9am -- it can't sit
   there waiting for you to type a password.

## 3. Set up the Python virtual environment

From the project folder:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
(The current pipeline only uses Python's standard library, so this step
mostly just creates `venv\` so `scheduler\run_agent.bat` has something to
activate. If we add packages later, they'll install here.)

## 4. Find the real data endpoint

Run:
```
python scripts\find_endpoint.py
```
This checks several likely ArcGIS service URLs and prints what it finds --
service names, layer names, and field lists. Look through the output for
the layer that represents **rezoning cases** (fields like case number,
status, requested zoning), not the static current-zoning-districts layer.

Once you've identified it, copy the full layer URL (ending in a layer
number, like `.../MapServer/2`).

If none of the candidate URLs resolve cleanly, the fallback is to open
https://raleighnc.gov/planning/services/rezoning-process/rezoning-cases
in a browser, open DevTools (F12) -> Network tab, reload the page, and look
for a request to a URL containing `arcgis/rest/services` and `/query`.
Copy the base layer URL (everything before `/query`).

## 5. Configure the project

1. Copy `.env.example` to `.env`.
2. Set `ZONING_CASES_LAYER_URL` to the URL you found in step 4.
3. Leave `GIT_AUTO_PUSH=false` for now -- we'll turn it on after testing.

Then open `config/settings.py` and update `FIELD_MAP` to match the real
field names from step 4's output (the placeholder guesses are likely wrong
field names, even if the overall structure is right).

## 6. Test the data fetch

```
python scripts\fetch_zoning_cases.py
```
This should print the number of features fetched and a sample record's
fields. Confirm the sample fields make sense (e.g. status looks like a real
case status, not blank). Adjust `FIELD_MAP` and re-run until it looks right.

## 7. Test the map data build

```
python scripts\build_map_data.py
```
This reads `data/cases.json` (from step 6) and writes `docs/data.js`.

## 8. Get a Google Maps JavaScript API key

1. Go to https://console.cloud.google.com/ and create a new project (or use
   an existing one).
2. Enable billing on the project. Google requires a billing account to
   issue Maps API keys, but the free monthly credit comfortably covers a
   personal map like this with normal usage.
3. In "APIs & Services" -> "Library", enable **Maps JavaScript API**.
4. In "APIs & Services" -> "Credentials", create a new API key.
5. **Restrict the key** (important, since it'll be visible in your public
   HTML): under "Application restrictions" choose "Websites" and add your
   future GitHub Pages URL, e.g. `https://<your-username>.github.io/*`.
   Under "API restrictions," limit it to "Maps JavaScript API" only.

## 9. Add the API key to the map page

Open `docs/index.html` and replace `YOUR_API_KEY_HERE` with your real key.

(This key is restricted to your Pages domain per step 8, so it's safe to
commit -- this is the standard way Google Maps JS keys are deployed.)

## 10. View the map locally

Open `docs/index.html` directly in a browser to confirm markers show up
and the sidebar list/filters work, before publishing anything.

## 11. Push to GitHub and enable Pages

```
git add .
git commit -m "Initial setup"
git push -u origin main
```

Then on GitHub: repo Settings -> Pages -> under "Build and deployment,"
set Source to "Deploy from a branch," branch `main`, folder `/docs`. Save.

GitHub will give you a URL like:
`https://<your-username>.github.io/raleigh-zoning-agent/`

That's your live, bookmarkable map.

## 12. Turn on auto-push and test the full daily pipeline

In `.env`, set `GIT_AUTO_PUSH=true`. Then run the whole pipeline manually
once:
```
python scripts\run_daily.py
```
Check that it committed and pushed successfully, and that the live GitHub
Pages URL updates within a minute or two.

## 13. Register the 9am Task Scheduler job

Open PowerShell **as Administrator**, navigate to the project folder, and
run:
```
.\scheduler\register_task.ps1
```
This registers a daily 9:00 AM task. Test it immediately without waiting
until tomorrow:
```
Start-ScheduledTask -TaskName RaleighZoningAgent
```
Check `logs\run_<date>.log` afterward to confirm it ran cleanly.

## Notes on the work machine running this

- The task only runs if the machine is on (not asleep) at 9am. If your
  work computer sleeps overnight, either disable sleep, or in Task
  Scheduler's task properties, under "Conditions," check "Wake the
  computer to run this task."
- If your work machine ever goes through a VPN-only network policy that
  blocks general internet access, the ArcGIS query and the `git push` step
  may fail -- check `logs\` if a morning run doesn't show up on the map.
