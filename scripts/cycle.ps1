# Evolvra cycle: ingest -> score -> export -> commit -> push. Run by hand or by the scheduled task.
# Usage:  .\scripts\cycle.ps1            (data only)
#         .\scripts\cycle.ps1 -Evolve    (also evolve the weakest scored agent, ~70 free-tier calls)
param([switch]$Evolve)
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location "$repo\core"
$log = Join-Path $HOME ".evolvra\cycle.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
# Tee-Object -Append writes UTF-16 under Windows PowerShell 5.1 (the scheduled task), UTF-8 under pwsh 7,
# which left cycle.log mixed and unreadable to grep. Append UTF-8 explicitly on both.
function Write-Log { process { $_; Add-Content -Path $log -Value "$_" -Encoding UTF8 } }
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
"[$stamp] cycle start (evolve=$Evolve)" | Write-Log
git pull -q --rebase origin main 2>&1 | Write-Log
if ($Evolve) { uv run evolvra cycle --evolve 2>&1 | Write-Log }
else         { uv run evolvra cycle          2>&1 | Write-Log }
"[$((Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))] cycle end" | Write-Log
Pop-Location
