# Evolvra cycle: ingest -> score -> export -> commit -> push. Run by hand or by the scheduled task.
# Usage:  .\scripts\cycle.ps1            (data only)
#         .\scripts\cycle.ps1 -Evolve    (also evolve the weakest scored agent, ~70 free-tier calls)
param([switch]$Evolve)
$ErrorActionPreference = "Continue"
# Judge critiques contain characters cp1252 cannot print (e.g. non-breaking hyphens); keep Python on UTF-8.
$env:PYTHONIOENCODING = "utf-8"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location "$repo\core"
$log = Join-Path $HOME ".evolvra\cycle.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
# Tee-Object -Append writes UTF-16 under Windows PowerShell 5.1 (the scheduled task), UTF-8 under pwsh 7,
# which left cycle.log mixed and unreadable to grep. Append UTF-8 explicitly on both.
# Add-Content fails ("Stream was not readable") on the existing log, which starts with a UTF-16 BOM.
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Write-Log { process { $_; [System.IO.File]::AppendAllText($log, "$_`r`n", $utf8) } }
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
"[$stamp] cycle start (evolve=$Evolve)" | Write-Log
# --autostash: a stray local edit (6-8 Nov: a leftover STATUS.md) must not stop the pull; without it 8 cycles ran old code
git pull -q --rebase --autostash origin main 2>&1 | Write-Log
if ($Evolve) { uv run evolvra cycle --evolve 2>&1 | Write-Log }
else         { uv run evolvra cycle          2>&1 | Write-Log }
"[$((Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))] cycle end" | Write-Log
Pop-Location
