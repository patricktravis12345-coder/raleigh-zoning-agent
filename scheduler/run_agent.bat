@echo off
REM Called by Windows Task Scheduler each morning.
REM Activates the project's virtual environment and runs the daily pipeline.

REM Adjust this path if you clone the repo somewhere other than your user folder.
cd /d "%~dp0\.."

call venv\Scripts\activate.bat

python scripts\run_daily.py

REM Exit code is preserved so Task Scheduler can detect failures.
exit /b %ERRORLEVEL%
