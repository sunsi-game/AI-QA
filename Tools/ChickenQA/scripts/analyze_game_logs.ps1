param(
    [Parameter(Mandatory = $true)]
    [string]$Project,
    [string]$Log = '',
    [switch]$Ai,
    [switch]$PrepareAi,
    [string]$AiPayload = '',
    [string]$Model = 'gemini-3.5-flash-lite',
    [switch]$OpenReport
)

# ASCII-only for Windows PowerShell 5.1 compatibility. This script does not run the game.
$ErrorActionPreference = 'Stop'
if ($Ai -and $PrepareAi) { throw 'Choose only one: -Ai or -PrepareAi.' }
if ($AiPayload -and -not $Ai) { throw '-AiPayload requires -Ai.' }
$ToolRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ToolRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python venv is missing: $Python. Run: python -m venv .venv"
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$outputDir = Join-Path $ToolRoot "output\game_$stamp"
$arguments = @('-m', 'chickenqa', '--out', $outputDir, '--model', $Model)
if ($Log) { $arguments += @('--log', $Log) }
else { $arguments += @('--project', $Project) }
if ($PrepareAi) { $arguments += '--prepare-ai' }
if ($Ai) { $arguments += '--ai' }
if ($AiPayload) { $arguments += @('--ai-payload', $AiPayload) }

Write-Host '[ChickenQA] Analyzing an existing Unreal game log...'
Push-Location $ToolRoot
try {
    & $Python @arguments
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($exitCode -ne 0) { throw "ChickenQA exited with code $exitCode. See the error above." }
$report = Join-Path $outputDir 'report.md'
Write-Host "[ChickenQA] Report: $report"
if ($PrepareAi) { Write-Host "[ChickenQA] Review before upload: $(Join-Path $outputDir 'ai_payload_preview.json')" }
if ($OpenReport) {
    try { Invoke-Item -LiteralPath $report }
    catch { Write-Warning "Report generated but could not open automatically: $report" }
}
