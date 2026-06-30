"""
Runs the full daily pipeline:
  1. fetch_zoning_cases.py  -- pull latest data from Raleigh's ArcGIS service
  2. build_map_data.py      -- diff against history, write docs/data.js
  3. git add/commit/push    -- publish the update so GitHub Pages redeploys

This is what scheduler/run_agent.bat calls every morning at 9am.

Logs to logs/run_YYYY-MM-DD.log in addition to stdout, so failures from an
unattended Task Scheduler run can be diagnosed after the fact.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"


class Tee:
    """Writes to both stdout and a log file."""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def run_step(description, module_path):
    print(f"\n{'=' * 60}\n{description}\n{'=' * 60}")
    result = subprocess.run(
        [sys.executable, str(module_path)],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {description} (exit code {result.returncode})")


def git(*args):
    result = subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result


def publish_to_git():
    if not settings.GIT_AUTO_COMMIT:
        print("GIT_AUTO_COMMIT is false; skipping commit/push.")
        return

    print(f"\n{'=' * 60}\nPublishing to GitHub\n{'=' * 60}")

    git("add", "docs/data.js", "data/seen.json")

    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("No changes to commit (data unchanged since last run).")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    message = f"{settings.GIT_COMMIT_MESSAGE_PREFIX}: {date_str}"
    git("commit", "-m", message)

    if settings.GIT_AUTO_PUSH:
        push_result = git("push")
        if push_result.returncode != 0:
            raise RuntimeError(
                "git push failed. Check that your GitHub credentials/SSH key "
                "are configured for this machine (see SETUP.md)."
            )
    else:
        print("GIT_AUTO_PUSH is false; committed locally but not pushed.")


def main():
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"run_{datetime.now().strftime('%Y-%m-%d')}.log"
    sys.stdout = Tee(log_file)

    print(f"\n\n### Daily run started: {datetime.now().isoformat()} ###")

    try:
        run_step("Step 1: Fetch zoning cases", PROJECT_ROOT / "scripts" / "fetch_zoning_cases.py")
        run_step("Step 2: Build map data", PROJECT_ROOT / "scripts" / "build_map_data.py")
        publish_to_git()
        print(f"\n### Daily run completed successfully: {datetime.now().isoformat()} ###")
    except Exception as e:
        print(f"\n### Daily run FAILED: {e} ###")
        sys.exit(1)


if __name__ == "__main__":
    main()
