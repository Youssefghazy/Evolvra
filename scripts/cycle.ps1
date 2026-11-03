# Evolvra cycle: ingest -> score -> export -> commit -> push. Run by hand or by the scheduled task.
# Usage:  .\scripts\cycle.ps1            (data only)
#         .\scripts\cycle.ps1 -Evolve    (also evolve the weakest scored agent, ~70 free-tier calls)
param([switch]$Evolve)
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location "$repo\core"
$log = Join-Path $HOME ".evolvra\cycle.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
"[$stamp] cycle start (evolve=$Evolve)" | Tee-Object -FilePath $log -Append
git pull -q --rebase origin main 2>&1 | Tee-Object -FilePath $log -Append
if ($Evolve) { uv run evolvra cycle --evolve 2>&1 | Tee-Object -FilePath $log -Append }
else         { uv run evolvra cycle          2>&1 | Tee-Object -FilePath $log -Append }
"[$stamp] cycle end" | Tee-Object -FilePath $log -Append
Pop-Location
