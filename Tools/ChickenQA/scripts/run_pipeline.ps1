param(
    [Parameter(Mandatory = $true)]
    [string]$Project,
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8',
    [switch]$RunTests,
    [switch]$BuildEditor,
    [switch]$Ai
)

# ASCII-only for Windows PowerShell 5.1.
$ErrorActionPreference = 'Stop'
if ($BuildEditor -and -not $RunTests) { throw '-BuildEditor requires -RunTests.' }
$Project = (Resolve-Path -LiteralPath $Project -ErrorAction Stop).Path
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Python venv is missing: $Python" }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$outputDir = Join-Path $Root "output\run_$stamp"
$testDir = Join-Path $outputDir 'unreal_automation'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
if ($RunTests) {
    # Do not report success if UE failed or executed zero tests.
    & (Join-Path $PSScriptRoot 'run_unreal_tests.ps1') -Project $Project -EngineRoot $EngineRoot -ReportPath $testDir -BuildEditor:$BuildEditor
    if ($LASTEXITCODE -ne 0) { throw 'Unreal tests failed' }
}
$arguments = @('-m', 'chickenqa', '--project', $Project, '--out', $outputDir)
$index = Join-Path $testDir 'index.json'
if ($RunTests) { $arguments += @('--ue-report', $index) }
if ($Ai) { $arguments += '--ai' }
Push-Location $Root
try {
    & $Python @arguments
    $pythonExit = $LASTEXITCODE
} finally { Pop-Location }
if ($pythonExit -ne 0) { throw "ChickenQA analysis returned $pythonExit" }
Write-Host "[ChickenQA] Report: $(Join-Path $outputDir 'report.md')"
