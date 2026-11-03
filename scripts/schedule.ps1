# Registers a Windows scheduled task that runs scripts\cycle.ps1 every N hours while you are logged in.
# Usage:  .\scripts\schedule.ps1              (every 6 hours, data only)
#         .\scripts\schedule.ps1 -Hours 12 -Evolve
#         .\scripts\schedule.ps1 -Remove
param([int]$Hours = 6, [switch]$Evolve, [switch]$Remove)
$name = "Evolvra Cycle"
if ($Remove) { Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue; "removed $name"; exit 0 }
$script = Join-Path $PSScriptRoot "cycle.ps1"
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" + $(if ($Evolve) { " -Evolve" } else { "" })
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Hours $Hours)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
"registered '$name': every $Hours h, evolve=$Evolve. First run in ~2 minutes. Log: ~\.evolvra\cycle.log"
