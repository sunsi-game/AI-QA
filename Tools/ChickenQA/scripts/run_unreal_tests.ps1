param(
    [Parameter(Mandatory = $true)]
    [string]$Project,
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8',
    [string]$TestPrefix = 'ChickenQA.',
    [ValidateRange(1, 2147483647)]
    [int]$MinTests = 6,
    [string]$ReportPath = '',
    [switch]$BuildEditor
)

# ASCII-only for Windows PowerShell 5.1. Run only after compiling the Editor target.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
if (-not (Test-Path -LiteralPath $Editor -PathType Leaf)) { throw "Unreal Editor executable not found: $Editor" }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "ChickenQA Python environment not found: $Python" }
if (-not (Test-Path -LiteralPath $Project -PathType Leaf)) { throw "Project not found: $Project" }
$Project = (Resolve-Path -LiteralPath $Project).Path
if ($BuildEditor) {
    $BuildScript = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
    $SourceDir = Join-Path (Split-Path -Parent $Project) 'Source'
    $EditorTargets = @(Get-ChildItem -LiteralPath $SourceDir -Filter '*Editor.Target.cs' -File)
    if ($EditorTargets.Count -ne 1) { throw 'Expected exactly one Editor.Target.cs under project Source.' }
    if (-not (Test-Path -LiteralPath $BuildScript -PathType Leaf)) { throw "Build script not found: $BuildScript" }
    $EditorTarget = $EditorTargets[0].Name -replace '\.Target\.cs$', ''
    Write-Host "[ChickenQA] Building $EditorTarget before discovering tests. Close Unreal Editor first."
    & $BuildScript $EditorTarget Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "Editor build failed with exit code $LASTEXITCODE" }
}
if (-not $ReportPath) { $ReportPath = Join-Path $Root ('output\unreal_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
New-Item -ItemType Directory -Force -Path $ReportPath | Out-Null
$ReportPath = (Resolve-Path -LiteralPath $ReportPath).Path

# One PowerShell array item per argument. Windows handles spaces in paths.
$ueArgs = @(
    $Project,
    '-unattended', '-nop4', '-nosplash',
    "-ExecCmds=Automation RunTest $TestPrefix;Quit",
    "-ReportExportPath=$ReportPath",
    '-log'
)
Write-Host "[ChickenQA] Running UE tests: $TestPrefix"
Write-Host "[ChickenQA] Report directory: $ReportPath"
& $Editor @ueArgs
$editorExit = $LASTEXITCODE
Write-Host "[ChickenQA] Unreal process exit code: $editorExit"
if ($editorExit -ne 0) { throw "UnrealEditor-Cmd exited with $editorExit. See editor log." }

$index = Join-Path $ReportPath 'index.json'
if (-not (Test-Path -LiteralPath $index -PathType Leaf)) {
    throw "Unreal test report missing: $index. Exit code 0 is not proof that tests ran."
}
& $Python (Join-Path $PSScriptRoot 'check_ue_report.py') --report $index --prefix $TestPrefix --min-tests $MinTests
if ($LASTEXITCODE -ne 0) { throw "Unreal test report verification FAILED. Review $index" }
Write-Host "[ChickenQA] Verified: at least $MinTests tests PASSED under $TestPrefix."
