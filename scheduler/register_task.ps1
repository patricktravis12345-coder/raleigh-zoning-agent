# Registers the Raleigh Zoning Agent to run daily at 9:00 AM via Windows
# Task Scheduler. Run this once, from an elevated (Run as Administrator)
# PowerShell prompt, after the project is fully set up (see SETUP.md).
#
# Usage:
#   .\scheduler\register_task.ps1

$taskName = "RaleighZoningAgent"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$batPath = Join-Path $scriptDir "run_agent.bat"

if (-not (Test-Path $batPath)) {
    Write-Error "Could not find run_agent.bat at $batPath"
    exit 1
}

$action = New-ScheduledTaskAction -Execute $batPath
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

# Removes any previous registration of this task so re-running this script
# is safe / idempotent.
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Pulls Raleigh rezoning case data and updates the GitHub Pages map daily at 9am."

Write-Host "Task '$taskName' registered. It will run daily at 9:00 AM."
Write-Host "You can test it immediately with:"
Write-Host "    Start-ScheduledTask -TaskName $taskName"
